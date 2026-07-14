(ns brazilian-soccer-mcp.core
  (:require [cheshire.core :as json]
            [clojure.string :as str]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.tools :as tools])
  (:gen-class))

;;; ─── MCP Protocol ────────────────────────────────────────────────────────────

(def server-info
  {:name    "brazilian-soccer-mcp"
   :version "1.0.0"})

(def capabilities
  {:tools {}})

(defn- make-response [id result]
  {:jsonrpc "2.0"
   :id      id
   :result  result})

(defn- make-error [id code message]
  {:jsonrpc "2.0"
   :id      id
   :error   {:code    code
             :message message}})

(defn- tool-list-result []
  {:tools (mapv (fn [t]
                  {:name        (:name t)
                   :description (:description t)
                   :inputSchema (:inputSchema t)})
                tools/tools)})

(defn- tool-call-result [tool-name args]
  (let [content (tools/call-tool tool-name args)]
    {:content [{:type "text"
                :text (str content)}]}))

(defn handle-request
  "Handle a single JSON-RPC request map, returning a response map."
  [req]
  (let [id     (get req "id")
        method (get req "method")
        params (get req "params" {})]
    (case method
      "initialize"
      (make-response id {:protocolVersion "2024-11-05"
                         :serverInfo      server-info
                         :capabilities    capabilities})

      "notifications/initialized"
      nil  ; no response for notifications

      "tools/list"
      (make-response id (tool-list-result))

      "tools/call"
      (let [tool-name (get params "name")
            args      (get params "arguments" {})]
        (try
          (make-response id (tool-call-result tool-name args))
          (catch Exception e
            (make-error id -32000 (str "Tool execution error: " (.getMessage e))))))

      "ping"
      (make-response id {})

      ;; Unknown method
      (when (some? id)
        (make-error id -32601 (str "Method not found: " method))))))

;;; ─── Stdio transport ─────────────────────────────────────────────────────────

(defn- write-response! [response]
  (when response
    (println (json/generate-string response))
    (flush)))

(defn- run-stdio-loop!
  "Read newline-delimited JSON-RPC messages from stdin, respond on stdout."
  []
  ;; Pre-load data at startup so first query is fast
  (future (data/load-all-data!))
  (let [rdr (java.io.BufferedReader. (java.io.InputStreamReader. System/in "UTF-8"))]
    (loop []
      (when-let [line (.readLine rdr)]
        (let [line (str/trim line)]
          (when (seq line)
            (try
              (let [req  (json/parse-string line)
                    resp (handle-request req)]
                (write-response! resp))
              (catch Exception e
                (write-response! (make-error nil -32700
                                             (str "Parse error: " (.getMessage e))))))))
        (recur)))))

(defn -main [& _args]
  (run-stdio-loop!))
