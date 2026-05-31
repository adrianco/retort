(ns brazilian-soccer.normalize-test
  "=============================================================================
   BDD tests (Given-When-Then) for text & value normalization.
   =============================================================================
   Verifies the data-cleaning rules the whole server depends on: team-name
   canonicalization across suffix/accent variations, multi-format date parsing,
   and lenient numeric parsing."
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.string]
            [brazilian-soccer.normalize :as norm]))

(deftest team-name-normalization
  (testing "Scenario: spelling variants of one club fold to a single key"
    ;; Given different spellings/punctuation of the same club name
    ;; When we compute their canonical keys
    ;; Then accents fold, case lowers, and punctuation becomes single spaces
    (is (= "palmeiras sp" (norm/canonical-key "Palmeiras-SP")))
    (is (= "palmeiras sp" (norm/canonical-key "palmeiras  -  sp")))
    (is (= "america mg"   (norm/canonical-key "América - MG")))
    (is (= "nacional uru" (norm/canonical-key "Nacional (URU)")))
    (is (= "barcelona equ" (norm/canonical-key "Barcelona-EQU")))
    (is (= "gremio" (norm/canonical-key "Grêmio")))
    (is (= (norm/canonical-key "São Paulo-SP") (norm/canonical-key "Sao Paulo - SP"))))

  (testing "Scenario: clubs sharing a base name but different states stay distinct"
    ;; The whole reason the key retains the suffix: these are different clubs.
    (is (not= (norm/canonical-key "Atlético-MG") (norm/canonical-key "Atlético-PR")))
    (is (not= (norm/canonical-key "América-MG") (norm/canonical-key "América-RN")))
    (is (not= (norm/canonical-key "Botafogo-RJ") (norm/canonical-key "Botafogo-PB"))))

  (testing "Scenario: a suffix-less query is a substring of the suffixed key"
    ;; This is how the query layer reconciles \"Palmeiras\" with \"Palmeiras-SP\".
    (is (clojure.string/includes? (norm/canonical-key "Palmeiras-SP")
                                  (norm/canonical-key "Palmeiras")))))

(deftest clean-name-keeps-display-form
  (testing "Scenario: cleaning preserves accents/case for display"
    (is (= "América" (norm/clean-team-name "América - MG")))
    (is (= "Palmeiras" (norm/clean-team-name "Palmeiras-SP")))
    (is (= "Nacional" (norm/clean-team-name "Nacional (URU)")))))

(deftest date-parsing
  (testing "Scenario: multiple date formats normalize to ISO YYYY-MM-DD"
    ;; Given ISO, ISO+time and Brazilian-format dates
    ;; When parsed
    ;; Then all become a plain ISO date string
    (is (= "2023-09-24" (norm/parse-date "2023-09-24")))
    (is (= "2012-05-19" (norm/parse-date "2012-05-19 18:30:00")))
    (is (= "2003-03-29" (norm/parse-date "29/03/2003")))
    (is (nil? (norm/parse-date "")))
    (is (nil? (norm/parse-date nil))))
  (testing "Scenario: year extraction"
    (is (= 2003 (norm/year-of "29/03/2003")))
    (is (= 2012 (norm/year-of "2012-05-19 18:30:00")))))

(deftest int-parsing
  (testing "Scenario: lenient integer parsing across int/float/string/blank"
    (is (= 1 (norm/parse-int "1")))
    (is (= 1 (norm/parse-int "1.0")))
    (is (= 2 (norm/parse-int 2)))
    (is (= 3 (norm/parse-int " 3 ")))
    (is (nil? (norm/parse-int "")))
    (is (nil? (norm/parse-int nil)))))
