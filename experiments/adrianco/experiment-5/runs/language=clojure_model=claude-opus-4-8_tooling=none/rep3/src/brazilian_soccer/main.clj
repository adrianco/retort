;; =============================================================================
;; brazilian-soccer.main
;; -----------------------------------------------------------------------------
;; Entry point for the Brazilian Soccer MCP server.
;;
;; Usage:
;;   clojure -M -m brazilian-soccer.main
;;
;; Speaks the MCP stdio protocol (JSON-RPC 2.0, newline-delimited) on stdin/
;; stdout. Datasets are eagerly loaded at startup so the first query is fast.
;; Startup diagnostics are written to stderr to keep stdout a clean protocol
;; channel.
;; =============================================================================
(ns brazilian-soccer.main
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.mcp :as mcp])
  (:import [java.io BufferedReader InputStreamReader OutputStreamWriter])
  (:gen-class))

(defn -main [& _args]
  (binding [*out* *err*]
    (let [{:keys [matches players]} @data/db]
      (println "brazilian-soccer-mcp: loaded"
               (count matches) "matches and"
               (count players) "players. Ready on stdio.")))
  (let [in  (BufferedReader. (InputStreamReader. System/in "UTF-8"))
        out (OutputStreamWriter. System/out "UTF-8")]
    (mcp/serve in out)))
