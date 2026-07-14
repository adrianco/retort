(ns brazilian-soccer-mcp.tools-test
  (:require [clojure.test :refer :all]
            [clojure.string :as str]
            [brazilian-soccer-mcp.tools :as tools]))

(def sample-matches
  [{:home-team "Flamengo" :away-team "Palmeiras" :home-goal 2 :away-goal 1
    :season 2023 :competition "brasileirao" :round 22
    :date (java.time.LocalDate/of 2023 9 3)}
   {:home-team "Fluminense" :away-team "Flamengo" :home-goal 1 :away-goal 0
    :season 2023 :competition "brasileirao" :round 8
    :date (java.time.LocalDate/of 2023 5 28)}
   {:home-team "Flamengo" :away-team "Corinthians" :home-goal 0 :away-goal 0
    :season 2022 :competition "brasileirao" :round 5
    :date (java.time.LocalDate/of 2022 4 10)}
   {:home-team "Santos" :away-team "Flamengo" :home-goal 1 :away-goal 3
    :season 2023 :competition "copa-do-brasil" :round "semi-final"
    :date (java.time.LocalDate/of 2023 8 10)}])

(def sample-players
  [{:id "1" :name "Gabriel Barbosa" :nationality "Brazil" :overall 82 :position "ST" :club "Flamengo" :age 26}
   {:id "2" :name "Bruno Henrique" :nationality "Brazil" :overall 80 :position "LW" :club "Flamengo" :age 32}
   {:id "3" :name "L. Messi" :nationality "Argentina" :overall 94 :position "RF" :club "FC Barcelona" :age 31}])

(deftest find-matches-tool-test
  (testing "returns text content for team matches"
    (let [result (tools/call-find-matches sample-matches {"team" "Flamengo"})]
      (is (string? result))
      (is (str/includes? result "Flamengo"))
      (is (str/includes? result "4 match"))))

  (testing "returns text for no results"
    (let [result (tools/call-find-matches sample-matches {"team" "Grêmio"})]
      (is (string? result))
      (is (str/includes? result "No matches"))))

  (testing "head-to-head between two teams"
    (let [result (tools/call-find-matches sample-matches {"team1" "Flamengo" "team2" "Palmeiras"})]
      (is (string? result))
      (is (str/includes? result "Flamengo"))
      (is (str/includes? result "Palmeiras")))))

(deftest team-stats-tool-test
  (testing "returns stats for a team"
    (let [result (tools/call-team-stats sample-matches "Flamengo" nil nil)]
      (is (string? result))
      (is (str/includes? result "Flamengo"))
      (is (str/includes? result "Wins"))
      (is (str/includes? result "Draws"))
      (is (str/includes? result "Losses"))))

  (testing "handles unknown team"
    (let [result (tools/call-team-stats sample-matches "Grêmio" nil nil)]
      (is (string? result))
      (is (str/includes? result "No matches")))))

(deftest find-players-tool-test
  (testing "returns formatted player list"
    (let [result (tools/call-find-players sample-players {"nationality" "Brazil"})]
      (is (string? result))
      (is (str/includes? result "Gabriel Barbosa"))
      (is (str/includes? result "Brazil"))))

  (testing "returns text when no players found"
    (let [result (tools/call-find-players sample-players {"nationality" "France"})]
      (is (string? result))
      (is (str/includes? result "No players")))))

(deftest standings-tool-test
  (testing "returns formatted standings"
    (let [result (tools/call-standings sample-matches nil nil)]
      (is (string? result))
      (is (str/includes? result "pts"))
      (is (str/includes? result "W"))
      (is (str/includes? result "D"))
      (is (str/includes? result "L")))))

(deftest biggest-wins-tool-test
  (testing "returns formatted biggest wins"
    (let [result (tools/call-biggest-wins sample-matches 5)]
      (is (string? result))
      (is (str/includes? result "1-3")))))

(deftest mcp-tools-list-test
  (testing "tools list has required shape"
    (let [tl (tools/list-tools)]
      (is (seq tl))
      (is (every? #(contains? % :name) tl))
      (is (every? #(contains? % :description) tl))
      (is (every? #(contains? % :inputSchema) tl))))

  (testing "all required tools are listed"
    (let [names (set (map :name (tools/list-tools)))]
      (is (contains? names "find_matches"))
      (is (contains? names "team_stats"))
      (is (contains? names "find_players"))
      (is (contains? names "standings"))
      (is (contains? names "biggest_wins"))
      (is (contains? names "head_to_head")))))
