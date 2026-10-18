(ns brazilian-soccer-mcp.data-test
  (:require [clojure.test :refer [deftest is testing]]
            [brazilian-soccer-mcp.data :as data]))

(def ^:private db
  (delay (data/load-dataset "data/kaggle")))

(deftest loads-all-match-sources
  (let [competitions (set (map :competition (:matches @db)))]
    (is (= #{:brasileirao :copa-do-brasil :libertadores :serie-b :serie-c} competitions))))

(deftest matches-are-sorted-by-date
  (let [dates (map :date (:matches @db))]
    (is (= (sort dates) dates))))

(deftest overlapping-sources-are-deduplicated
  (testing "Palmeiras v Portuguesa 2012 appears in several files but is kept once"
    (let [hits (filter #(and (= :brasileirao (:competition %))
                             (= 2012 (:season %))
                             (= "Palmeiras" (:home %))
                             (= "Portuguesa" (:away %)))
                       (:matches @db))]
      (is (= 1 (count hits)))
      (is (= 1 (:home-goals (first hits))))
      (is (= 1 (:away-goals (first hits)))))))

(deftest brasileirao-season-has-one-match-per-fixture
  (let [season (filter #(and (= :brasileirao (:competition %)) (= 2019 (:season %))) (:matches @db))]
    (is (= 380 (count season)))))

(deftest rows-without-scores-are-skipped
  (is (every? #(and (number? (:home-goals %)) (number? (:away-goals %))) (:matches @db))))

(deftest loads-fifa-players
  (let [messi (first (filter #(= "L. Messi" (:name %)) (:players @db)))]
    (is (= 94 (:overall messi)))
    (is (= "FC Barcelona" (:club messi)))
    (is (= "Argentina" (:nationality messi)))
    (is (= 18207 (count (:players @db))))))
