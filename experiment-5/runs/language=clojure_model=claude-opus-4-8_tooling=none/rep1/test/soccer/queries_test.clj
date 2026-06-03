(ns soccer.queries-test
  "=============================================================================
   BDD (Given-When-Then) scenarios for the query layer, mirroring the
   'Required Capabilities' and 'Testing Approach' sections of the spec. All
   scenarios run against soccer.fixtures/db.
   ============================================================================="
  (:require [clojure.test :refer [deftest testing is]]
            [soccer.fixtures :as fx]
            [soccer.queries :as q]))

(deftest match-queries
  (testing "Scenario: Find matches between two teams"
    ;; Given the match data is loaded
    ;; When I search for matches between Flamengo and Fluminense
    (let [ms (q/search-matches fx/db {:team "Flamengo" :team2 "Fluminense"})]
      ;; Then I receive a list of matches
      (is (= 2 (count ms)))
      ;; And each match has date, scores and competition
      (is (every? #(and (:date %) (:competition %)
                        (some? (:home-goal %)) (some? (:away-goal %))) ms))
      ;; And results are most-recent first
      (is (= "2019-09-03" (:date (first ms))))))

  (testing "Scenario: Find a team's matches in a season"
    ;; When I ask what matches Palmeiras played in 2019
    (let [ms (q/search-matches fx/db {:team "Palmeiras" :season 2019})]
      ;; Then only 2019 Palmeiras matches are returned
      (is (= 4 (count ms)))
      (is (every? #(= 2019 (:season %)) ms))))

  (testing "Scenario: Filter matches by competition"
    (let [ms (q/search-matches fx/db {:competition "Libertadores"})]
      (is (= 1 (count ms)))
      (is (= "Copa Libertadores" (:competition (first ms)))))))

(deftest team-statistics
  (testing "Scenario: Get team statistics for a season"
    ;; Given the match data is loaded
    ;; When I request statistics for Flamengo in 2019
    (let [t (q/team-stats fx/db {:team "Flamengo" :season 2019
                                 :competition "Brasileirão Série A"})]
      ;; Then I receive wins, losses, draws and goals
      (is (= 5 (:played t)))
      (is (= 4 (:wins t)))
      (is (= 1 (:draws t)))
      (is (= 0 (:losses t)))
      (is (= 12 (:gf t)))
      (is (= 3 (:ga t)))
      (is (= 13 (:points t)))))

  (testing "Scenario: Restrict a team's record to home matches"
    (let [t (q/team-stats fx/db {:team "Flamengo" :season 2019
                                 :competition "Brasileirão Série A" :venue :home})]
      ;; Flamengo home league games in 2019: vs Palmeiras(3-1), Santos(4-0), Fluminense(2-1)
      (is (= 3 (:played t)))
      (is (= 3 (:wins t))))))

(deftest head-to-head-query
  (testing "Scenario: Compare two teams head-to-head"
    ;; When I compare Flamengo and Fluminense head-to-head
    (let [h (q/head-to-head fx/db {:team1 "Flamengo" :team2 "Fluminense"})]
      ;; Then each side's record is reported
      (is (= 2 (:meetings h)))
      (is (= 1 (:team1-wins h)))   ; Flamengo won the Brasileirão meeting
      (is (= 1 (:team2-wins h)))   ; Fluminense won the cup meeting
      (is (= 0 (:draws h))))))

(deftest competition-standings
  (testing "Scenario: Compute league standings from match results"
    ;; When I request the 2019 Brasileirão standings
    (let [rows (q/standings fx/db {:competition "Brasileirão Série A" :season 2019})]
      ;; Then teams are ranked by points
      (is (= ["Flamengo" "Palmeiras" "Santos" "Fluminense"] (map :team rows)))
      (is (= [13 4 2 0] (map :points rows)))
      ;; And the leader's goal difference is correct
      (is (= 9 (:gd (first rows)))))))

(deftest statistical-analysis
  (testing "Scenario: Average goals per match for a competition"
    (let [s (q/league-stats fx/db {:competition "Brasileirão Série A" :season 2019})]
      ;; 7 league matches in 2019: rounds 1-6 + the Fla-Flu derby (round 7)
      (is (= 7 (:matches s)))
      ;; goals: 4+2+4+2+4+1+3 = 20
      (is (= 20 (:goals s)))
      (is (< (Math/abs (- (:avg-goals s) (/ 20.0 7))) 1e-9))))

  (testing "Scenario: Biggest victories by margin"
    (let [ms (q/biggest-wins fx/db {:limit 3})]
      ;; Then the 8-0 Libertadores result is first
      (is (= 8 (- (:home-goal (first ms)) (:away-goal (first ms))))))))

(deftest player-queries
  (testing "Scenario: Find Brazilian players sorted by rating"
    ;; When I search for Brazilian players
    (let [ps (q/search-players fx/db {:nationality "Brazil"})]
      ;; Then only Brazilians are returned, highest rated first
      (is (every? #(= "Brazil" (:nationality %)) ps))
      (is (= "Neymar Jr" (:name (first ps))))))

  (testing "Scenario: Find players at a specific club"
    (let [ps (q/search-players fx/db {:club "Flamengo"})]
      (is (= 3 (count ps)))
      (is (= ["Gabriel Barbosa" "Diego Alves" "Bruno Henrique"] (map :name ps)))))

  (testing "Scenario: Search a player by name"
    (let [ps (q/search-players fx/db {:name "Gabriel Barbosa"})]
      (is (= 1 (count ps)))
      (is (= "Flamengo" (:club (first ps))))))

  (testing "Scenario: Filter players by position and rating"
    (let [ps (q/search-players fx/db {:club "Flamengo" :position "GK"})]
      (is (= ["Diego Alves"] (map :name ps))))))
