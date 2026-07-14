(ns brazilian-soccer.server
  "MCP (Model Context Protocol) server over stdio.

  Speaks JSON-RPC 2.0, one message per line on stdin/stdout, per the MCP
  stdio transport. Supported methods: initialize, ping, tools/list,
  tools/call; notifications are accepted and ignored. Diagnostics go to
  stderr so stdout stays a clean protocol channel.

  Run with: clojure -M:run"
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.tools :as tools]
            [clojure.data.json :as json]
            [clojure.string :as str])
  (:gen-class))

(def protocol-version "2024-11-05")

(def server-info
  {:name "brazilian-soccer-mcp"
   :version "1.0.0"})

(defn- rpc-result [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn- rpc-error [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn handle-request
  "Handles one parsed JSON-RPC message (string keys). Returns the response
  map, or nil for notifications (no id) which must not be answered."
  [{:strs [id method params] :as msg}]
  (let [notification? (not (contains? msg "id"))]
    (cond
      (= method "initialize")
      (rpc-result id {:protocolVersion (or (get params "protocolVersion") protocol-version)
                      :capabilities {:tools {}}
                      :serverInfo server-info
                      :instructions (str "Knowledge base of Brazilian soccer: "
                                         "Brasileirão Série A/B/C, Copa do Brasil and Copa "
                                         "Libertadores matches (2003-2023) plus the FIFA 19 "
                                         "player database. Team-name variants are normalized "
                                         "automatically.")})

      (= method "ping")
      (rpc-result id {})

      (= method "tools/list")
      (rpc-result id {:tools (tools/list-tools)})

      (= method "tools/call")
      (let [{:strs [name arguments]} params]
        (rpc-result id (tools/call-tool name arguments)))

      notification?              ; e.g. notifications/initialized, cancelled
      nil

      :else
      (rpc-error id -32601 (str "Method not found: " method)))))

(defn handle-line
  "Parses one line of input and returns the JSON response string, or nil
  when no response should be sent."
  [line]
  (when-not (str/blank? line)
    (let [msg (try (json/read-str line) (catch Exception _ ::parse-error))]
      (cond
        (= ::parse-error msg)
        (json/write-str (rpc-error nil -32700 "Parse error"))

        (map? msg)
        (some-> (try (handle-request msg)
                     (catch Exception e
                       (rpc-error (get msg "id") -32603
                                  (str "Internal error: " (.getMessage e)))))
                json/write-str)

        :else
        (json/write-str (rpc-error nil -32600 "Invalid request"))))))

(defn -main [& _]
  ;; Force the datasets to load before serving so the first query is fast.
  (binding [*out* *err*]
    (println "brazilian-soccer-mcp: loading datasets from" data/data-dir "...")
    (println "brazilian-soccer-mcp:" (count @data/all-matches) "matches,"
             (count @data/all-players) "players. Ready."))
  (let [out (java.io.PrintWriter.
             (java.io.OutputStreamWriter. System/out java.nio.charset.StandardCharsets/UTF_8)
             true)
        in (java.io.BufferedReader.
            (java.io.InputStreamReader. System/in java.nio.charset.StandardCharsets/UTF_8))]
    (loop []
      (when-let [line (.readLine in)]
        (when-let [response (handle-line line)]
          (.println out response))
        (recur)))))
