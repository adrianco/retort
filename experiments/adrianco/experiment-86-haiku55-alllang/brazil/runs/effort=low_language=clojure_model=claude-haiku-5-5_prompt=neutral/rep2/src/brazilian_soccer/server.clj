(ns brazilian-soccer.server
  "MCP server over stdio (newline-delimited JSON-RPC 2.0).
  Logs go to stderr; stdout carries protocol messages only.
  Usage: clojure -M:server [data-dir]   (default data/kaggle or $BRAZIL_SOCCER_DATA)"
  (:require [brazilian-soccer.data :as data]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer.json :as json]
            [brazilian-soccer.tools :as tools]))

(def ^:private protocol-version "2024-11-05")

(defn- ok [id result] {:jsonrpc "2.0" :id id :result result})

(defn- rpc-error [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn- call-tool-result [ctx params]
  (let [name (get params "name")
        args (or (get params "arguments") {})]
    (try
      {:content [{:type "text" :text (tools/call-tool ctx name args)}]
       :isError false}
      (catch clojure.lang.ExceptionInfo e
        (if (:unknown-tool (ex-data e))
          (throw e)
          {:content [{:type "text" :text (ex-message e)}] :isError true}))
      (catch Exception e
        {:content [{:type "text" :text (str "Error: " (.getMessage e))}] :isError true}))))

(defn- dispatch [ctx method params]
  (case method
    "initialize" {:protocolVersion protocol-version
                  :capabilities {:tools {}}
                  :serverInfo {:name "brazilian-soccer-mcp" :version "0.1.0"}}
    "ping" {}
    "tools/list" {:tools (tools/tool-descriptors)}
    "tools/call" (call-tool-result ctx params)
    ::unknown))

(defn handle-message
  "Handles one decoded JSON-RPC message. Returns the response map, or nil for
  notifications (messages without an id)."
  [ctx msg]
  (let [id (get msg "id")
        method (get msg "method")
        params (get msg "params")]
    (cond
      (not (string? method))
      (when (some? id) (rpc-error id -32600 "Invalid Request"))

      (not (some? id)) nil

      :else
      (try
        (let [result (dispatch ctx method params)]
          (if (= result ::unknown)
            (rpc-error id -32601 (str "Method not found: " method))
            (ok id result)))
        (catch clojure.lang.ExceptionInfo e
          (if (:unknown-tool (ex-data e))
            (rpc-error id -32602 (ex-message e))
            (rpc-error id -32603 (ex-message e))))))))

(defn handle-line
  "Decodes one line of input and returns the encoded response, or nil."
  [ctx line]
  (let [response (try
                   (handle-message ctx (json/decode line))
                   (catch Exception _
                     (rpc-error nil -32700 "Parse error")))]
    (when response
      (json/encode response))))

(defn serve
  "Reads JSON-RPC lines from in and writes responses to out until EOF."
  [ctx in out]
  (doseq [line (line-seq (io/reader in))
          :when (not (str/blank? line))]
    (when-let [resp (handle-line ctx line)]
      (binding [*out* out]
        (println resp)
        (flush)))))

(defn -main [& args]
  (let [dir (or (first args) (System/getenv "BRAZIL_SOCCER_DATA") "data/kaggle")
        _ (binding [*out* *err*] (println "Loading data from" dir))
        ctx (data/load-all dir)]
    (binding [*out* *err*]
      (println "Loaded" (count (:matches ctx)) "matches and" (count (:players ctx)) "players"))
    (serve ctx *in* *out*)))
