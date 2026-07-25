(ns brazilian-soccer.server
  "Entry point launched by an MCP client: `clojure -M:mcp`.

  CONTEXT
  -------
  stdout belongs to the JSON-RPC transport, so every human readable message
  goes to stderr.  The CSV files are parsed *before* the first request is read
  (about half a second) so that no query ever pays the loading cost - the
  specification asks for simple lookups under two seconds."
  (:gen-class)
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.mcp :as mcp]))

(defn -main [& args]
  (let [dir (or (first args) (data/default-data-dir))]
    (binding [*out* *err*]
      (println "brazilian-soccer MCP server starting, data directory:" dir))
    (let [started (System/currentTimeMillis)
          db (data/load-db dir)]
      (binding [*out* *err*]
        (println (format "loaded %d matches, %d clubs and %d players in %d ms"
                         (count (:matches db)) (count (:teams db)) (count (:players db))
                         (- (System/currentTimeMillis) started)))
        (println "listening for MCP JSON-RPC on stdin"))
      (mcp/serve db System/in System/out))))
