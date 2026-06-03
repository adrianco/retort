(ns soccer.normalize-test
  "BDD (Given-When-Then) scenarios for team-name / date normalization, covering
   the 'Data Quality Notes' requirements: suffix variations, accents, and the
   several date formats."
  (:require [clojure.test :refer [deftest testing is]]
            [soccer.normalize :as n]))

(deftest team-name-normalization
  (testing "Scenario: strip state and country suffixes from team names"
    ;; Given names written with the conventions seen across the datasets
    ;; When normalized to a canonical display name
    ;; Then the suffix is removed
    (is (= "Palmeiras" (n/canonical "Palmeiras-SP")))
    (is (= "América" (n/canonical "América - MG")))
    (is (= "Nacional" (n/canonical "Nacional (URU)")))
    (is (= "Flamengo" (n/canonical "Flamengo"))))

  (testing "Scenario: accent-insensitive matching keys"
    ;; Given the same club written with and without accents
    ;; When reduced to a match key
    ;; Then both produce the same key
    (is (= (n/team-key "São Paulo") (n/team-key "Sao Paulo")))
    (is (= (n/team-key "Grêmio") (n/team-key "Gremio"))))

  (testing "Scenario: distinct clubs sharing a base name stay distinct"
    ;; Given two different clubs (Atlético-MG and Atlético-PR)
    ;; When reduced to grouping keys
    ;; Then the keys differ (the state suffix is preserved)
    (is (not= (n/team-key "Atletico-MG") (n/team-key "Atletico-PR")))
    (is (= "atletico mg" (n/team-key "Atlético - MG")))))

(deftest team-matching
  (testing "Scenario: a bare query matches a suffixed team name"
    ;; Given a user query 'Flamengo' and a dataset name 'Flamengo-RJ'
    ;; When tested for a match
    ;; Then they match
    (is (n/team-matches? "Flamengo" "Flamengo-RJ"))
    (is (n/team-matches? "Inter" "Internacional"))
    (is (not (n/team-matches? "Santos" "Flamengo")))))

(deftest date-normalization
  (testing "Scenario: handle ISO, datetime and Brazilian date formats"
    ;; Given dates in the three formats present in the data
    ;; When normalized
    ;; Then all become ISO yyyy-MM-dd
    (is (= "2012-05-19" (n/norm-date "2012-05-19 18:30:00")))
    (is (= "2023-09-24" (n/norm-date "2023-09-24")))
    (is (= "2003-03-29" (n/norm-date "29/03/2003")))
    (is (nil? (n/norm-date "")))))

(deftest number-parsing
  (testing "Scenario: parse integer-ish strings including float form"
    (is (= 2 (n/->int "2")))
    (is (= 2 (n/->int "2.0")))
    (is (nil? (n/->int "")))
    (is (nil? (n/->int nil)))))
