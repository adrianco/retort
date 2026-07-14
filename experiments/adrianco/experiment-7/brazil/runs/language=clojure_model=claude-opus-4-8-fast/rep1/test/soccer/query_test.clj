;; =============================================================================
;; soccer.query-test — BDD (Given/When/Then) tests for the query layer
;; -----------------------------------------------------------------------------
;; Project: brazilian-soccer-mcp
;;
;; Uses a small hand-built fixture database so the analytics are verified with
;; known-correct expected values, independent of the real CSV contents.
;; =============================================================================
(ns soccer.query-test
  (:require [clojure.test :refer [deftest testing is]]
            [soccer.query :as q]
            [soccer.normalize :as n])
  (:import [java.time LocalDate]))

(defn- m [comp season home away hg ag & [date]]
  {:competition comp :season season
   :home (n/canonical-name home) :away (n/canonical-name away)
   :home-goals hg :away-goals ag
   :date (or date (LocalDate/of season 1 1))})

;; A tiny 3-team round robin (Flamengo, Palmeiras, Santos) plus a cup tie.
(def fixture
  {:matches
   [(m "Brasileirão Série A" 2023 "Flamengo-RJ" "Palmeiras-SP" 2 1 (LocalDate/of 2023 5 1))
    (m "Brasileirão Série A" 2023 "Palmeiras-SP" "Flamengo-RJ" 0 0 (LocalDate/of 2023 8 1))
    (m "Brasileirão Série A" 2023 "Flamengo-RJ" "Santos" 3 0 (LocalDate/of 2023 6 1))
    (m "Brasileirão Série A" 2023 "Santos" "Flamengo-RJ" 1 2 (LocalDate/of 2023 9 1))
    (m "Brasileirão Série A" 2023 "Palmeiras-SP" "Santos" 4 0 (LocalDate/of 2023 7 1))
    (m "Brasileirão Série A" 2023 "Santos" "Palmeiras-SP" 1 1 (LocalDate/of 2023 10 1))
    (m "Copa do Brasil" 2023 "Flamengo" "Santos" 5 0 (LocalDate/of 2023 4 1))]
   :players
   [{:name "Gabriel Barbosa" :nationality "Brazil" :overall 84 :potential 86
     :club "Flamengo" :position "ST" :age 26}
    {:name "Neymar Jr" :nationality "Brazil" :overall 92 :potential 92
     :club "Paris Saint-Germain" :position "LW" :age 31}
    {:name "Endrick" :nationality "Brazil" :overall 70 :potential 90
     :club "Palmeiras" :position "ST" :age 17}
    {:name "Lionel Messi" :nationality "Argentina" :overall 93 :potential 93
     :club "Paris Saint-Germain" :position "RW" :age 35}
    {:name "Pedro" :nationality "Brazil" :overall 80 :potential 84
     :club "Flamengo" :position "ST" :age 25}]})

;; --- 1. Match queries -------------------------------------------------------

(deftest search-matches-between-two-teams
  (testing "Given the data, When searching Flamengo vs Palmeiras,
            Then both league meetings are returned, newest first"
    (let [res (q/search-matches fixture {:team "Flamengo" :opponent "Palmeiras"})]
      (is (= 2 (count res)))
      (is (= (LocalDate/of 2023 8 1) (:date (first res))) "sorted newest first")
      (is (every? #(or (n/same-team? "Flamengo" (:home %))
                       (n/same-team? "Flamengo" (:away %))) res)))))

(deftest search-matches-by-competition-and-season
  (testing "Given a competition + season filter, When searching, Then only those return"
    (let [res (q/search-matches fixture {:competition "Copa do Brasil" :season 2023})]
      (is (= 1 (count res)))
      (is (= "Copa do Brasil" (:competition (first res)))))))

(deftest search-matches-by-date-range
  (testing "Given a date range, When searching, Then only in-range matches return"
    (let [res (q/search-matches fixture {:team "Flamengo"
                                         :date-from "2023-05-15"
                                         :date-to "2023-08-15"})]
      (is (= 2 (count res)))
      (is (every? #(and (not (.isBefore (:date %) (LocalDate/of 2023 5 15)))
                        (not (.isAfter (:date %) (LocalDate/of 2023 8 15)))) res)))))

(deftest search-matches-with-name-variation
  (testing "Given a suffixed name in data, When searching by plain name, Then it matches"
    (is (pos? (count (q/search-matches fixture {:team "Palmeiras"}))))))

;; --- 2. Team queries --------------------------------------------------------

