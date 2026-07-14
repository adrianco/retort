;; =============================================================================
;; Tests for brsoccer.normalize -- the name/date normalization that makes
;; cross-dataset matching work.
;; =============================================================================
(ns brsoccer.normalize-test
  (:require [clojure.test :refer [deftest is testing]]
            [brsoccer.normalize :as n]))

(deftest team-key-unifies-spellings
  (testing "state/country suffixes, accents, spaces and case all collapse"
    (is (= "saopaulo" (n/team-key "São Paulo-SP")))
    (is (= "saopaulo" (n/team-key "Sao Paulo")))
    (is (= (n/team-key "Palmeiras-SP") (n/team-key "Palmeiras")))
    (is (= (n/team-key "Flamengo-RJ") (n/team-key "Flamengo")))
    (is (= (n/team-key "Grêmio") (n/team-key "Gremio")))
    (is (= (n/team-key "Nacional (URU)") (n/team-key "Nacional")))
    (is (= (n/team-key "América - MG") (n/team-key "America-MG")))))

(deftest disambiguates-and-folds-cross-dataset-names
  (testing "the three Atléticos stay DISTINCT despite sharing a base name"
    (is (= "atleticomg" (n/team-key "Atletico-MG")))
    (is (= "atleticogo" (n/team-key "Atletico-GO")))
    (is (= "atleticopr" (n/team-key "Athletico-PR")))
    (is (not= (n/team-key "Atletico-MG") (n/team-key "Atletico-GO"))))
  (testing "long-form and short-form spellings fold onto one key"
    (is (= (n/team-key "Atletico-MG") (n/team-key "Atletico Mineiro")))
    (is (= (n/team-key "Athletico-PR") (n/team-key "Athletico Paranaense")))
    (is (= (n/team-key "Athletico-PR") (n/team-key "Atletico Paranaense")))
    (is (= (n/team-key "Bahia") (n/team-key "EC Bahia")))
    (is (= (n/team-key "Vasco") (n/team-key "Vasco da Gama RJ")))
    (is (= (n/team-key "Fortaleza") (n/team-key "Fortaleza FC")))))

(deftest blank-handling
  (is (nil? (n/team-key "")))
  (is (nil? (n/team-key nil))))

(deftest date-parsing
  (testing "all three documented date formats normalize to ISO"
    (is (= "2012-05-19" (n/parse-date "2012-05-19 18:30:00")))
    (is (= "2003-03-29" (n/parse-date "29/03/2003")))
    (is (= "2023-09-24" (n/parse-date "2023-09-24")))
    (is (nil? (n/parse-date "")))
    (is (= 2003 (n/year-of "2003-03-29")))))

(deftest numeric-parsing
  (is (= 3 (n/parse-int "3")))
  (is (= 3 (n/parse-int "3.0")))   ; BR-Football stores goals as floats
  (is (nil? (n/parse-int "")))
  (is (= 2.0 (n/parse-num "2"))))
