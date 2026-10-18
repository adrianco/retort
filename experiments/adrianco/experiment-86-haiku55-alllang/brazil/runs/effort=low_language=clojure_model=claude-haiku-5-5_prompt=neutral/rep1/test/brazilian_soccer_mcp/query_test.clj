(ns brazilian-soccer-mcp.query-test
  (:require [clojure.test :refer [deftest is testing]]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.normalize :as n]
            [brazilian-soccer-mcp.query :as q])
  (:import (java.time LocalDate)))

(defn- game
  "A normalized match record built by hand so query results are fully known."
  [competition date home home-goals away away-goals]
  (let [d (LocalDate/parse date)]
    {:competition competition
     :date d
     :season (.getYear d)
     :round nil
     :home (n/display-name home)
     :away (n/display-name away)
     :home-key (n/team-key home)
     :away-key (n/team-key away)
     :home-goals home-goals
     :away-goals away-goals}))

(def sample-db
  {:matches (sort-by :date
                     [(game :brasileirao "2019-05-01" "Flamengo-RJ" 2 "Fluminense-RJ" 1)
                      (game :brasileirao "2019-08-10" "Fluminense-RJ" 0 "Flamengo-RJ" 0)
                      (game :brasileirao "2019-09-14" "Flamengo-RJ" 3 "Palmeiras-SP" 0)
                      (game :brasileirao "2019-10-02" "Palmeiras-SP" 1 "Corinthians-SP" 1)
                      (game :brasileirao "2019-11-05" "Corinthians-SP" 2 "Flamengo-RJ" 1)
                      (game :copa-do-brasil "2019-06-12" "Flamengo" 4 "Palmeiras" 1)
                      (game :brasileirao "2018-05-01" "Palmeiras-SP" 2 "Flamengo-RJ" 0)])
   :players []})

(deftest parse-competition-understands-common-names
  (is (= :brasileirao (q/parse-competition "Brasileirão")))
  (is (= :brasileirao (q/parse-competition "serie a")))
  (is (= :copa-do-brasil (q/parse-competition "Copa do Brasil")))
  (is (= :libertadores (q/parse-competition "libertadores")))
  (is (= :serie-b (q/parse-competition "Série B")))
  (is (nil? (q/parse-competition "Premier League"))))

(deftest search-matches-finds-head-to-head-most-recent-first
  (let [{:keys [total matches]} (q/search-matches sample-db {:team "Flamengo" :opponent "Fluminense"})]
    (is (= 2 total))
    (is (= ["2019-08-10" "2019-05-01"] (map (comp str :date) matches)))))

(deftest search-matches-respects-venue
  (is (= 3 (:total (q/search-matches sample-db {:team "Flamengo" :venue :home}))))
  (is (= 3 (:total (q/search-matches sample-db {:team "Flamengo" :venue :away})))))

(deftest search-matches-filters-by-competition-season-and-dates
  (is (= 1 (:total (q/search-matches sample-db {:competition :copa-do-brasil}))))
  (is (= 6 (:total (q/search-matches sample-db {:season 2019}))))
  (is (= 2 (:total (q/search-matches sample-db {:from (LocalDate/parse "2019-09-01")
                                                 :to (LocalDate/parse "2019-10-31")})))))

(deftest search-matches-caps-results
  (let [{:keys [total matches]} (q/search-matches sample-db {:team "Flamengo" :limit 2})]
    (is (= 6 total))
    (is (= 2 (count matches)))))

(deftest team-record-counts-results-from-the-team-perspective
  (let [r (q/team-record sample-db "Flamengo" {:season 2019 :competition :brasileirao})]
    (is (= 4 (:matches r)))
    (is (= 2 (:wins r)))
    (is (= 1 (:draws r)))
    (is (= 1 (:losses r)))
    (is (= 6 (:goals-for r)))
    (is (= 3 (:goals-against r)))
    (is (= 50.0 (:win-rate r)))))

