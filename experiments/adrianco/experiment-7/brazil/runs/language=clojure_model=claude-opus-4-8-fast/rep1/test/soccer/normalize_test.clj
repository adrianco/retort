;; =============================================================================
;; soccer.normalize-test — BDD tests for name/date normalization
;; -----------------------------------------------------------------------------
;; Project: brazilian-soccer-mcp
;; Style: Given / When / Then behaviour scenarios.
;; =============================================================================
(ns soccer.normalize-test
  (:require [clojure.test :refer [deftest testing is]]
            [soccer.normalize :as n])
  (:import [java.time LocalDate]))

(deftest strip-accents-scenario
  (testing "Given accented Portuguese text, When stripped, Then ASCII remains"
    (is (= "Sao Paulo" (n/strip-accents "São Paulo")))
    (is (= "Gremio" (n/strip-accents "Grêmio")))
    (is (= "Avai" (n/strip-accents "Avaí")))))

(deftest canonical-name-scenarios
  (testing "Given a state suffix, When canonicalized, Then suffix is removed"
    (is (= "Palmeiras" (n/canonical-name "Palmeiras-SP")))
    (is (= "Flamengo" (n/canonical-name "Flamengo-RJ"))))
  (testing "Given a spaced state token, When canonicalized, Then it is removed"
    (is (= "América Mineiro" (n/canonical-name "America MG")) "alias maps America MG")
    (is (= "Boavista" (n/canonical-name "Boavista RJ"))))
  (testing "Given a country code, When canonicalized, Then it is removed"
    (is (= "Nacional" (n/canonical-name "Nacional (URU)")))
    (is (= "Barcelona" (n/canonical-name "Barcelona-EQU"))))
  (testing "Given a known full name, When canonicalized, Then mapped to alias"
    (is (= "Corinthians"
           (n/canonical-name "Sport Club Corinthians Paulista")))
    (is (= "São Paulo" (n/canonical-name "Sao Paulo")))))

(deftest same-team-scenarios
  (testing "Given two spellings of one club, When compared, Then they match"
    (is (n/same-team? "Palmeiras-SP" "Palmeiras"))
    (is (n/same-team? "São Paulo" "Sao Paulo FC"))
    (is (n/same-team? "Grêmio" "Gremio"))
    (is (not (n/same-team? "Flamengo" "Fluminense")))))

(deftest name-matches-scenarios
  (testing "Given a partial query, When matched, Then it finds the full name"
    (is (n/name-matches? "Atletico" "Atlético Mineiro"))
    (is (n/name-matches? "fla" "Flamengo"))
    (is (not (n/name-matches? "Santos" "Flamengo")))))

(deftest parse-date-scenarios
  (testing "Given various date formats, When parsed, Then LocalDate is returned"
    (is (= (LocalDate/of 2023 9 24) (n/parse-date "2023-09-24")))
    (is (= (LocalDate/of 2012 5 19) (n/parse-date "2012-05-19 18:30:00")))
    (is (= (LocalDate/of 2003 3 29) (n/parse-date "29/03/2003")))
    (is (= (LocalDate/of 2003 1 1) (n/parse-date "2003.01.01"))))
  (testing "Given junk or NA, When parsed, Then nil"
    (is (nil? (n/parse-date "NA")))
    (is (nil? (n/parse-date "")))
    (is (nil? (n/parse-date nil)))))
