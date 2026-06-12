;; =============================================================================
;; brsoccer.main
;;
;; Context:
;;   Entry point for the Brazilian Soccer MCP server. Eagerly loads the knowledge
;;   graph (so the first tool call is fast and any data error surfaces at startup
;;   on stderr), then serves the MCP JSON-RPC protocol over stdin/stdout.
;;
;;   Usage:  clojure -M:run
;;   The host application speaks newline-delimited JSON-RPC 2.0 on stdio.
;;   IMPORTANT: only protocol JSON is written to stdout; logs go to stderr.
;; =============================================================================
(ns brsoccer.main
  (:require [brsoccer.data :as data]
            [brsoccer.mcp :as mcp])
  (:import [java.io BufferedReader InputStreamReader])
  (:gen-class))

(defn -main [& _]
  (let [g (data/graph)]
    (binding [*out* *err*]
      (println (format "[brsoccer] knowledge graph loaded: %d matches, %d players, %d teams"
                       (count (:matches g)) (count (:players g)) (count (:teams g))))
      (println "[brsoccer] MCP server ready on stdio")
      (flush)))
  (let [in (BufferedReader. (InputStreamReader. System/in "UTF-8"))]
    (mcp/serve! in *out*)))