(deftest team-record-supports-home-only
  (let [r (q/team-record sample-db "Flamengo" {:season 2019 :venue :home})]
    (is (= 3 (:matches r)))
    (is (= 3 (:wins r)))
    (is (= 100.0 (:win-rate r)))))

(deftest team-record-with-no-matches-has-no-win-rate
  (let [r (q/team-record sample-db "Santos" {})]
    (is (= 0 (:matches r)))
    (is (nil? (:win-rate r)))))

(deftest head-to-head-totals-both-directions
  (let [h (q/head-to-head sample-db "Flamengo" "Palmeiras" {})]
    (is (= 3 (:total h)))
    (is (= 2 (:a-wins h)))
    (is (= 1 (:b-wins h)))
    (is (= 0 (:draws h)))
    (is (= "2019-09-14" (str (:date (:match (first (:matches h)))))))))

(deftest standings-award-three-points-for-a-win
  (let [table (q/standings sample-db :brasileirao 2019)
        by-team (into {} (map (juxt :team identity)) table)]
    (is (= "Flamengo" (:team (first table))))
    (is (= 1 (:position (first table))))
    (is (= 7 (:points (by-team "Flamengo"))))
    (is (= 1 (:points (by-team "Fluminense"))))
    (is (= 1 (:points (by-team "Palmeiras"))))
    (is (= 4 (count table)))))

(deftest match-stats-summarises-goals-and-win-rates
  (let [s (q/match-stats sample-db {:competition :brasileirao :season 2019})]
    (is (= 5 (:matches s)))
    (is (= 11 (:goals s)))
    (is (= 2.2 (:goals-per-match s)))
    (is (= 60.0 (:home-win-rate s)))
    (is (= 40.0 (:draw-rate s)))
    (is (= 0.0 (:away-win-rate s)))
    (is (= 3 (abs (- (:home-goals (first (:biggest-wins s))) (:away-goals (first (:biggest-wins s)))))))))

(def ^:private player-db
  {:matches []
   :players [{:name "Gabriel Barbosa" :nationality "Brazil" :club "Flamengo" :position "ST" :overall 84}
             {:name "Diego Ribas" :nationality "Brazil" :club "Flamengo" :position "CAM" :overall 80}
             {:name "Cuellar" :nationality "Colombia" :club "Flamengo" :position "CM" :overall 79}
             {:name "Dani Alves" :nationality "Brazil" :club "São Paulo FC" :position "RB" :overall 75}
             {:name "Pedro" :nationality "Brazil" :club "Flamengo" :position "ST" :overall 82}]})

(deftest search-players-filters-by-club-nationality-and-position
  (let [r (q/search-players player-db {:club "flamengo" :nationality "brazil" :position "forward"})]
    (is (= 2 (:total r)))
    (is (= ["Gabriel Barbosa" "Pedro"] (map :name (:players r)))))
  (is (= ["Dani Alves"] (map :name (:players (q/search-players player-db {:club "Sao Paulo"})))))
  (is (= 2 (:total (q/search-players player-db {:min-overall 82})))))

(deftest search-players-matches-by-partial-name
  (is (= ["Gabriel Barbosa"] (map :name (:players (q/search-players player-db {:name "barbosa"}))))))

(deftest real-dataset-answers-sample-questions
  (let [db (data/load-dataset "data/kaggle")]
    (testing "Flamengo vs Fluminense matches exist in the dataset"
      (is (pos? (:total (q/search-matches db {:team "Flamengo" :opponent "Fluminense"})))))
    (testing "2019 Brasileirão champion is Flamengo on 90 points"
      (let [champion (first (q/standings db :brasileirao 2019))]
        (is (= "Flamengo" (:team champion)))
        (is (= 90 (:points champion)))))
    (testing "Corinthians home record in 2022 is computed from data"
      (let [r (q/team-record db "Corinthians" {:season 2022 :venue :home})]
        (is (pos? (:matches r)))
        (is (= (:matches r) (+ (:wins r) (:draws r) (:losses r))))))))
