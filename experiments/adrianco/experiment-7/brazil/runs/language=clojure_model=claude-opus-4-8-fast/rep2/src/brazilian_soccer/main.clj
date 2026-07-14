(ns brazilian-soccer.main
  "=============================================================================
   main.clj — Entry point for the Brazilian Soccer MCP server
   -----------------------------------------------------------------------------
   Context:
     Boots the in-memory knowledge graph (parsing the Kaggle CSVs once) and
     then serves the MCP protocol over stdio. Diagnostic output goes to stderr
     so it never corrupts the JSON-RPC stream on stdout.

   Run with:  clojure -M:run
   ============================================================================="
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.mcp :as mcp])
  (:import [java.io BufferedReader InputStreamReader])
  (:gen-class))

(defn -main [& _args]
  (binding [*out* *err*]
    (let [db (data/db)]
      (println (format "[brazilian-soccer-mcp] loaded %d matches, %d players"
                       (count (:matches db)) (count (:players db))))
      (println "[brazilian-soccer-mcp] ready — listening on stdio")))
  (let [in  (BufferedReader. (InputStreamReader. System/in "UTF-8"))
        out (java.io.OutputStreamWriter. System/out "UTF-8")]
    (mcp/serve! in out)))
