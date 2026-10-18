(ns brazil-soccer.tools-test
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [brazil-soccer.tools :as tools]
            [brazil-soccer.support :refer [real-db small-db]]))

(defn- run [db tool-name args]
  (let [tool (first (filter #(= tool-name (:name %)) (tools/tools db)))]
    ((:handler tool) args)))

(deftest every_tool_is_registered_with_a_schema
  (testing "Given the server, then it exposes the nine query tools with object schemas"
    (let [registry (tools/tools small-db)]
      (is (= #{"find_matches" "team_record" "head_to_head" "competition_standings"
               "team_rankings" "league_summary" "search_players"
               "brazilian_players_by_club" "team_profile"}
             (set (map :name registry))))
      (is (every? #(= "object" (get-in % [:inputSchema :type])) registry)))))

(deftest match_lines_are_formatted_for_the_model
  (testing "Given the small database, when I find Flamengo's matches, then each line gives date, score and competition"
    (let [out (run small-db "find_matches" {:team "Flamengo" :competition "Serie A" :season 2020})]
      (is (str/starts-with? out "4 matches found."))
      (is (str/includes? out "2020-03-08: Fluminense 0-0 Flamengo (Brasileirão Série A Round 2)"))))
  (testing "Given a head-to-head query, then the summary line gives both teams' wins and the draws"
    (let [out (run small-db "find_matches" {:team "Flamengo" :opponent "Fluminense"})]
      (is (str/includes? out "Head-to-head in these matches: Flamengo 2 wins, Fluminense 0 wins, 1 draws")))))

(deftest a_limit_truncates_with_a_note
  (testing "Given limit 1, then one match is listed and the rest are counted"
    (let [out (run small-db "find_matches" {:team "Flamengo" :limit 1})]
      (is (str/includes? out "... 6 more matches in dataset")))))

(deftest snake_case_arguments_are_accepted
  (testing "Given snake_case argument names from the model, then they are used"
    (let [out (run small-db "find_matches" {:competition "Copa do Brasil" :final_only true})]
      (is (str/includes? out "1 matches found.")))))

(deftest unknown_teams_report_no_matches
  (testing "Given a team that is not in the data, then the reply says so"
    (is (= "No matches found for Nowhere FC." 
           (run small-db "team_record" {:team "Nowhere FC"})))))

(deftest unknown_competitions_are_errors
  (testing "Given a competition that does not exist, then the tool fails with a helpful message"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"Unknown competition"
                          (run small-db "find_matches" {:competition "Premier League"})))))

(deftest standings_reply_lists_champion
  (testing "Given the real 2019 data, when I ask for the table, then the first line names Flamengo as champion on 90 points"
    (let [out (run @real-db "competition_standings" {:competition "Serie A" :season 2019})]
      (is (str/includes? out "1. Flamengo - 90 pts"))
      (is (str/ends-with? (first (filter #(str/starts-with? % "1. ") (str/split-lines out)))
                          "- Champion")))))

(deftest league_summary_reply_includes_key_figures
  (testing "Given 2023 Serie A, when I ask for a summary, then the average goals per match is reported"
    (let [out (run @real-db "league_summary" {:competition "Serie A" :season 2023})]
      (is (str/includes? out "Average goals per match: 2.47")))))

(deftest player_search_reply_lists_matches
  (testing "Given the small database, when I search for Brazilian players, then they are listed with ratings"
    (let [out (run small-db "search_players" {:nationality "Brazil" :limit 2})]
      (is (str/starts-with? out "4 players matched (showing 2)."))
      (is (str/includes? out "Alisson - Overall: 89")))))

(deftest team_profile_reply_has_sections
  (testing "Given the small database, when I profile Flamengo, then the reply has record, competition and squad sections"
    (let [out (run small-db "team_profile" {:team "Flamengo"})]
      (is (str/includes? out "Match record (all competitions):"))
      (is (str/includes? out "By competition:"))
      (is (str/includes? out "FIFA squad: 2 players (avg overall 79.0)")))))
