(ns brazilian-soccer-mcp.core
  (:require [brazilian-soccer-mcp.mcp :as mcp])
  (:gen-class))

(defn -main
  "Entry point: starts the MCP server reading from stdin and writing to stdout.
   Optionally accepts a data directory path as first arg (default: data/kaggle)."
  [& args]
  (let [data-dir (or (first args) "data/kaggle")]
    (binding [*err* *out*]
      (mcp/run-server! data-dir))))
