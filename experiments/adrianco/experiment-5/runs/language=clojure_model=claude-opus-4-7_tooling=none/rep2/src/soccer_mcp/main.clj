(ns soccer-mcp.main
  "Entry point: loads the dataset once and starts the MCP stdio server."
  (:require [soccer-mcp.data :as data]
            [soccer-mcp.server :as server])
  (:gen-class))

(defn -main [& args]
  (let [data-dir (or (first args) "data/kaggle")
        dataset  (data/load-all data-dir)]
    (server/run-stdio! dataset)))
