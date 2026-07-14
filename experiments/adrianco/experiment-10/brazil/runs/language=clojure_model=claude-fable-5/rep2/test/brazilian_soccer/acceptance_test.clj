(ns brazilian-soccer.acceptance-test
  "Acceptance scenarios from the specification's success criteria:
  at least 20 sample questions answerable through the MCP tools, each
  within the required response-time budget (<2s simple, <5s aggregate)."
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.tools :as tools]))

(def sample-questions
  "Question -> [tool arguments substring-expected-in-answer]"
  [["Show me all Flamengo vs Fluminense matches"
    "search_matches" {"team" "Flamengo" "opponent" "Fluminense"} "Flamengo"]
   ["What matches did Palmeiras play in 2023?"
    "search_matches" {"team" "Palmeiras" "season" 2023} "Palmeiras"]
   ["Find all Copa do Brasil finals (e.g. 2012)"
    "search_matches" {"competition" "copa do brasil" "stage" "final" "season" 2012} "final"]
   ["When did Flamengo last play Corinthians?"
    "search_matches" {"team" "Flamengo" "opponent" "Corinthians" "limit" 1} "Flamengo"]
   ["Show me Libertadores knockout matches in 2019"
    "search_matches" {"competition" "libertadores" "season" 2019 "stage" "semi"} "Copa Libertadores"]
   ["What matches were played between June and July 2014?"
    "search_matches" {"date_from" "2014-06-01" "date_to" "2014-07-31" "limit" 5} "2014"]
   ["What is Corinthians' home record in 2022?"
    "get_team_stats" {"team" "Corinthians" "season" 2022 "venue" "home"
                      "competition" "brasileirao"} "Wins"]
   ["How did São Paulo do away from home in 2019?"
    "get_team_stats" {"team" "Sao Paulo" "season" 2019 "venue" "away"
                      "competition" "serie a"} "São Paulo away record"]
   ["Compare Palmeiras and Santos head-to-head"
    "head_to_head" {"team1" "Palmeiras" "team2" "Santos"} "Head-to-head record"]
   ["Compare Grêmio and Internacional (Gre-Nal derby)"
    "head_to_head" {"team1" "Gremio" "team2" "Internacional"} "Grêmio"]
   ["Who won the 2019 Brasileirão?"
    "get_standings" {"season" 2019} "Flamengo - 90 pts"]
   ["Show the 2015 Brasileirão final standings"
    "get_standings" {"season" 2015} "Corinthians"]
   ["Which teams were relegated in 2020?"
    "get_standings" {"season" 2020} "20."]
   ["Find all Brazilian players in the dataset"
    "search_players" {"nationality" "Brazil" "limit" 10} "Neymar"]
   ["Who are the highest-rated players at Cruzeiro?"
    "search_players" {"club" "Cruzeiro" "limit" 5} "Cruzeiro"]
   ["Show me goalkeepers from Grêmio"
    "search_players" {"club" "Grêmio" "position" "GK"} "GK"]
   ["Who is Casemiro?"
    "get_player" {"name" "Casemiro"} "Real Madrid"]
   ["Who is Gabriel Jesus?"
    "get_player" {"name" "Gabriel Jesus"} "Brazil"]
   ["What's the average goals per match in the Brasileirão?"
    "get_competition_stats" {"competition" "brasileirao"} "Average goals per match"]
   ["How often does the home team win in the Libertadores?"
    "get_competition_stats" {"competition" "libertadores"} "Home wins"]
   ["Show me the biggest wins in the dataset"
    "get_biggest_wins" {"limit" 5} "margin"]
   ["Which teams played Serie A in 2003?"
    "list_teams" {"competition" "serie a" "season" 2003} "Cruzeiro"]])

(deftest scenario-twenty-plus-sample-questions
  (testing "Given the full dataset is loaded
            When each sample question is answered via its MCP tool
            Then every answer contains the expected information"
    (is (>= (count sample-questions) 20))
    (doseq [[question tool args expected] sample-questions]
      (let [{:keys [content isError]} (tools/call-tool tool args)
            text (:text (first content))]
        (is (false? isError) question)
        (is (and text (str/includes? text expected))
            (str question " — expected answer to contain " (pr-str expected)
                 ", got: " (pr-str (some-> text (subs 0 (min 200 (count text)))))))))))

(deftest scenario-query-performance
  (testing "Given the datasets are already loaded
            When simple and aggregate queries run
            Then they finish well inside the 2s / 5s budgets"
    @data/all-matches
    @data/all-players
    (let [timed (fn [tool args]
                  (let [start (System/nanoTime)]
                    (tools/call-tool tool args)
                    (/ (- (System/nanoTime) start) 1e6)))]
      (is (< (timed "search_matches" {"team" "Flamengo"}) 2000.0))
      (is (< (timed "get_player" {"name" "Neymar"}) 2000.0))
      (is (< (timed "get_standings" {"season" 2019}) 5000.0))
      (is (< (timed "get_competition_stats" {}) 5000.0)))))

(deftest scenario-cross-file-queries
  (testing "Given match data and player data from different files
            When a club appears in both
            Then both match history and squad can be retrieved"
    (let [matches (:text (first (:content (tools/call-tool
                                           "search_matches"
                                           {"team" "Cruzeiro" "limit" 3}))))
          squad (:text (first (:content (tools/call-tool
                                         "search_players"
                                         {"club" "Cruzeiro" "limit" 3}))))]
      (is (str/includes? matches "Cruzeiro"))
      (is (str/includes? squad "Cruzeiro")))))
