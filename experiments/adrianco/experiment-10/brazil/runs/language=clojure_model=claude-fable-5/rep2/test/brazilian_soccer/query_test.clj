(ns brazilian-soccer.query-test
  "BDD scenarios for match, team, player, competition and statistical
  queries, mirroring the Gherkin scenarios in the specification."
  (:require [clojure.test :refer [deftest is testing]]
            [brazilian-soccer.query :as query]))

;; ---------------------------------------------------------------------------
;; Feature: Match Queries

(deftest scenario-find-matches-between-two-teams
  (testing "Given the match data is loaded
            When I search for matches between Flamengo and Fluminense
            Then I should receive a list of matches
            And each match should have date, scores and competition"
    (let [matches (query/find-matches {:team "Flamengo" :opponent "Fluminense"})]
      (is (seq matches))
      (is (every? :date matches))
      (is (every? :competition matches))
      (is (every? #(#{"Flamengo" "Fluminense"} (:home %)) matches))
      (is (every? #(#{"Flamengo" "Fluminense"} (:away %)) matches)))))

(deftest scenario-find-matches-by-team-and-season
  (testing "Given the match data is loaded
            When I ask what matches Palmeiras played in 2023
            Then every match involves Palmeiras in the 2023 season"
    (let [matches (query/find-matches {:team "Palmeiras" :season 2023})]
      (is (seq matches))
      (is (every? #(= 2023 (:season %)) matches))
      (is (every? #(or (= "Palmeiras" (:home %)) (= "Palmeiras" (:away %)))
                  matches)))))

(deftest scenario-find-matches-by-date-range
  (testing "Given the match data is loaded
            When I search with a date range
            Then all matches fall inside the range"
    (let [matches (query/find-matches {:team "Santos"
                                       :date-from "2015-01-01"
                                       :date-to "2015-12-31"})]
      (is (seq matches))
      (is (every? #(and (<= (compare "2015-01-01" (:date %)) 0)
                        (<= (compare (:date %) "2015-12-31") 0))
                  matches)))))

(deftest scenario-find-cup-finals
  (testing "Given the match data is loaded
            When I search for Copa Libertadores finals in 2018
            Then I get exactly the two legs of the final
            And 'final' does not match semifinals"
    (let [matches (query/find-matches {:competition "libertadores"
                                       :season 2018 :stage "final"})]
      (is (= 2 (count matches)) "two-legged final")
      (is (every? #(= "final" (:stage %)) matches)))))

;; ---------------------------------------------------------------------------
;; Feature: Team Queries

(deftest scenario-get-team-statistics
  (testing "Given the match data is loaded
            When I request statistics for Palmeiras in season 2023
            Then I should receive wins, losses, draws and goals"
    (let [stats (query/team-stats "Palmeiras" {:season 2023})]
      (is (pos? (:matches stats)))
      (is (= (:matches stats)
             (+ (:wins stats) (:draws stats) (:losses stats))))
      (is (pos? (:goals-for stats))))))

(deftest scenario-home-record-uses-only-home-matches
  (testing "Given the match data is loaded
            When I request Corinthians' home record for the 2022 Brasileirão
            Then it covers exactly the 19 home fixtures of a 38-round season"
    (let [stats (query/team-stats "Corinthians"
                                  {:season 2022 :competition "brasileirao"
                                   :venue "home"})]
      (is (= 19 (:matches stats)))
      (is (= 19 (+ (:wins stats) (:draws stats) (:losses stats)))))))

(deftest scenario-head-to-head-comparison
  (testing "Given the match data is loaded
            When I compare Palmeiras and Santos head-to-head
            Then wins plus draws account for every decided match"
    (let [{:keys [matches team1-wins team2-wins draws]}
          (query/head-to-head "Palmeiras" "Santos" {})]
      (is (seq matches))
      (is (= (count (filter #(and (:home-goals %) (:away-goals %)) matches))
             (+ team1-wins team2-wins draws))))))

;; ---------------------------------------------------------------------------
;; Feature: Competition Queries

(deftest scenario-standings-identify-the-champion
  (testing "Given the 2019 Brasileirão match results
            When the league table is calculated
            Then Flamengo is champion with 90 points from 28W 6D 4L"
    (let [{:keys [rows]} (query/standings {:season 2019})
          champion (first rows)]
      (is (= 20 (count rows)))
      (is (= "Flamengo" (:team champion)))
      (is (= 90 (:points champion)))
      (is (= [28 6 4] [(:wins champion) (:draws champion) (:losses champion)]))
      (is (every? #(= 38 (:played %)) rows)))))

(deftest scenario-standings-for-other-seasons
  (testing "Given match results for several seasons
            When league tables are calculated
            Then the known champions come out on top"
    (is (= "Corinthians" (-> (query/standings {:season 2015}) :rows first :team)))
    (is (= "Palmeiras" (-> (query/standings {:season 2022}) :rows first :team)))))

(deftest scenario-relegation-zone
  (testing "Given a calculated league table
            When I look at the bottom four
            Then they are real participants, not data noise"
    (let [{:keys [rows]} (query/standings {:season 2016})]
      (is (= 20 (count rows)) "phantom teams from mislabeled rows are excluded")
      (is (= "Palmeiras" (:team (first rows)))))))

;; ---------------------------------------------------------------------------
;; Feature: Player Queries

(deftest scenario-search-players-by-nationality
  (testing "Given the FIFA player data is loaded
            When I search for Brazilian players
            Then I get all 827, sorted by overall rating"
    (let [players (query/search-players {:nationality "Brazil" :limit 10000})]
      (is (= 827 (count players)))
      (is (= "Neymar Jr" (:name (first players))))
      (is (apply >= (map :overall players)) "sorted by rating"))))

(deftest scenario-search-players-by-club-and-position
  (testing "Given the FIFA player data is loaded
            When I filter by club and by position
            Then only matching players are returned"
    (let [cruzeiro (query/search-players {:club "Cruzeiro" :limit 100})
          keepers  (query/search-players {:club "Grêmio" :position "GK" :limit 100})]
      (is (seq cruzeiro))
      (is (every? #(= "Cruzeiro" (:club %)) cruzeiro))
      (is (seq keepers))
      (is (every? #(= "GK" (:position %)) keepers)))))

(deftest scenario-lookup-a-single-player
  (testing "Given the FIFA player data is loaded
            When I look up a player by partial name
            Then the best match is returned with attributes"
    (let [p (query/get-player "Neymar")]
      (is (= "Neymar Jr" (:name p)))
      (is (= "Brazil" (:nationality p)))
      (is (= 92 (:overall p)))
      (is (seq (:skills p))))
    (is (nil? (query/get-player "No Such Player Xyz")))))

;; ---------------------------------------------------------------------------
;; Feature: Statistical Analysis

(deftest scenario-average-goals-per-match
  (testing "Given all Brasileirão matches
            When the average goals per match is calculated
            Then it falls in a plausible range"
    (let [{:keys [matches avg-goals home-wins draws away-wins]}
          (query/competition-stats {:competition "brasileirao"})]
      (is (> matches 8000))
      (is (< 2.0 avg-goals 3.0))
      (is (= matches (+ home-wins draws away-wins)))
      (is (> home-wins away-wins) "home advantage exists"))))

(deftest scenario-biggest-wins
  (testing "Given all matches with scores
            When ranked by goal margin
            Then margins are non-increasing and the largest is at least 6"
    (let [wins (query/biggest-wins {:limit 10})
          margin #(abs (- (:home-goals %) (:away-goals %)))]
      (is (= 10 (count wins)))
      (is (apply >= (map margin wins)))
      (is (>= (margin (first wins)) 6)))))
