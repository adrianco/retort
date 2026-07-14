(ns brazilian-soccer-mcp.core
  "Entry point for the Brazilian soccer MCP server. Loads CSV data into
  memory once at startup and then services MCP requests over stdio."
  (:require [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.mcp  :as mcp]
            [clojure.string :as str])
  (:gen-class))

(defn- log [& parts]
  ;; All non-protocol output must go to stderr so that stdout stays clean
  ;; for JSON-RPC framing.
  (binding [*out* *err*]
    (apply println parts)))

(defn -main [& args]
  (let [dir (or (some (fn [a] (when (str/starts-with? a "--data=") (subs a 7))) args)
                "data/kaggle")]
    (log "[brazilian-soccer-mcp] loading data from" dir)
    (let [ds (data/load-dataset dir)
          summary (data/dataset-summary ds)]
      (log "[brazilian-soccer-mcp] ready —"
           (:matches summary) "matches,"
           (:players summary) "players,"
           (count (:competitions summary)) "competitions")
      (mcp/serve! ds))))
