(ns brazilian-soccer-mcp.mcp
  "Minimal MCP server: newline-delimited JSON-RPC 2.0 over a reader/writer pair."
  (:require [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer-mcp.tools :as tools]))

(def protocol-version "2024-11-05")

(defn- result [id value] {:jsonrpc "2.0" :id id :result value})

(defn- error [id code message] {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn handle-message
  "Handles one parsed JSON-RPC message. Returns the response map, or nil for
  notifications (messages without an id) that need no reply."
  [db {:keys [id method params]}]
  (cond
    (not (string? method)) (when (some? id) (error id -32600 "Invalid Request"))
    (= method "initialize") (result id {:protocolVersion protocol-version
                                        :capabilities {:tools {}}
                                        :serverInfo {:name "brazilian-soccer-mcp" :version "0.1.0"}})
    (str/starts-with? method "notifications/") nil
    (= method "ping") (result id {})
    (= method "tools/list") (result id {:tools tools/specs})
    (= method "tools/call") (result id (tools/call db (:name params) (:arguments params)))
    :else (when (some? id) (error id -32601 (str "Method not found: " method)))))

(defn- process-line [db line]
  (let [msg (try (json/read-str line :key-fn keyword)
                 (catch Exception _ ::parse-error))]
    (if (= ::parse-error msg)
      (error nil -32700 "Parse error")
      (try
        (handle-message db msg)
        (catch Exception e
          (error (:id msg) -32603 (str "Internal error: " (ex-message e))))))))

(defn serve
  "Reads requests line by line from `in` and writes responses to `out` until EOF."
  [db in out]
  (doseq [line (line-seq (io/reader in))
          :when (not (str/blank? line))]
    (when-let [response (process-line db line)]
      (.write out (str (json/write-str response) "\n"))
      (.flush out))))
