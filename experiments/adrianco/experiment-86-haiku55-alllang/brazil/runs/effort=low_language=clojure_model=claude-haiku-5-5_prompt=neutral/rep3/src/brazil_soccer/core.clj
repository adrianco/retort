(ns brazil-soccer.core
  "Entry point: loads the Brazilian soccer datasets and serves MCP over stdio.
  Set BRAZIL_SOCCER_DATA to point at a different data directory."
  (:require [brazil-soccer.data :as data]
            [brazil-soccer.mcp :as mcp]
            [brazil-soccer.tools :as tools])
  (:gen-class))

(defn -main [& _]
  (let [data-dir (or (System/getenv "BRAZIL_SOCCER_DATA") data/default-data-dir)
        started (System/nanoTime)
        db (data/load-db data-dir)]
    ;; stdout carries the protocol, so diagnostics go to stderr.
    (binding [*out* *err*]
      (println (format "Loaded %d matches and %d players from %s in %d ms"
                       (count (:matches db)) (count (:players db)) data-dir
                       (quot (- (System/nanoTime) started) 1000000))))
    (mcp/serve *in* *out* (tools/tools db))))
