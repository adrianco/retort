(ns soccer-mcp.data-test
  "BDD-style (Given/When/Then) tests for the data normalization layer."
  (:require [clojure.test :refer [deftest is testing]]
            [soccer-mcp.data :as data]))

(deftest team-name-normalization
  (testing "Feature: Team name normalization"
    (testing "Scenario: state suffix is preserved on the display name"
      ;; Given a team name with a state suffix
      ;; When normalized for display
      ;; Then the suffix is kept (so we can tell Atletico-MG from Atletico-PR)
      (is (= "Palmeiras-SP" (data/normalize-team "Palmeiras-SP")))
      (is (= "Flamengo-RJ"  (data/normalize-team "Flamengo-RJ")))
      (is (= ["Palmeiras" "SP"] (data/split-state-suffix "Palmeiras-SP"))))

    (testing "Scenario: team-key strips the suffix for matching"
      ;; team-key drops the state suffix and folds accents/case so that
      ;; queries like "Palmeiras" still match a stored "Palmeiras-SP".
      (is (= "palmeiras" (data/team-key "Palmeiras-SP")))
      (is (= "sao paulo" (data/team-key "São Paulo-SP"))))

    (testing "Scenario: names without a state suffix pass through"
      (is (= "Santos"  (data/normalize-team "Santos")))
      (is (= ["Santos" nil] (data/split-state-suffix "Santos"))))

    (testing "Scenario: matching is case- and accent-insensitive"
      ;; Given two names that differ only by case or accent
      ;; When matched
      ;; Then they are considered equivalent
      (is (data/team-matches? "São Paulo" "sao paulo"))
      (is (data/team-matches? "Grêmio"    "gremio"))
      (is (data/team-matches? "Flamengo-RJ" "Flamengo"))
      (is (not (data/team-matches? "Palmeiras" "Flamengo"))))))

(deftest date-normalization
  (testing "Feature: Date normalization"
    (testing "Scenario: ISO datetime is reduced to YYYY-MM-DD"
      (is (= "2012-05-19" (data/normalize-date "2012-05-19 18:30:00"))))

    (testing "Scenario: Brazilian DD/MM/YYYY is converted to ISO"
      (is (= "2003-03-29" (data/normalize-date "29/03/2003")))
      (is (= "2019-12-08" (data/normalize-date "8/12/2019"))))

    (testing "Scenario: unknown formats return nil"
      (is (nil? (data/normalize-date "not a date")))
      (is (nil? (data/normalize-date ""))))))

(deftest parse-long-safe-cases
  (testing "Feature: tolerant integer parsing"
    (is (= 1   (data/parse-long-safe "1")))
    (is (= 1   (data/parse-long-safe "1.0")))
    (is (= 2   (data/parse-long-safe "  2 ")))
    (is (nil? (data/parse-long-safe "")))
    (is (nil? (data/parse-long-safe nil)))
    (is (nil? (data/parse-long-safe "abc")))))

;; ----------------------------------------------------------------------------
;; Integration: actually load the bundled CSVs.

(def ^:private dataset (delay (data/load-all "data/kaggle")))

(deftest dataset-loads
  (testing "Feature: dataset loading"
    (let [{:keys [matches players]} @dataset]
      (testing "Scenario: all match CSV files contribute records"
        ;; Given the six CSVs in data/kaggle
        ;; When the dataset is loaded
        ;; Then we have matches from every source we ship
        (is (pos? (count matches)))
        (let [sources (into #{} (map :source-file) matches)]
          (is (contains? sources "Brasileirao_Matches.csv"))
          (is (contains? sources "Brazilian_Cup_Matches.csv"))
          (is (contains? sources "Libertadores_Matches.csv"))
          (is (contains? sources "BR-Football-Dataset.csv"))
          (is (contains? sources "novo_campeonato_brasileiro.csv"))))

      (testing "Scenario: players load with names and overall ratings"
        (is (pos? (count players)))
        (is (every? :name players))
        (is (pos? (count (filter :overall players))))))))
