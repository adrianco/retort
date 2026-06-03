(ns soccer.main
  "=============================================================================
   soccer.main — Entry point
   -----------------------------------------------------------------------------
   Usage:
     clojure -M -m soccer.main            # start the MCP stdio server
     clojure -M -m soccer.main --demo     # print answers to sample questions
     clojure -M -m soccer.main --help

   On startup the datasets are loaded into memory once (a few seconds) and then
   either the JSON-RPC stdio loop runs (MCP mode) or a set of demonstration
   queries from the spec are printed (demo mode). All diagnostic output goes to
   stderr so stdout stays a clean JSON-RPC channel in MCP mode.
   ============================================================================="
  (:require [soccer.data :as data]
            [soccer.queries :as q]
            [soccer.format :as fmt]
            [soccer.mcp :as mcp])
  (:gen-class))

(defn- eprintln [& xs] (binding [*out* *err*] (apply println xs)))

(defn run-demo [db]
  (let [section (fn [title] (println (str "\n=== " title " ===")))]
    (section "Flamengo vs Fluminense (Fla-Flu)")
    (println (fmt/head-to-head (q/head-to-head db {:team1 "Flamengo" :team2 "Fluminense"})))

    (section "Palmeiras matches in 2019 (first 5)")
    (println (fmt/matches (q/search-matches db {:team "Palmeiras" :season 2019 :limit 5})))

    (section "Corinthians home record, 2019 Brasileirão")
    (println (fmt/team-stats (q/team-stats db {:team "Corinthians" :season 2019
                                               :competition "Brasileirão" :venue :home})))

    (section "2019 Brasileirão final standings (top 6)")
    (let [opts {:competition "Brasileirão Série A" :season 2019}]
      (println (fmt/standings (take 6 (q/standings db opts)) opts)))

    (section "Brasileirão 2019 league statistics")
    (println (fmt/league-stats (q/league-stats db {:competition "Brasileirão Série A" :season 2019})))

    (section "Biggest wins in Libertadores (top 5)")
    (println (fmt/biggest-wins (q/biggest-wins db {:competition "Libertadores" :limit 5})))

    (section "Top Brazilian players (top 10)")
    (println (fmt/players (q/search-players db {:nationality "Brazil" :limit 10})))

    (section "Highest-rated players at a Brazilian club (Santos)")
    (println (fmt/players (q/search-players db {:club "Santos" :limit 8})))

    (section "Search player by name: Gabriel Jesus")
    (println (fmt/players (q/search-players db {:name "Gabriel Jesus"})))))

(defn -main [& args]
  (eprintln "Loading Brazilian soccer datasets...")
  (let [db (data/db)]
    (eprintln (format "Loaded %d matches and %d players."
                      (count (:matches db)) (count (:players db))))
    (cond
      (some #{"--help" "-h"} args)
      (do (println "Brazilian Soccer MCP Server")
          (println "  (no args)  start MCP stdio server")
          (println "  --demo     print sample-question answers")
          (println "  --help     this message"))

      (some #{"--demo"} args)
      (run-demo db)

      :else
      (do (eprintln "Brazilian Soccer MCP server ready (JSON-RPC over stdio).")
          (mcp/serve! db)))))
