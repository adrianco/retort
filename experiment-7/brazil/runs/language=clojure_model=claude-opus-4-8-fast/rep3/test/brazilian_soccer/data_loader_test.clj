;; =============================================================================
;; brazilian-soccer.data-loader-test
;; -----------------------------------------------------------------------------
;; BDD coverage that every provided CSV is loadable and normalised into the
;; uniform match/player record shape.
;; =============================================================================
(ns brazilian-soccer.data-loader-test
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.data-loader :as loader]
            [brazilian-soccer.test-helper :as h]))

(def matches (delay (loader/load-matches h/data-dir)))
(def players (delay (loader/load-players-data h/data-dir)))

(deftest all-files-load-test
  (testing "Given the six CSV files, When loaded, Then all rows are parsed"
    (is (> (count @matches) 20000) "match rows from all five match files")
    (is (> (count @players) 18000) "player rows from fifa_data.csv")))

(deftest competitions-present-test
  (testing "Given the loaded matches, Then each canonical competition is represented"
    (let [comps (set (map :competition @matches))]
      (is (contains? comps "Brasileirão Série A"))
      (is (contains? comps "Copa do Brasil"))
      (is (contains? comps "Copa Libertadores")))))

(deftest match-record-shape-test
  (testing "Given a match record, Then it has normalised keys, dates and scores"
    (let [m (first (filter #(and (:date %) (:home-goals %)) @matches))]
      (is (string? (:competition m)))
      (is (re-matches #"\d{4}-\d{2}-\d{2}" (:date m)))
      (is (integer? (:season m)))
      (is (string? (:home-key m)))
      (is (integer? (:home-goals m))))))

(deftest extended-stats-test
  (testing "Given BR-Football rows, Then extended stats (shots/corners) are captured"
    (let [with-stats (filter #(and (= :br-football (:source %))
                                   (seq (:stats %))) @matches)]
      (is (seq with-stats))
      (is (some :home-shots (map :stats with-stats))))))

(deftest player-record-shape-test
  (testing "Given a player record, Then ratings and matching keys are present"
    (let [p (first (filter #(= "Brazil" (:nationality %)) @players))]
      (is (string? (:name p)))
      (is (integer? (:overall p)))
      (is (= "brazil" (:nationality-key p))))))
