;; =============================================================================
;; brazilian-soccer.normalize-test
;; -----------------------------------------------------------------------------
;; BDD (Given/When/Then) coverage for the normalisation rules that let the system
;; reconcile the datasets' inconsistent team names, accents and date formats.
;; =============================================================================
(ns brazilian-soccer.normalize-test
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.normalize :as n]))

(deftest accents-test
  (testing "Given accented Portuguese names, When stripped, Then ASCII results"
    (is (= "Sao Paulo" (n/strip-accents "São Paulo")))
    (is (= "Gremio" (n/strip-accents "Grêmio")))
    (is (= "Avai" (n/strip-accents "Avaí")))))

(deftest team-key-test
  (testing "Given a team with a redundant state suffix, When keyed, Then the suffix is dropped"
    (is (= "palmeiras" (n/team-key "Palmeiras-SP")))
    (is (= "palmeiras" (n/team-key "Palmeiras")))
    (is (= "sao paulo" (n/team-key "São Paulo-SP")))
    (is (= "sao paulo" (n/team-key "Sao Paulo"))))

  (testing "Given clubs distinguished only by state, When keyed, Then state is preserved"
    (is (= "atletico-mg" (n/team-key "Atletico-MG")))
    (is (= "atletico-pr" (n/team-key "Atletico-PR")))
    (is (not= (n/team-key "Atletico-MG") (n/team-key "Atletico-PR")))
    (is (= "america-mg" (n/team-key "América-MG"))))

  (testing "Given a country-coded name, When keyed, Then the country tag is dropped"
    (is (= "nacional" (n/team-key "Nacional (URU)")))
    (is (= "barcelona" (n/team-key "Barcelona-EQU"))))

  (testing "Given blank input, When keyed, Then nil"
    (is (nil? (n/team-key "")))
    (is (nil? (n/team-key nil)))))

(deftest display-name-test
  (testing "Given a suffixed name, When displayed, Then it is clean"
    (is (= "Flamengo" (n/display-name "Flamengo-RJ")))
    (is (= "Atletico-MG" (n/display-name "Atletico-MG")))))

(deftest iso-date-test
  (testing "Given the three dataset date formats, When parsed, Then ISO yyyy-MM-dd"
    (is (= "2012-05-19" (n/iso-date "2012-05-19 18:30:00")))
    (is (= "2023-09-24" (n/iso-date "2023-09-24")))
    (is (= "2003-03-29" (n/iso-date "29/03/2003")))
    (is (nil? (n/iso-date "")))
    (is (nil? (n/iso-date "not-a-date")))))

(deftest number-parsing-test
  (testing "Given messy numeric CSV cells, When parsed, Then ints/doubles or nil"
    (is (= 2 (n/->int "2")))
    (is (= 2 (n/->int "2.0")))
    (is (= 3 (n/->int " 3 ")))
    (is (nil? (n/->int "")))
    (is (= 4.0 (n/->double "4.0")))))
