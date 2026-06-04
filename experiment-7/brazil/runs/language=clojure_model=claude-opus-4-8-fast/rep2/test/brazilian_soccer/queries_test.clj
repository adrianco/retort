(ns brazilian-soccer.queries-test
  "=============================================================================
   queries_test.clj — Given/When/Then tests for the query/analytics layer
   -----------------------------------------------------------------------------
   Uses a small synthetic match set for precise assertions, plus light
   smoke tests against the real loaded CSV data to satisfy the spec's data
   coverage criteria.
   ============================================================================="
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.normalize :as norm]
            [brazilian-soccer.queries :as q]
            [brazilian-soccer.data :as data]))

;; ---------------------------------------------------------------------------
;; Synthetic fixture — mirrors the unified match record shape
;; ---------------------------------------------------------------------------

(defn- mk [date comp season home hg ag away & [extra]]
  (merge {:competition comp :season season :date date
          :home-team home :away-team away
          :home-goal hg :away-goal ag
          :home-key (norm/match-key home) :away-key (norm/match-key away)
          :winner (cond (> hg ag) :home (< hg ag) :away :else :draw)}
         extra))

(def sample
  [(mk "2019-05-01" "Brasileirão" 2019 "Flamengo" 2 1 "Fluminense" {:round 1})
   (mk "2019-08-01" "Brasileirão" 2019 "Fluminense" 0 0 "Flamengo" {:round 20})
   (mk "2019-09-01" "Brasileirão" 2019 "Flamengo" 5 0 "Santos"     {:round 25})
   (mk "2019-10-01" "Brasileirão" 2019 "Santos" 1 3 "Flamengo"     {:round 30})
   (mk "2018-07-01" "Copa do Brasil" 2018 "Palmeiras" 1 1 "Flamengo")])

;; ---------------------------------------------------------------------------
;; Match queries
;; ---------------------------------------------------------------------------

(deftest find-matches-between-two-teams
  (testing "Given match data is loaded"
    (testing "When I search for matches between Flamengo and Fluminense"
      (let [ms (q/search-matches sample {:team "Flamengo" :opponent "Fluminense"})]
        (testing "Then I receive the meetings, each with date and scores"
          (is (= 2 (count ms)))
          (is (every? :date ms))
          (is (every? (every-pred :home-goal :away-goal) ms))
          (testing "And they are sorted most-recent first"
            (is (= "2019-08-01" (:date (first ms))))))))))