(deftest team-record-scenario
  (testing "Given the season, When requesting Flamengo's record, Then W/D/L and goals are correct"
    (let [s (q/team-stats fixture "Flamengo" {:season 2023 :competition "Brasileirão Série A"})]
      ;; Flamengo league games: W vs Pal(2-1), D vs Pal(0-0), W vs San(3-0), W vs San(2-1)
      (is (= 4 (:matches s)))
      (is (= 3 (:wins s)))
      (is (= 1 (:draws s)))
      (is (= 0 (:losses s)))
      (is (= 7 (:goals-for s)))
      (is (= 2 (:goals-against s)))
      (is (= 10 (:points s)))
      (is (= 0.75 (:win-rate s))))))

(deftest team-record-home-only
  (testing "Given venue=home, When requesting record, Then only home games count"
    (let [s (q/team-stats fixture "Flamengo" {:season 2023
                                              :competition "Brasileirão Série A"
                                              :venue :home})]
      ;; home league games: vs Pal 2-1 (W), vs San 3-0 (W)
      (is (= 2 (:matches s)))
      (is (= 2 (:wins s))))))

;; --- 5. Head to head --------------------------------------------------------

(deftest head-to-head-scenario
  (testing "Given two teams, When computing H2H, Then aggregate is correct across competitions"
    (let [h (q/head-to-head fixture "Flamengo" "Santos")]
      ;; league: Fla 3-0, Fla 2-1 (away win); cup: Fla 5-0 => 3 Fla wins
      (is (= 3 (:matches h)))
      (is (= 3 (:a-wins h)))
      (is (= 0 (:b-wins h)))
      (is (= 0 (:draws h)))
      (is (= 10 (:a-goals h)))
      (is (= 1 (:b-goals h))))))

;; --- 4. Standings -----------------------------------------------------------

(deftest standings-scenario
  (testing "Given a season, When computing standings, Then table is points-ordered"
    (let [table (q/standings fixture "Brasileirão Série A" 2023)]
      (is (= 3 (count table)))
      (is (= "Flamengo" (:team (first table))) "Flamengo top on 10 pts")
      (is (= 1 (:position (first table))))
      (is (= 10 (:points (first table))))
      ;; Palmeiras: D vs Fla, L vs Fla, W vs San, D vs San => 1W 2D 1L = 5 pts
      (let [pal (first (filter #(= "Palmeiras" (:team %)) table))]
        (is (= 5 (:points pal)))))))

;; --- 5. Competition stats ---------------------------------------------------

(deftest competition-stats-scenario
  (testing "Given a competition+season, When aggregating, Then goals/match & rates are correct"
    (let [s (q/competition-stats fixture {:competition "Brasileirão Série A" :season 2023})]
      (is (= 6 (:matches s)))
      ;; total goals: (2+1)+(0+0)+(3+0)+(1+2)+(4+0)+(1+1) = 15
      (is (= 15 (:total-goals s)))
      (is (= 2.5 (:goals-per-match s)))
      ;; home wins: game1(2-1),game3(3-0),game5(4-0) = 3; away win: game4 (1-2) =1; draws: 2
      (is (= 3 (:home-wins s)))
      (is (= 1 (:away-wins s)))
      (is (= 2 (:draws s))))))

(deftest biggest-wins-scenario
  (testing "Given the data, When finding biggest wins, Then sorted by margin desc"
    (let [res (q/biggest-wins fixture {:limit 3})]
      (is (= 5 (:margin (first res))) "Flamengo 5-0 Santos is biggest")
      (is (>= (:margin (first res)) (:margin (second res)))))))

;; --- 3. Player queries ------------------------------------------------------

(deftest player-search-by-name
  (testing "Given a name, When searching players, Then the player is found"
    (let [res (q/search-players fixture {:name "Gabriel Barbosa"})]
      (is (= 1 (count res)))
      (is (= "Gabriel Barbosa" (:name (first res)))))))

(deftest player-search-brazilian-sorted
  (testing "Given nationality=Brazil, When searching, Then sorted by overall desc"
    (let [res (q/search-players fixture {:nationality "Brazil"})]
      (is (= 4 (count res)))
      (is (= "Neymar Jr" (:name (first res))))
      (is (apply >= (map :overall res))))))

(deftest player-search-by-club-and-position
  (testing "Given club + position filters, When searching, Then results match both"
    (let [res (q/search-players fixture {:club "Flamengo" :position "ST"})]
      (is (= 2 (count res)))
      (is (every? #(= "Flamengo" (:club %)) res))
      (is (every? #(= "ST" (:position %)) res)))))

(deftest players-by-club-summary-scenario
  (testing "Given Brazilians, When summarising by club, Then counts & averages are right"
    (let [res (q/players-by-club-summary fixture {:nationality "Brazil"})
          fla (first (filter #(= "Flamengo" (:club %)) res))]
      (is (= 2 (:players fla)))
      (is (= 82.0 (:avg-overall fla)) "(84+80)/2"))))
