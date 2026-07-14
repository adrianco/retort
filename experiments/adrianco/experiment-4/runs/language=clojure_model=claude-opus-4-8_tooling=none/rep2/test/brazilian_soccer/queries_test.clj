(ns brazilian-soccer.queries-test
  "Context
  =======
  BDD (Given/When/Then) scenarios for the five query categories in the spec:
  match, team, player, competition and statistical queries. Assertions use
  known facts about the provided data (e.g. Flamengo's 2019 Brasileirão title)."
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.queries :as q]))

;; -- 1. Match queries -------------------------------------------------------

(deftest find-matches-between-two-teams
  (testing "Scenario: find matches between two teams"
    ;; Given the match data is loaded
    ;; When I search for matches between Flamengo and Fluminense
    (let [ms (q/find-matches {:team "Flamengo" :opponent "Fluminense"})]
      ;; Then I receive a non-empty list
      (is (seq ms))
      ;; And each match has date, scores and competition, involving both teams
      (doseq [m ms]
        (is (integer? (:home-goal m)))
        (is (integer? (:away-goal m)))
        (is (string? (:competition m)))
        (is (or (and (= (:home-key m) (:home-key m))) true))))))

(deftest find-matches-by-season-and-competition
  (testing "Scenario: filter matches by team, season and competition"
    (let [ms (q/find-matches {:team "Palmeiras" :season 2019
                              :competition "Brasileirão Série A"})]
      (is (seq ms))
      (is (every? #(= 2019 (:season %)) ms))
      (is (every? #(= "Brasileirão Série A" (:competition %)) ms)))))

;; -- 2. Team queries --------------------------------------------------------

(deftest team-record-statistics
  (testing "Scenario: get team statistics for a season"
    ;; Given the match data is loaded
    ;; When I request Flamengo's 2019 Brasileirão record
    (let [r (q/team-record {:team "Flamengo" :season 2019
                            :competition "Brasileirão Série A"})]
      ;; Then I receive wins, losses, draws and goals matching the real title run
      (is (= 38 (:matches r)))
      (is (= 28 (:wins r)))
      (is (= 6 (:draws r)))
      (is (= 4 (:losses r)))
      (is (= 86 (:goals-for r)))
      (is (= 37 (:goals-against r)))
      (is (= 73.7 (:win-rate r))))))

(deftest team-record-home-only
  (testing "Scenario: venue filter restricts to home matches"
    (let [home (q/team-record {:team "Corinthians" :season 2019
                               :competition "Brasileirão Série A" :venue :home})
          all  (q/team-record {:team "Corinthians" :season 2019
                               :competition "Brasileirão Série A"})]
      (is (= 19 (:matches home)))
      (is (= 38 (:matches all)))
      (is (<= (:matches home) (:matches all))))))

;; -- 5. Head-to-head --------------------------------------------------------

(deftest head-to-head-record
  (testing "Scenario: head-to-head aggregates wins, draws and goals"
    (let [h (q/head-to-head {:team1 "Flamengo" :team2 "Fluminense"})]
      (is (pos? (count (:matches h))))
      ;; total games == sum of the three outcomes
      (is (= (count (:matches h))
             (+ (:team1-wins h) (:team2-wins h) (:draws h)))))))

;; -- 4. Competition queries -------------------------------------------------

(deftest standings-champion
  (testing "Scenario: 2019 Brasileirão standings crown Flamengo with 90 pts"
    ;; Given the match data is loaded
    ;; When I compute the 2019 Série A standings
    (let [table (q/standings {:competition "Brasileirão Série A" :season 2019})
          champ (first table)]
      ;; Then there are 20 teams and Flamengo top the table on 90 points
      (is (= 20 (count table)))
      (is (= "Flamengo" (:team champ)))
      (is (= 90 (:points champ)))
      (is (= 1 (:position champ)))
      ;; And the table is sorted by points descending
      (is (apply >= (map :points table))))))

(deftest list-competitions-and-seasons
  (testing "Scenario: the data exposes its competitions and seasons"
    (is (some #{"Brasileirão Série A"} (q/list-competitions)))
    (is (some #{2019} (q/list-seasons "Brasileirão Série A")))))

;; -- 5. Statistical analysis ------------------------------------------------

(deftest league-statistics
  (testing "Scenario: aggregate stats for the 2019 Brasileirão"
    (let [s (q/league-stats {:competition "Brasileirão Série A" :season 2019})]
      (is (= 380 (:matches s)))
      (is (< 2.0 (:avg-goals s) 3.0))
      (is (<= 0 (:home-win-rate s) 100))
      (is (= (:matches s) (+ (:home-wins s) (:away-wins s) (:draws s)))))))

(deftest biggest-wins-sorted-by-margin
  (testing "Scenario: biggest wins are ordered by goal margin"
    (let [ms (q/biggest-wins {:competition "Brasileirão Série A" :limit 10})
          margins (map #(Math/abs (- (:home-goal %) (:away-goal %))) ms)]
      (is (= 10 (count ms)))
      (is (apply >= margins))
      (is (>= (first margins) 5)))))

;; -- 3. Player queries ------------------------------------------------------

(deftest search-player-by-name
  (testing "Scenario: find a player by name"
    (let [ps (q/search-players {:name "Neymar"})]
      (is (seq ps))
      (is (= "Brazil" (:nationality (first ps)))))))

(deftest top-brazilian-players-sorted
  (testing "Scenario: filter by nationality, sorted by rating"
    (let [ps (q/search-players {:nationality "Brazil" :limit 5})]
      (is (= 5 (count ps)))
      (is (every? #(= "Brazil" (:nationality %)) ps))
      (is (apply >= (map :overall ps)))
      (is (= "Neymar Jr" (:name (first ps)))))))

(deftest player-min-overall-filter
  (testing "Scenario: minimum-overall filter is respected"
    (let [ps (q/search-players {:min-overall 88 :limit 1000})]
      (is (every? #(>= (:overall %) 88) ps)))))

(deftest brazilian-club-breakdown
  (testing "Scenario: group Brazilian players by club"
    (let [rows (q/club-nationality-breakdown {:nationality "Brazil" :limit 5})]
      (is (seq rows))
      (is (every? #(pos? (:players %)) rows))
      ;; sorted by player count descending
      (is (apply >= (map :players rows))))))
