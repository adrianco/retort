(ns brazilian-soccer-mcp.mcp
  "Minimal MCP (Model Context Protocol) server over stdio.

  Implements just enough of the JSON-RPC 2.0 protocol to satisfy the
  three methods we care about: `initialize`, `tools/list` and
  `tools/call`. Everything else returns the standard JSON-RPC
  -32601 method-not-found error.

  The protocol framing is plain newline-delimited JSON (one request per
  line) which is the form used by Claude Desktop's MCP stdio transport
  and by ad-hoc test clients."
  (:require [brazilian-soccer-mcp.tools :as tools]
            [cheshire.core :as json]
            [clojure.string :as str]))

(def protocol-version "2024-11-05")

(defn- ok [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn- err [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn- tool-result-text [text]
  {:content [{:type "text" :text (str text)}]
   :isError false})

(defn keywordize-keys [m]
  (cond
    (map? m)        (into {} (map (fn [[k v]] [(keyword k) (keywordize-keys v)])) m)
    (sequential? m) (mapv keywordize-keys m)
    :else           m))

(defn handle-request
  "Dispatch a single decoded JSON-RPC request and return the response
  map. `dataset` is the in-memory dataset returned by `data/load-dataset`."
  [dataset {:keys [id method params] :as _req}]
  (case method
    "initialize"
    (ok id {:protocolVersion protocol-version
            :capabilities    {:tools {}}
            :serverInfo      {:name    "brazilian-soccer-mcp"
                              :version "0.1.0"}})

    "notifications/initialized"
    nil

    "ping"
    (ok id {})

    "tools/list"
    (ok id {:tools (tools/descriptors)})

    "tools/call"
    (let [{:keys [name arguments]} (or params {})]
      (if-not name
        (err id -32602 "Missing tool name")
        (let [text (tools/call dataset name (when arguments (keywordize-keys arguments)))]
          (ok id (tool-result-text text)))))

    (err id -32601 (str "Method not found: " method))))

(defn- read-line! [^java.io.BufferedReader in]
  (.readLine in))

(defn- write-json! [^java.io.Writer out msg]
  (locking out
    (.write out (json/generate-string msg))
    (.write out "\n")
    (.flush out)))

(defn serve!
  "Run the stdio MCP server loop. Reads newline-delimited JSON-RPC
   requests from `in` and writes responses to `out`. Returns when the
   input stream is closed."
  ([dataset]
   (serve! dataset System/in System/out))
  ([dataset in-stream out-stream]
   (let [in  (java.io.BufferedReader. (java.io.InputStreamReader. in-stream "UTF-8"))
         out (java.io.OutputStreamWriter. out-stream "UTF-8")]
     (loop []
       (let [line (read-line! in)]
         (cond
           (nil? line)         nil
           (str/blank? line)   (recur)
           :else
           (let [req (try (json/parse-string line true)
                          (catch Exception _ nil))]
             (if-not req
               (do (write-json! out (err nil -32700 "Parse error")) (recur))
               (let [resp (try (handle-request dataset req)
                               (catch Exception e
                                 (err (:id req) -32603 (.getMessage e))))]
                 (when resp (write-json! out resp))
                 (recur))))))))))
