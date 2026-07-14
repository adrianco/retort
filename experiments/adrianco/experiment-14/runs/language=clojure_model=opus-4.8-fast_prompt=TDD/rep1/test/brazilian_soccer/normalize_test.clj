(ns brazilian-soccer.normalize-test
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.normalize :as norm]))

(deftest strip-accents-test
  (testing "removes diacritics from Portuguese text"
    (is (= "Sao Paulo" (norm/strip-accents "São Paulo")))
    (is (= "Gremio" (norm/strip-accents "Grêmio")))
    (is (= "Avai" (norm/strip-accents "Avaí")))
    (is (= "Atletico" (norm/strip-accents "Atlético")))))

(deftest clean-team-test
  (testing "strips trailing state suffix with hyphen"
    (is (= "Palmeiras" (norm/clean-team "Palmeiras-SP")))
    (is (= "Flamengo" (norm/clean-team "Flamengo-RJ"))))
  (testing "strips trailing country code in parentheses"
    (is (= "Nacional" (norm/clean-team "Nacional (URU)")))
    (is (= "Barcelona" (norm/clean-team "Barcelona-EQU"))))
  (testing "strips ' - XX' state suffix with spaces"
    (is (= "Boavista Sport Club"
           (norm/clean-team "Boavista Sport Club - RJ"))))
  (testing "leaves plain names untouched"
    (is (= "Santos" (norm/clean-team "Santos")))
    (is (= "Corinthians" (norm/clean-team "Corinthians"))))
  (testing "trims surrounding whitespace"
    (is (= "Vasco" (norm/clean-team "  Vasco  ")))))

(deftest team-key-test
  (testing "produces an accent-folded lowercase key for matching"
    (is (= "sao paulo" (norm/team-key "São Paulo")))
    (is (= "palmeiras" (norm/team-key "Palmeiras-SP")))
    (is (= "gremio" (norm/team-key "Grêmio-RS")))
    (is (= (norm/team-key "Nacional (URU)") (norm/team-key "Nacional"))))
  (testing "folds the Athletico/Atlético orthographic variant"
    (is (= (norm/team-key "Athletico-PR") (norm/team-key "Atlético-PR")))
    (is (= (norm/strict-key "Athletico-PR") (norm/strict-key "Atletico-PR")))))

(deftest strict-key-test
  (testing "preserves the state/country suffix so distinct clubs stay distinct"
    (is (not= (norm/strict-key "Atlético-MG") (norm/strict-key "Atlético-GO")))
    (is (not= (norm/strict-key "América-MG") (norm/strict-key "América-RN"))))
  (testing "still folds accents, case and suffix punctuation across files"
    (is (= (norm/strict-key "Atlético-MG") (norm/strict-key "atletico-mg")))
    (is (= (norm/strict-key "Nacional (URU)") (norm/strict-key "Nacional-URU")))
    (is (= (norm/strict-key "Boavista - RJ") (norm/strict-key "Boavista-RJ"))))
  (testing "unsuffixed name variants collapse"
    (is (= (norm/strict-key "São Paulo") (norm/strict-key "Sao Paulo")))))

(deftest team-suffix-test
  (testing "extracts the lowercased state/country suffix, or nil when absent"
    (is (= "mg" (norm/team-suffix "Atlético-MG")))
    (is (= "rj" (norm/team-suffix "Flamengo-RJ")))
    (is (= "uru" (norm/team-suffix "Nacional (URU)")))
    (is (nil? (norm/team-suffix "Flamengo")))
    (is (nil? (norm/team-suffix "Vasco da Gama")))))

(deftest same-team?-test
  (testing "matches names across naming conventions"
    (is (norm/same-team? "Palmeiras-SP" "Palmeiras"))
    (is (norm/same-team? "São Paulo" "Sao Paulo"))
    (is (not (norm/same-team? "Palmeiras" "Santos")))))

(deftest parse-date-test
  (testing "ISO date with time"
    (is (= (java.time.LocalDate/of 2012 5 19)
           (norm/parse-date "2012-05-19 18:30:00"))))
  (testing "plain ISO date"
    (is (= (java.time.LocalDate/of 2023 9 24)
           (norm/parse-date "2023-09-24"))))
  (testing "Brazilian DD/MM/YYYY format"
    (is (= (java.time.LocalDate/of 2003 3 29)
           (norm/parse-date "29/03/2003"))))
  (testing "blank or nil returns nil"
    (is (nil? (norm/parse-date "")))
    (is (nil? (norm/parse-date nil)))))

(deftest parse-int-test
  (testing "parses integer strings, including float-looking values"
    (is (= 1 (norm/parse-int "1")))
    (is (= 2 (norm/parse-int "2.0")))
    (is (nil? (norm/parse-int "")))
    (is (nil? (norm/parse-int nil)))))
