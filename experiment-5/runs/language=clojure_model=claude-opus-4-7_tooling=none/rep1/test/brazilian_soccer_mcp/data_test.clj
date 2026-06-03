(ns brazilian-soccer-mcp.data-test
  "Unit tests for the data-loading and normalization layer."
  (:require [brazilian-soccer-mcp.data :as data]
            [clojure.test :refer [deftest is testing]]))

(deftest normalize-team-test
  (testing "Scenario: state suffixes are preserved so different Atléticos stay distinct"
    (is (= "atletico-mg" (data/normalize-team "Atlético-MG")))
    (is (= "atletico-mg" (data/normalize-team "Atletico-MG")))
    (is (= "atletico-pr" (data/normalize-team "Atletico-PR")))
    (is (not= (data/normalize-team "Atletico-MG") (data/normalize-team "Atletico-PR"))))

  (testing "Scenario: parenthetical country codes are removed"
    (is (= "nacional" (data/normalize-team "Nacional (URU)")))
    ;; "-EQU" is a 3-letter suffix so it isn't treated as a state code;
    ;; the key still distinguishes Barcelona of Ecuador from FC Barcelona.
    (is (= "barcelona equ" (data/normalize-team "Barcelona-EQU"))))

  (testing "Scenario: known aliases collapse to a single canonical key"
    (is (= (data/normalize-team "Flamengo-RJ") (data/normalize-team "Flamengo")))
    (is (= (data/normalize-team "Vasco-RJ")     (data/normalize-team "Vasco da Gama-RJ")))
    (is (= (data/normalize-team "Athletico-PR") (data/normalize-team "Atletico-PR"))))

  (testing "Scenario: nil and blank inputs return nil"
    (is (nil? (data/normalize-team nil)))
    (is (nil? (data/normalize-team "")))
    (is (nil? (data/normalize-team "   ")))))

(deftest team-key-matches-test
  (testing "Scenario: queries without a state match suffixed records"
    (is (data/team-key-matches? "palmeiras" "palmeiras-sp"))
    (is (data/team-key-matches? "palmeiras-sp" "palmeiras-sp")))
  (testing "Scenario: a query with a state never matches the wrong state"
    (is (not (data/team-key-matches? "atletico-mg" "atletico-pr"))))
  (testing "Scenario: unrelated keys never match"
    (is (not (data/team-key-matches? "flamengo" "fluminense")))))

(deftest parse-date-test
  (is (= "2019-06-08" (data/parse-date "2019-06-08")))
  (is (= "2019-06-08" (data/parse-date "2019-06-08 18:30:00")))
  (is (= "2003-03-29" (data/parse-date "29/03/2003")))
  (is (nil? (data/parse-date "")))
  (is (nil? (data/parse-date nil))))

(deftest load-dataset-test
  (testing "Scenario: loading the bundled CSV files yields the documented row counts"
    (let [ds      (data/load-dataset "data/kaggle")
          summary (data/dataset-summary ds)]
      (is (>= (:matches summary) 10000)
          "expect tens of thousands of match records after dedup")
      (is (= 18207 (:players summary))
          "FIFA dataset has 18,207 players")
      (is (some #{"Brasileirão Série A"} (:competitions summary)))
      (is (some #{"Copa Libertadores"}   (:competitions summary)))
      (is (some #{"Copa do Brasil"}      (:competitions summary)))
      (is (= 5 (count (:sources summary)))
          "all five match CSV sources are loaded"))))
