;; =============================================================================
;; soccer.data-test — Integration tests against the real Kaggle datasets
;; -----------------------------------------------------------------------------
;; Project: brazilian-soccer-mcp
;;
;; These load the actual CSV files from data/kaggle/ and assert plausibility:
;; every file is loadable & queryable, cross-file queries work, and a handful of
;; the specification's sample questions return sensible answers.  Skipped
;; gracefully if the data directory is absent.
;; =============================================================================
(ns soccer.data-test
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.java.io :as io]
            [soccer.data :as data]
            [soccer.query :as q]))

(def data-present? (.exists (io/file data/default-data-dir "fifa_data.csv")))

(defonce real-db (when data-present? (data/load-db)))

(defmacro when-data [& body]
  `(if data-present? (do ~@body)
       (println "  (skipping data integration tests: data/kaggle not found)")))

(deftest all-files-loaded
  (when-data
    (testing "Given the datasets, When loaded, Then matches and players are present"
      (is (> (count (:matches real-db)) 10000) "many matches loaded")
      (is (> (count (:players real-db)) 18000) "fifa players loaded"))))

(deftest all-competitions-present
  (when-data
    (testing "Given the data, When listing competitions, Then the three majors exist"
      (let [comps (set (q/competitions real-db))]
        (is (contains? comps "Brasileirão Série A"))
        (is (contains? comps "Copa do Brasil"))
        (is (contains? comps "Copa Libertadores"))))))

(deftest sample-match-query
  (when-data
    (testing "Given the data, When searching Flamengo vs Fluminense, Then meetings return"
      (let [res (q/search-matches real-db {:team "Flamengo" :opponent "Fluminense"})]
        (is (pos? (count res)))
        (is (every? #(and (:home %) (:away %)) res))))))

(deftest sample-team-record
  (when-data
    (testing "Given the data, When asking Palmeiras' 2019 record, Then it is non-trivial"
      (let [s (q/team-stats real-db "Palmeiras" {:season 2019})]
        (is (pos? (:matches s)))
        (is (= (:matches s) (+ (:wins s) (:draws s) (:losses s))))))))

(deftest sample-standings-2019
  (when-data
    (testing "Given 2019 Brasileirão, When computing standings, Then Flamengo are champions"
      (let [table (q/standings real-db "Brasileirão Série A" 2019)]
        (is (= 20 (count table)) "20-team league")
        (is (= "Flamengo" (:team (first table)))
            "Flamengo won the 2019 Brasileirão")))))

(deftest sample-brazilian-players
  (when-data
    (testing "Given the FIFA data, When filtering Brazilians, Then Neymar is top-rated"
      (let [res (q/search-players real-db {:nationality "Brazil" :limit 5})]
        (is (pos? (count res)))
        (is (= "Brazil" (:nationality (first res))))
        (is (>= (:overall (first res)) 88))))))

(deftest sample-player-by-name
  (when-data
    (testing "Given the FIFA data, When searching 'Neymar', Then a player returns"
      (let [res (q/search-players real-db {:name "Neymar"})]
        (is (pos? (count res)))
        (is (= "Brazil" (:nationality (first res))))))))

(deftest cross-file-query
  (when-data
    (testing "Given player + match data, When querying both for Santos, Then both answer
              (note: this FIFA edition lacks Flamengo/Palmeiras club licences,
               but Santos players are present)"
      (let [players (q/search-players real-db {:club "Santos"})
            matches (q/search-matches real-db {:team "Santos" :limit 5})]
        (is (pos? (count players)))
        (is (pos? (count matches)))))))

(deftest performance-budget
  (when-data
    (testing "Given the data, When running an aggregate query, Then it finishes well under 5s"
      (let [start (System/currentTimeMillis)
            _ (q/standings real-db "Brasileirão Série A" 2019)
            elapsed (- (System/currentTimeMillis) start)]
        (is (< elapsed 5000) (str "standings took " elapsed "ms"))))))
