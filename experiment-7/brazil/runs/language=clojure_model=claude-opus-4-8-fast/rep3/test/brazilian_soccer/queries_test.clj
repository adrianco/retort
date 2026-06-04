;; =============================================================================
;; brazilian-soccer.queries-test
;; -----------------------------------------------------------------------------
;; BDD (Gherkin-style Given/When/Then) coverage of the five capability groups
;; required by TASK.md: match, team, player, competition and statistical queries.
;; =============================================================================
(ns brazilian-soccer.queries-test
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.queries :as q]
            [brazilian-soccer.test-helper :as h]))

;; ---- 1. Match queries -----------------------------------------------------

(deftest find-matches-between-two-teams
  (testing "Given match data, When searching Flamengo vs Fluminense, Then we get dated, scored matches"
    (let [ms (q/find-matches (h/graph) {:team "Flamengo" :opponent "Fluminense"})]
      (is (seq ms))
      (is (every? :date ms))
      (is (every? #(or (= "Flamengo" (:home %)) (= "Flamengo" (:away %))) ms))
      (is (every? #(or (= "Fluminense" (:home %)) (= "Fluminense" (:away %))) ms)))))

(deftest find-matches-by-season-and-team
  (testing "Given a season filter, When searching Palmeiras in 2019, Then only 2019 matches return"
    (let [ms (q/find-matches (h/graph) {:team "Palmeiras" :season 2019})]
      (is (seq ms))
      (is (every? #(= 2019 (:season %)) ms)))))

(deftest find-matches-by-competition
  (testing "Given a competition filter, When searching Libertadores, Then all results are that competition"
    (let [ms (q/find-matches (h/graph) {:competition "Libertadores" :limit 100})]
      (is (seq ms))
      (is (every? #(= "Copa Libertadores" (:competition %)) ms)))))

(deftest find-matches-home-filter
  (testing "Given a home-only filter, When searching Corinthians at home, Then it is always the home side"
    (let [ms (q/find-matches (h/graph) {:team "Corinthians" :home true :season 2022})]
      (is (seq ms))
      (is (every? #(= "Corinthians" (:home %)) ms)))))

;; ---- 2. Team queries ------------------------------------------------------

(deftest team-stats-test
  (testing "Given match data, When computing Palmeiras 2019 stats, Then W/D/L and goals add up"
    (let [s (q/team-stats (h/graph) {:team "Palmeiras" :season 2019})]
      (is (some? s))
      (is (pos? (:matches s)))
      (is (= (:matches s) (+ (:wins s) (:draws s) (:losses s))))
      (is (>= (:goals-for s) 0)))))

(deftest head-to-head-test
  (testing "Given two rivals, When computing head-to-head, Then totals are internally consistent"
    (let [h (q/head-to-head (h/graph) "Flamengo" "Fluminense")]
      (is (pos? (:total h)))
      (is (= (:total h) (count (:matches h))))
      (is (= (:total h) (+ (:a-wins h) (:b-wins h) (:draws h)))))))

;; ---- 3. Player queries ----------------------------------------------------

(deftest brazilian-players-test
  (testing "Given player data, When filtering by nationality Brazil, Then only Brazilians return, rating-sorted"
    (let [ps (q/find-players (h/graph) {:nationality "Brazil" :limit 20})]
      (is (seq ps))
      (is (every? #(= "Brazil" (:nationality %)) ps))
      (is (apply >= (map :overall ps)) "sorted by overall descending"))))

(deftest player-by-name-test
  (testing "Given a name search, When looking up a known player, Then a match returns"
    (let [ps (q/find-players (h/graph) {:name "Neymar"})]
      (is (seq ps))
      (is (some #(re-find #"(?i)neymar" (:name %)) ps)))))

(deftest players-by-position-test
  (testing "Given a position filter, When searching GK, Then every result is a GK"
    (let [ps (q/find-players (h/graph) {:position "GK" :nationality "Brazil" :limit 10})]
      (is (seq ps))
      (is (every? #(= "GK" (:position %)) ps)))))

;; ---- 4. Competition queries ----------------------------------------------

(deftest standings-test
  (testing "Given a league season, When computing the 2019 Brasileirão table, Then Flamengo top a sane 20-team table"
    (let [rows (q/standings (h/graph) "Brasileirão Série A" 2019)]
      (is (seq rows))
      (is (= 20 (count rows)) "20-club league")
      (is (= 1 (:rank (first rows))))
      ;; points are non-increasing down the table
      (is (apply >= (map :points rows)))
      ;; 2019 champions were Flamengo
      (is (= "Flamengo" (:team (first rows)))))))

(deftest list-competitions-test
  (testing "Given the graph, When listing competitions, Then each has seasons and counts"
    (let [cs (q/list-competitions (h/graph))]
      (is (seq cs))
      (is (every? #(pos? (:matches %)) cs)))))

;; ---- 5. Statistical analysis ---------------------------------------------

(deftest league-stats-test
  (testing "Given Brasileirão matches, When aggregating, Then averages and rates are in plausible ranges"
    (let [s (q/league-stats (h/graph) {:competition "Brasileirão Série A"})]
      (is (pos? (:scored-matches s)))
      (is (< 1.5 (:avg-goals s) 4.0) "avg goals per match is plausible")
      (is (< 0.0 (:home-win-rate s) 1.0))
      (is (< 0.99 (+ (:home-win-rate s) (:away-win-rate s) (:draw-rate s)) 1.01)
          "rates sum to ~1"))))

(deftest biggest-wins-test
  (testing "Given match data, When finding biggest wins, Then they are sorted by margin descending"
    (let [ms (q/biggest-wins (h/graph) {:competition "Brasileirão Série A" :limit 5})]
      (is (= 5 (count ms)))
      (is (apply >= (map :margin ms)))
      (is (>= (:margin (first ms)) 4)))))
