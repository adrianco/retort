(ns brazilian-soccer.main
  "Context
  =======
  Entry point and stdio transport for the Brazilian Soccer MCP server.

  Reads newline-delimited JSON-RPC 2.0 messages from stdin, dispatches each to
  `brazilian-soccer.mcp/handle-request`, and writes JSON responses to stdout
  (one per line). Log/diagnostic output goes to stderr so it never corrupts the
  protocol stream. Run with:  clojure -M:server"
  (:require [cheshire.core :as json]
            [clojure.java.io :as io]
            [brazilian-soccer.mcp :as mcp]
            [brazilian-soccer.data :as data])
  (:gen-class))

(defn- log [& xs]
  (binding [*out* *err*]
    (apply println xs)
    (flush)))

(defn- write-message! [^java.io.Writer out msg]
  (locking out
    (.write out (json/generate-string msg))
    (.write out "\n")
    (.flush out)))

(defn process-line
  "Decode one JSON-RPC line, handle it, and return the response map (or nil)."
  [line]
  (let [req (json/parse-string line true)]
    (mcp/handle-request req)))

(defn -main [& _]
  (log "[brazilian-soccer-mcp] starting; loading datasets...")
  (let [{:keys [matches players]} @data/db]
    (log (format "[brazilian-soccer-mcp] loaded %d matches and %d players."
                 (count matches) (count players))))
  (let [out *out*
        reader (io/reader System/in)]
    (loop []
      (when-let [line (.readLine ^java.io.BufferedReader reader)]
        (when (seq (.trim ^String line))
          (try
            (when-let [resp (process-line line)]
              (write-message! out resp))
            (catch Exception e
              (log "[brazilian-soccer-mcp] error:" (.getMessage e))
              (write-message! out {:jsonrpc "2.0" :id nil
                                   :error {:code -32700
                                           :message (str "Parse/handler error: " (.getMessage e))}}))))
        (recur)))
    (log "[brazilian-soccer-mcp] stdin closed; exiting.")))
