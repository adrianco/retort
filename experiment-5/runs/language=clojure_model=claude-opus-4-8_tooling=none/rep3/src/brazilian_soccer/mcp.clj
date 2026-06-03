;; =============================================================================
;; brazilian-soccer.mcp
;; -----------------------------------------------------------------------------
;; Minimal Model Context Protocol (MCP) server over the stdio transport.
;;
;; Transport  : newline-delimited JSON-RPC 2.0 messages on stdin/stdout.
;; Lifecycle  : initialize -> notifications/initialized -> tools/list / tools/call
;;
;; Implemented methods:
;;   initialize                -> protocol/version + capabilities + serverInfo
;;   notifications/initialized -> (no response; notification)
;;   ping                      -> {}
;;   tools/list                -> {:tools [...]} from tools/list-tools
;;   tools/call                -> {:content [...]} from tools/call-tool
;;
;; Notifications (no :id) never produce a response. Unknown methods return a
;; JSON-RPC error (-32601). Each parsed line is handled independently so a bad
;; message cannot crash the loop.
;;
;; References: https://modelcontextprotocol.io
;; =============================================================================
(ns brazilian-soccer.mcp
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [brazilian-soccer.tools :as tools])
  (:import [java.io BufferedReader Writer]))

(def protocol-version "2024-11-05")

(def server-info
  {:name "brazilian-soccer-mcp" :version "1.0.0"})

(defn- result-msg [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn- error-msg [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn handle-request
  "Pure request router. Takes a parsed JSON-RPC message map (keyword keys) and
   returns a response map to send, or nil for notifications / no-reply."
  [{:keys [id method params]}]
  (case method
    "initialize"
    (result-msg id {:protocolVersion protocol-version
                    :capabilities    {:tools {}}
                    :serverInfo      server-info})

    ("notifications/initialized" "initialized" "notifications/cancelled")
    nil

    "ping"
    (result-msg id {})

    "tools/list"
    (result-msg id {:tools (tools/list-tools)})

    "tools/call"
    (let [tool-name (get params "name")
          arguments (get params "arguments")]
      (result-msg id (tools/call-tool tool-name arguments)))

    ;; default
    (when id
      (error-msg id -32601 (str "Method not found: " method)))))

(defn- write-msg! [^Writer out msg]
  (when msg
    (locking out
      (.write out (json/write-str msg))
      (.write out "\n")
      (.flush out))))

(defn- parse-line [line]
  ;; key-fn keeps top-level JSON-RPC fields as keywords; params stay
  ;; string-keyed (tool arguments use arbitrary string keys).
  (json/read-str line
                 :key-fn (fn [k]
                           (if (#{"jsonrpc" "id" "method" "params"} k)
                             (keyword k) k))))

(defn serve
  "Run the stdio MCP loop reading from `in` (BufferedReader) and writing to
   `out` (Writer). Returns when stdin reaches EOF."
  [^BufferedReader in ^Writer out]
  (loop []
    (when-let [line (.readLine in)]
      (when-not (str/blank? line)
        (let [resp (try
                     (handle-request (parse-line line))
                     (catch Exception e
                       (error-msg nil -32700
                                  (str "Parse/handler error: " (.getMessage e)))))]
          (write-msg! out resp)))
      (recur))))
