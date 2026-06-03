(ns brazilian-soccer-mcp.core
  "Entry point. Two modes:
     clojure -M:run                 # MCP stdio server
     clojure -M:run --query <name>  # ad-hoc CLI query for smoke testing"
  (:require [brazilian-soccer-mcp.data    :as data]
            [brazilian-soccer-mcp.queries :as q]
            [brazilian-soccer-mcp.server  :as server]
            [clojure.string               :as str])
  (:gen-class))

(defn- usage []
  (binding [*out* *err*]
    (println "Usage:")
    (println "  clojure -M:run                       Start MCP stdio server")
    (println "  clojure -M:run --query stats <team>  Show team stats")
    (println "  clojure -M:run --query h2h a b       Head-to-head between two teams")
    (println "  clojure -M:run --query standings YEAR")))

(defn -main [& args]
  (cond
    (empty? args)
    (server/run-stdio)

    (= "--query" (first args))
    (let [db    (data/db)
          cmd   (second args)
          rest* (drop 2 args)]
      (case cmd
        "stats"     (println (q/format-team-stats (q/team-stats db (first rest*))))
        "h2h"       (let [h (q/head-to-head db (first rest*) (second rest*))]
                      (println (format "%s vs %s — %d matches: %s %d, %s %d, %d draws"
                                       (first rest*) (second rest*) (:total h)
                                       (first rest*) (:a-wins h)
                                       (second rest*) (:b-wins h) (:draws h))))
        "standings" (doseq [[i r] (map-indexed vector
                                               (take 20
                                                     (q/standings db (Long/parseLong (first rest*)))))]
                      (println (format "%2d. %-30s %2d pts" (inc i) (:team r) (:points r))))
        (usage)))

    :else (usage)))