(deftest filter-matches-by-competition-and-season
  (testing "Given match data, When filtered by competition+season"
    (let [ms (q/search-matches sample {:competition "Brasileirão" :season 2019})]
      (testing "Then only that competition/season is returned"
        (is (= 4 (count ms)))
        (is (every? #(= 2019 (:season %)) ms))))))

(deftest filter-matches-by-date-range
  (testing "Given match data, When filtered by a date range"
    (let [ms (q/search-matches sample {:date-from "2019-08-01" :date-to "2019-09-30"})]
      (testing "Then only matches in range are returned"
        (is (= 2 (count ms)))))))

;; ---------------------------------------------------------------------------
;; Team statistics
;; ---------------------------------------------------------------------------

(deftest team-statistics-for-a-season
  (testing "Given match data, When I request Flamengo's 2019 Brasileirão stats"
    (let [s (q/team-stats sample {:team "Flamengo" :season 2019 :competition "Brasileirão"})]
      (testing "Then wins, draws, losses and goals are computed"
        (is (= 4 (:played s)))
        (is (= 3 (:wins s)))     ; 2-1, 5-0, 3-1(away)
        (is (= 1 (:draws s)))    ; 0-0
        (is (= 0 (:losses s)))
        (is (= 10 (:goals-for s)))      ; 2+0+5+3
        (is (= 2  (:goals-against s)))  ; 1+0+0+1
        (is (= 10 (:points s)))))))

(deftest team-statistics-home-only
  (testing "Given match data, When venue is home-only"
    (let [s (q/team-stats sample {:team "Flamengo" :season 2019 :venue :home})]
      (testing "Then only home matches count"
        (is (= 2 (:played s)))      ; 2-1 vs Flu, 5-0 vs Santos
        (is (= 2 (:wins s)))))))

;; ---------------------------------------------------------------------------
;; Head to head
;; ---------------------------------------------------------------------------

(deftest head-to-head-record
  (testing "Given match data, When comparing Flamengo and Fluminense"
    (let [h (q/head-to-head sample {:team1 "Flamengo" :team2 "Fluminense"})]
      (testing "Then the tally reflects 1 win and 1 draw for Flamengo"
        (is (= 1 (:team1-wins h)))
        (is (= 0 (:team2-wins h)))
        (is (= 1 (:draws h)))
        (is (= 2 (:total h)))))))

;; ---------------------------------------------------------------------------
;; Standings
;; ---------------------------------------------------------------------------

(deftest standings-calculated-from-results
  (testing "Given match data, When I compute the 2019 Brasileirão table"
    (let [table (q/standings sample {:competition "Brasileirão" :season 2019})
          champ (first table)]
      (testing "Then Flamengo tops the table on points"
        (is (= "Flamengo" (:team champ)))
        (is (= 1 (:rank champ)))
        (is (= 10 (:points champ)))
        (is (= 4 (:played champ)))))))

;; ---------------------------------------------------------------------------
;; Statistical analysis
;; ---------------------------------------------------------------------------

(deftest competition-statistics
  (testing "Given match data, When I aggregate 2019 Brasileirão stats"
    (let [s (q/competition-stats sample {:competition "Brasileirão" :season 2019})]
      (testing "Then averages and home win rate are computed"
        (is (= 4 (:matches s)))
        (is (= 12 (:total-goals s)))         ; 3+0+5+4
        (is (= 3.0 (:avg-goals s)))
        (is (= 2 (:home-wins s)))            ; 2-1, 5-0
        (is (= 1 (:away-wins s)))            ; Santos 1-3 Fla
        (is (= 1 (:draws s)))))))

(deftest biggest-wins-ordering
  (testing "Given match data, When I ask for the biggest wins"
    (let [ms (q/biggest-wins sample {:limit 3})]
      (testing "Then the largest margin comes first"
        (is (= 5 (- (:home-goal (first ms)) (:away-goal (first ms)))))))))

;; ---------------------------------------------------------------------------
;; Player queries (real FIFA data)
;; ---------------------------------------------------------------------------

(def players-fixture
  [{:name "Neymar Jr" :overall 92 :position "LW" :club "Paris Saint-Germain" :nationality "Brazil"}
   {:name "Alisson"   :overall 89 :position "GK" :club "Liverpool" :nationality "Brazil"}
   {:name "L. Messi"  :overall 94 :position "RF" :club "FC Barcelona" :nationality "Argentina"}
   {:name "Gabriel Barbosa" :overall 78 :position "ST" :club "Flamengo" :nationality "Brazil"}])

(deftest search-players-by-nationality
  (testing "Given player data, When I filter by Brazilian nationality"
    (let [ps (q/search-players players-fixture {:nationality "Brazil"})]
      (testing "Then only Brazilians are returned, sorted by rating"
        (is (= 3 (count ps)))
        (is (= "Neymar Jr" (:name (first ps))))
        (is (every? #(= "Brazil" (:nationality %)) ps))))))

(deftest search-players-by-club
  (testing "Given player data, When I filter by club Flamengo"
    (let [ps (q/search-players players-fixture {:club "Flamengo"})]
      (testing "Then only Flamengo players are returned"
        (is (= 1 (count ps)))
        (is (= "Gabriel Barbosa" (:name (first ps))))))))

;; ---------------------------------------------------------------------------
;; Integration smoke tests against the real loaded CSVs
;; ---------------------------------------------------------------------------

(deftest real-data-loads
  (testing "Given the real CSV datasets, When loaded"
    (let [db (data/load-db!)]
      (testing "Then matches and players are populated"
        (is (> (count (:matches db)) 10000))
        (is (> (count (:players db)) 18000))))))

(deftest real-data-flamengo-matches
  (testing "Given real data, When I search Flamengo matches, Then many exist"
    (let [ms (q/search-matches {:team "Flamengo" :limit 5})]
      (is (= 5 (count ms)))
      (is (every? #(or (norm/matches? "Flamengo" (:home-team %))
                       (norm/matches? "Flamengo" (:away-team %))) ms)))))

(deftest real-data-known-player
  (testing "Given real FIFA data, When I search for Neymar, Then he is found"
    (let [ps (q/search-players {:name "Neymar"})]
      (is (seq ps))
      (is (some #(= "Brazil" (:nationality %)) ps)))))
