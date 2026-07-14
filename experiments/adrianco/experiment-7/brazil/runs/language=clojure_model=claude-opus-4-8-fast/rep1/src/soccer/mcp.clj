;; =============================================================================
;; soccer.mcp — Model Context Protocol server (stdio / JSON-RPC 2.0)
;; -----------------------------------------------------------------------------
;; Project: brazilian-soccer-mcp
;;
;; Context:
;;   Entry point.  Speaks the MCP stdio transport: newline-delimited JSON-RPC
;;   2.0 messages on stdin/stdout (logs go to stderr so they never corrupt the
;;   protocol stream).  Implements the handshake (initialize /
;;   notifications/initialized), tool discovery (tools/list) and tool execution
;;   (tools/call) by delegating to soccer.tools.
;;
;;   The dataset is loaded once at startup (soccer.data/load-db) and kept in
;;   memory, so every tool call is a fast in-process query.
;;
;; Run:  clojure -M:run         (then talk JSON-RPC over stdin/stdout)
;; =============================================================================
(ns soccer.mcp
  (:require [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [soccer.data :as data]
            [soccer.tools :as tools])
  (:gen-class))

(def ^:const protocol-version "2024-11-05")

(defn- log [& xs]
  (binding [*out* *err*] (apply println xs) (flush)))

;; --- response builders ------------------------------------------------------

(defn- result-msg [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn- error-msg [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn- text-content [s]
  {:content [{:type "text" :text s}]})

;; --- request handling -------------------------------------------------------

(defn handle-request
  "Handle a single decoded JSON-RPC request map against `db`.
   Returns a response map, or nil for notifications (no reply expected)."
  [db {:keys [method id params]}]
  (case method
    "initialize"
    (result-msg id {:protocolVersion protocol-version
                    :capabilities {:tools {}}
                    :serverInfo {:name "brazilian-soccer-mcp"
                                 :version "1.0.0"}})

    "notifications/initialized" nil
    "initialized" nil
    "ping" (result-msg id {})

    "tools/list"
    (result-msg id {:tools (vec tools/tool-specs)})

    "tools/call"
    (let [tool-name (or (get params "name") (get params :name))
          args      (or (get params "arguments") (get params :arguments) {})]
      (try
        (let [text (tools/call-tool db tool-name args)]
          (result-msg id (text-content text)))
        (catch clojure.lang.ExceptionInfo e
          (if (= ::tools/unknown-tool (:type (ex-data e)))
            (error-msg id -32601 (.getMessage e))
            (result-msg id (assoc (text-content (str "Error: " (.getMessage e)))
                                  :isError true))))
        (catch Exception e
          (log "tool error:" (.getMessage e))
          (result-msg id (assoc (text-content (str "Error: " (.getMessage e)))
                                :isError true)))))

    ;; unknown method
    (when id (error-msg id -32601 (str "Method not found: " method)))))

;; --- stdio loop -------------------------------------------------------------

(defn serve
  "Run the JSON-RPC stdio loop reading from `in` and writing to `out`."
  [db in out]
  (let [w (io/writer out)]
    (binding [*out* w]
      (doseq [line (line-seq (io/reader in))]
        (when-not (str/blank? line)
          (let [resp (try
                       (handle-request db (json/read-str line :key-fn keyword))
                       (catch Exception e
                         (log "parse/handle error:" (.getMessage e))
                         (error-msg nil -32700 "Parse error")))]
            (when resp
              (println (json/write-str resp))
              (flush))))))))

(defn -main [& _]
  (log "brazilian-soccer-mcp: loading datasets...")
  (let [db (data/load-db)]
    (log (format "brazilian-soccer-mcp: ready (%d matches, %d players)"
                 (count (:matches db)) (count (:players db))))
    (serve db System/in System/out)))
