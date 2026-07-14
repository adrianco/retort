(ns soccer.server
  "MCP server for Brazilian soccer data.

   Speaks JSON-RPC 2.0 (the Model Context Protocol) over stdio.  `create-server`
   loads a dataset directory into memory; `process-line` is the public protocol
   boundary — a JSON-RPC request string in, a JSON-RPC response string out —
   used both by `-main` (stdio loop) and by the acceptance tests.  `-main`
   starts the read/write loop against stdin/stdout."
  (:require [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [soccer.data :as data]
            [soccer.tools :as tools])
  (:gen-class))

(def ^:private protocol-version "2024-11-05")

(defn create-server
  "Load `data-dir` and return a server value usable with `process-line`."
  [data-dir]
  {:dataset (data/load-dataset data-dir)})

;; ---------------------------------------------------------------------------
;; JSON-RPC request handling
;; ---------------------------------------------------------------------------

(defn- result [id value] {:jsonrpc "2.0" :id id :result value})
(defn- error [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn- handle-tools-call [server id params]
  (let [tool-name (:name params)
        args (or (:arguments params) {})
        tool (get tools/by-name tool-name)]
    (if tool
      (try
        (let [text ((:handler tool) (:dataset server) args)]
          (result id {:content [{:type "text" :text text}]}))
        (catch Exception e
          (error id -32603 (str "Tool execution error: " (.getMessage e)))))
      (error id -32601 (str "Unknown tool: " tool-name)))))

(defn handle-request
  "Handle a parsed JSON-RPC request map; return a response map (or nil for
   notifications that take no reply)."
  [server {:keys [id method params]}]
  (case method
    "initialize"
    (result id {:protocolVersion protocol-version
                :capabilities {:tools {}}
                :serverInfo {:name "brazilian-soccer-mcp" :version "1.0.0"}})

    "tools/list"
    (result id {:tools (tools/public-list)})

    "tools/call"
    (handle-tools-call server id params)

    "ping"
    (result id {})

    ;; Notifications (method starting with "notifications/") expect no reply.
    (if (and method (str/starts-with? method "notifications/"))
      nil
      (error id -32601 (str "Unknown method: " method)))))

(defn process-line
  "Public protocol boundary: parse one JSON-RPC line, handle it, and return the
   JSON-RPC response line (or nil for notifications)."
  [server line]
  (let [req (json/read-str line :key-fn keyword)
        resp (handle-request server req)]
    (when resp (json/write-str resp))))

;; ---------------------------------------------------------------------------
;; stdio loop
;; ---------------------------------------------------------------------------

(defn -main [& args]
  (let [data-dir (or (first args) (System/getenv "SOCCER_DATA_DIR") "data/kaggle")
        server (create-server data-dir)
        out (io/writer System/out)]
    (binding [*out* out]
      (with-open [r (io/reader System/in)]
        (doseq [line (line-seq r)]
          (when (seq (str/trim line))
            (when-let [resp (process-line server line)]
              (.write out (str resp "\n"))
              (.flush out))))))))
