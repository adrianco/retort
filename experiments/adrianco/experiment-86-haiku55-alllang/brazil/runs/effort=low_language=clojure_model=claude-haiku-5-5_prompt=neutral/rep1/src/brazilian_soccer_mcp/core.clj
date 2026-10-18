(ns brazilian-soccer-mcp.core
  "Entry point: loads the Kaggle data and serves MCP over stdio.

  Usage: clojure -M:server [data-dir]
  The data directory defaults to $BSM_DATA_DIR, then data/kaggle."
  (:require [clojure.java.io :as io]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.mcp :as mcp])
  (:gen-class))

(defn -main [& args]
  (let [dir (or (first args) (System/getenv "BSM_DATA_DIR") "data/kaggle")
        db (data/load-dataset dir)]
    (binding [*out* *err*]
      (println (str "Loaded " (count (:matches db)) " matches and "
                    (count (:players db)) " players from " dir)))
    (mcp/serve db
               (io/reader System/in :encoding "UTF-8")
               (io/writer System/out :encoding "UTF-8"))))
