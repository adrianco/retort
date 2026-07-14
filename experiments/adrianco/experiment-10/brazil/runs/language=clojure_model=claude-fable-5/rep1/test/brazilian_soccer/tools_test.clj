(ns brazilian-soccer.tools-test
  "CONTEXT
  =======
  BDD (Given/When/Then) tests for the MCP tool registry: schemas, formatted
  answers, error handling, the TASK.md success criteria of answering at
  least 20 sample questions, and the query-performance budget (simple
  lookups < 2s, aggregates < 5s, once data is loaded)."
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.string :as str]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.tools :as tools]))

(deftest tool-registry
  (testing "Given the tool registry
            When tools are listed for MCP
            Then each has a name, description and a JSON Schema, no handler"
    (let [listed (tools/list-tools)]
      (is (>= (count listed) 10))
      (doseq [t listed]
        (is (string? (:name t)))
        (is (seq (:description t)))
        (is (= "object" (get-in t [:inputSchema :type])))
        (is (contains? (:inputSchema t) :properties))
        (is (not (contains? t :handler)))))))

(deftest formatted-answers
  (testing "Given the example answer formats in TASK.md
            When tools are called
            Then responses contain the expected lines"
    (let [text #(get-in (tools/call-tool %1 %2) [:content 0 :text])]
      (testing "head-to-head answer has per-match lines and a summary"
        (let [t (text "head_to_head" {:team1 "Flamengo" :team2 "Fluminense"})]
          (is (str/includes? t "Flamengo vs Fluminense"))
          (is (str/includes? t "Head-to-head in dataset"))
          (is (re-find #"- \d{4}-\d{2}-\d{2}: .* \d+-\d+ .*" t))))
      (testing "team stats answer has the record block"
        (let [t (text "team_stats" {:team "Corinthians" :season 2022
                                    :competition "Brasileirao" :venue "home"})]
          (is (str/includes? t "- Matches: 19"))
          (is (str/includes? t "- Wins: 12, Draws: 4, Losses: 3"))
          (is (str/includes? t "Win rate:"))))
      (testing "standings answer is a ranked table with a champion"
        (let [t (text "league_standings" {:season 2019})]
          (is (str/includes? t " 1. Flamengo - 90 pts (28W, 6D, 4L"))
          (is (str/includes? t "Champion: Flamengo"))))
      (testing "competition stats answer has averages"
        (let [t (text "competition_stats" {:competition "Brasileirao"})]
          (is (str/includes? t "Average goals per match:"))
          (is (str/includes? t "Home wins:")))))))

(deftest error-handling
  (testing "Given a tool call
            When the tool does not exist
            Then call-tool returns nil (the server maps this to -32602)"
    (is (nil? (tools/call-tool "no_such_tool" {}))))
  (testing "When criteria match nothing
            Then a friendly message comes back rather than an error"
    (let [r (tools/call-tool "search_matches" {:team "Nonexistent United FC"})]
      (is (false? (:isError r)))
      (is (str/includes? (get-in r [:content 0 :text]) "No matches found")))))

(def sample-questions
  "20+ sample questions from TASK.md and the tool calls that answer them."
  [["Show me all Flamengo vs Fluminense matches"
    "head_to_head" {:team1 "Flamengo" :team2 "Fluminense"}]
   ["What matches did Palmeiras play in 2023?"
    "search_matches" {:team "Palmeiras" :season 2023}]
   ["Find all Copa Libertadores finals"
    "search_matches" {:competition "Libertadores" :stage "final"}]
   ["When did Flamengo last play Corinthians (and what was the score)?"
    "search_matches" {:team "Flamengo" :opponent "Corinthians" :limit 50}]
   ["What is Corinthians' home record in 2022?"
    "team_stats" {:team "Corinthians" :season 2022 :venue "home"}]
   ["How did Palmeiras do in 2023?"
    "team_stats" {:team "Palmeiras" :season 2023}]
   ["What is Santos' away record?"
    "team_stats" {:team "Santos" :venue "away"}]
   ["Compare Palmeiras and Santos head-to-head"
    "head_to_head" {:team1 "Palmeiras" :team2 "Santos"}]
   ["Who won the 2019 Brasileirão?"
    "league_standings" {:season 2019}]
   ["Who won the 2003 Brasileirão?"
    "league_standings" {:season 2003}]
   ["Which teams were relegated in 2020?"
    "league_standings" {:season 2020}]
   ["Which team scored the most goals in Serie A 2023?"
    "league_standings" {:season 2023}]
   ["Who is Neymar?"
    "search_players" {:name "Neymar"}]
   ["Find Brazilian players rated 85 or better"
    "search_players" {:nationality "Brazil" :min_overall 85}]
   ["Which players play for Fluminense?"
    "search_players" {:club "Fluminense"}]
   ["Show me all goalkeepers from Brazil"
    "search_players" {:nationality "Brazil" :position "GK"}]
   ["Who are the top Brazilian players?"
    "top_players" {:nationality "Brazil"}]
   ["Brazilian players per club with average ratings"
    "club_player_summary" {:nationality "Brazil" :min_players 3}]
   ["What's the average goals per match in the Brasileirão?"
    "competition_stats" {:competition "Brasileirao"}]
   ["Compare the 2018 and 2019 seasons"
    "competition_stats" {:season 2018}]
   ["Show me the biggest wins in the dataset"
    "biggest_wins" {:limit 10}]
   ["What competitions are covered?"
    "list_competitions" {}]
   ["What data is loaded?"
    "data_summary" {}]])

(deftest twenty-sample-questions
  (testing "Given the success criteria in TASK.md
            When at least 20 sample questions are asked via the tools
            Then every one yields a substantive, non-error answer"
    (is (>= (count sample-questions) 20))
    (doseq [[question tool args] sample-questions]
      (let [r (tools/call-tool tool args)]
        (is (some? r) question)
        (is (false? (:isError r)) question)
        (is (> (count (get-in r [:content 0 :text])) 20) question)))))

(deftest query-performance
  (testing "Given the database is already loaded
            When simple and aggregate queries run
            Then they finish inside the TASK.md budgets (2s / 5s)"
    (data/db) ; warm the cache; load time is excluded as per 'query performance'
    (let [t0 (System/nanoTime)
          _ (tools/call-tool "search_matches" {:team "Flamengo" :opponent "Corinthians"})
          simple-ms (/ (- (System/nanoTime) t0) 1e6)
          t1 (System/nanoTime)
          _ (tools/call-tool "league_standings" {:season 2019})
          _ (tools/call-tool "competition_stats" {})
          aggregate-ms (/ (- (System/nanoTime) t1) 1e6)]
      (is (< simple-ms 2000.0) (str "simple lookup took " simple-ms "ms"))
      (is (< aggregate-ms 5000.0) (str "aggregates took " aggregate-ms "ms")))))
