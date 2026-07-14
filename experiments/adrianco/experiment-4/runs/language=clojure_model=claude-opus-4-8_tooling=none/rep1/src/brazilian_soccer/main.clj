(ns brazilian-soccer.main
  "=============================================================================
   Brazilian Soccer MCP Server - Entry Point
   =============================================================================

   CONTEXT
     Process entry point. Loads the Brazilian soccer knowledge graph from the
     Kaggle CSVs (default \"data/kaggle\", overridable via the BRAZIL_SOCCER_DATA
     env var or the first CLI argument) and then starts the MCP stdio server.

     Because MCP communicates over stdout, the data-loading summary is logged to
     stderr so it never corrupts the JSON-RPC stream.

   USAGE
     clojure -M:run                 ; serve on stdio using data/kaggle
     clojure -M:run /path/to/data   ; serve using a custom data directory

   PUBLIC API
     -main  - load data and run the stdio server
   ============================================================================="
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.mcp :as mcp]
            [clojure.string :as str])
  (:gen-class))

(defn -main [& args]
  (let [data-dir (or (first args)
                     (System/getenv "BRAZIL_SOCCER_DATA")
                     data/default-data-dir)
        db (data/load-database data-dir)]
    (binding [*out* *err*]
      (println (format "Brazilian Soccer MCP server: loaded %d matches and %d players from %s"
                       (count (:matches db)) (count (:players db)) data-dir))
      (println (format "Competitions: %s"
                       (str/join ", " (sort (distinct (map :competition (:matches db))))))))
    (mcp/serve! db)))
