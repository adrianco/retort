(ns brsoccer.mcp
  "Model Context Protocol server: JSON-RPC 2.0, one message per line over stdio."
  (:require [brsoccer.tools :as tools]
            [clojure.data.json :as json]
            [clojure.java.io :as io])
  (:import (java.io BufferedReader PrintStream Writer)))

(def supported-versions ["2025-06-18" "2025-03-26" "2024-11-05"])

(def server-info {:name "brazilian-soccer-mcp" :version "1.0.0"})

(defn- rpc-error [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn- rpc-result [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn handle-message
  "Handle one decoded JSON-RPC message. `db` is a delay so the handshake never
  waits on data loading. Returns the response map, or nil for notifications."
  [db msg]
  (if-not (and (map? msg) (string? (get msg "method")))
    (when-not (and (map? msg) (or (contains? msg "result") (contains? msg "error")))
      (rpc-error (when (map? msg) (get msg "id")) -32600 "Invalid Request"))
    (let [id     (get msg "id")
          method (get msg "method")
          params (get msg "params")
          notification? (not (contains? msg "id"))
          reply  (fn [r] (when-not notification? (rpc-result id r)))]
      (try
        (case method
          "initialize"
          (let [wanted (get params "protocolVersion")]
            (reply {:protocolVersion (if (some #{wanted} supported-versions)
                                       wanted
                                       (first supported-versions))
                    :capabilities {:tools {:listChanged false}}
                    :serverInfo server-info
                    :instructions "Query Brazilian soccer data: matches (Brasileirão, Copa do Brasil, Libertadores), team records, calculated standings, statistics and FIFA player data. Team names are matched loosely; call dataset_info for coverage."}))

          "ping" (reply {})

          "tools/list"
          (reply {:tools (mapv #(select-keys % [:name :description :inputSchema]) tools/tools)})

          "tools/call"
          (let [tool (get params "name")
                args (get params "arguments")]
            (cond
              (not (string? tool))
              (when-not notification? (rpc-error id -32602 "Invalid params: missing tool name"))
              (not (or (nil? args) (map? args)))
              (when-not notification? (rpc-error id -32602 "Invalid params: arguments must be an object"))
              :else
              (let [{:keys [text error? unknown?]} (tools/call @db tool args)]
                (if unknown?
                  (when-not notification? (rpc-error id -32602 text))
                  (reply {:content [{:type "text" :text text}] :isError error?})))))

          (when-not notification?
            (rpc-error id -32601 (str "Method not found: " method))))
        (catch Exception e
          (when-not notification?
            (rpc-error id -32603 (str "Internal error: " (or (ex-message e) (str (class e)))))))))))

(defn handle-line
  "Decode one line, dispatch, and return the encoded response string (or nil)."
  [db line]
  (let [parsed (try (json/read-str line) (catch Exception _ ::bad))
        out    (cond
                 (= ::bad parsed)   (rpc-error nil -32700 "Parse error")
                 (vector? parsed)   (if (empty? parsed)
                                      (rpc-error nil -32600 "Invalid Request")
                                      (not-empty (vec (keep #(handle-message db %) parsed))))
                 :else              (handle-message db parsed))]
    (when out
      (json/write-str out :escape-unicode false :escape-slash false))))

(defn serve
  "Read newline-delimited JSON-RPC from `in` until EOF, writing responses to `out`."
  [db ^BufferedReader in ^Writer out]
  (loop []
    (when-let [line (.readLine in)]
      (when-not (clojure.string/blank? line)
        (when-let [resp (handle-line db line)]
          (.write out ^String resp)
          (.write out "\n")
          (.flush out)))
      (recur))))

(defn serve-stdio [db]
  (let [in  (io/reader System/in :encoding "UTF-8")
        out (io/writer System/out :encoding "UTF-8")]
    ;; stdout carries protocol frames only; anything printed goes to stderr.
    (binding [*out* (io/writer System/err :encoding "UTF-8")]
      (serve db in out))))
