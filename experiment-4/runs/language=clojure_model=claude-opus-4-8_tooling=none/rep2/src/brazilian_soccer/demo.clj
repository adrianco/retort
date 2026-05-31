(ns brazilian-soccer.demo
  "Context
  =======
  A runnable demonstration that answers 20+ of the spec's sample questions by
  invoking the MCP tools exactly as an LLM client would (via
  `brazilian-soccer.mcp/call-tool`). Run with:  clojure -M:demo

  This doubles as living documentation of the server's capabilities and a quick
  manual smoke test that every query category produces sensible output."
  (:require [brazilian-soccer.mcp :as mcp]
            [brazilian-soccer.data :as data]))

;; Each entry: [question tool args]
(def questions
  [["Show me all Flamengo vs Fluminense matches"
    "find_matches" {:team "Flamengo" :opponent "Fluminense" :limit 5}]
   ["What matches did Palmeiras play in 2019?"
    "find_matches" {:team "Palmeiras" :season 2019 :limit 5}]
   ["When did Flamengo last play Corinthians?"
    "find_matches" {:team "Flamengo" :opponent "Corinthians" :limit 1}]
   ["Find all Copa do Brasil matches in 2022"
    "find_matches" {:competition "Copa do Brasil" :season 2022 :limit 4}]
   ["What is Corinthians' home record in 2019?"
    "team_record" {:team "Corinthians" :season 2019
                   :competition "Brasileirão Série A" :venue "home"}]
   ["What is Palmeiras' overall 2019 Brasileirão record?"
    "team_record" {:team "Palmeiras" :season 2019 :competition "Brasileirão Série A"}]
   ["Compare Palmeiras and Santos head-to-head"
    "head_to_head" {:team1 "Palmeiras" :team2 "Santos"}]
   ["Fla-Flu derby head-to-head"
    "head_to_head" {:team1 "Flamengo" :team2 "Fluminense"}]
   ["Who won the 2019 Brasileirão?"
    "standings" {:competition "Brasileirão Série A" :season 2019}]
   ["Show the 2008 Brasileirão final standings"
    "standings" {:competition "Brasileirão Série A" :season 2008}]
   ["What's the average goals per match in the 2019 Brasileirão?"
    "league_stats" {:competition "Brasileirão Série A" :season 2019}]
   ["Show me the biggest wins in the Brasileirão"
    "biggest_wins" {:competition "Brasileirão Série A" :limit 5}]
   ["Who is Neymar?"
    "search_players" {:name "Neymar"}]
   ["Find the top Brazilian players"
    "search_players" {:nationality "Brazil" :limit 5}]
   ["Who are the highest-rated goalkeepers?"
    "search_players" {:position "GK" :limit 5}]
   ["Which players play for Santos?"
    "search_players" {:club "Santos" :nationality "Brazil" :limit 5}]
   ["Top-rated players with overall >= 90"
    "search_players" {:min-overall 90 :limit 5}]
   ["Brazilian players grouped by club"
    "club_nationality_breakdown" {:nationality "Brazil" :limit 6}]
   ["What competitions are in the data?"
    "list_competitions" {}]
   ["Which seasons of the Brasileirão are available?"
    "list_seasons" {:competition "Brasileirão Série A"}]
   ["Copa Libertadores matches in 2019"
    "find_matches" {:competition "Libertadores" :season 2019 :limit 4}]
   ["Compare the 2018 and 2019 Brasileirão (2018 stats)"
    "league_stats" {:competition "Brasileirão Série A" :season 2018}]])

(defn -main [& _]
  (println "Loading datasets...")
  (printf "Loaded %d matches and %d players.\n\n"
          (count (data/matches)) (count (data/players)))
  (doseq [[i [q tool args]] (map-indexed vector questions)]
    (println (format "Q%02d. %s" (inc i) q))
    (println (str "     [tool: " tool " " args "]"))
    (println (->> (mcp/call-tool tool args)
                  clojure.string/split-lines
                  (map #(str "     " %))
                  (clojure.string/join "\n")))
    (println)))
