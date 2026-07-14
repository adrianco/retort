(ns soccer.data-test
  "Unit tests for the normalization internals that the acceptance tests drove
   out: team-name handling, date parsing and goal parsing.  These are the
   finer-grained TDD layer beneath the acceptance suite."
  (:require [clojure.test :refer [deftest testing is]]
            [soccer.data :as data]))

(deftest accent-and-case-insensitive-matching
  (testing "normalization strips accents, lowercases and collapses whitespace"
    (is (= "sao paulo" (data/norm "São  Paulo")))
    (is (= "gremio" (data/norm "Grêmio")))
    (is (= (data/norm "Avaí") (data/norm "Avai")))))

(deftest bare-query-is-a-substring-of-suffixed-record
  (testing "the matching key keeps the suffix so substrings still match"
    (is (clojure.string/includes? (data/norm "Flamengo-RJ") (data/norm "Flamengo")))
    (is (clojure.string/includes? (data/norm "Nacional (URU)") (data/norm "Nacional")))))

(deftest display-name-drops-state-and-country-suffixes
  (testing "human-facing names are cleaned of suffixes"
    (is (= "Flamengo" (data/display-name "Flamengo-RJ")))
    (is (= "Nacional" (data/display-name "Nacional (URU)")))
    (is (= "Barcelona" (data/display-name "Barcelona-EQU")))
    (is (= "Internacional" (data/display-name "Internacional - RS")))))

(deftest distinct-clubs-stay-distinct
  (testing "different state suffixes do not collapse to the same key"
    (is (not= (data/norm "Atletico-MG") (data/norm "Atletico-PR")))))

(deftest date-parsing-handles-every-format
  (testing "ISO, ISO-with-time and Brazilian dates all become yyyy-MM-dd"
    (is (= "2023-09-24" (data/parse-date "2023-09-24")))
    (is (= "2012-05-19" (data/parse-date "2012-05-19 18:30:00")))
    (is (= "2003-03-29" (data/parse-date "29/03/2003")))
    (is (nil? (data/parse-date "")))))

(deftest goal-parsing-handles-ints-and-floats
  (testing "goals may arrive as ints, float strings or blanks"
    (is (= 1 (data/parse-int-ish "1")))
    (is (= 1 (data/parse-int-ish "1.0")))
    (is (= 3 (data/parse-int-ish 3)))
    (is (nil? (data/parse-int-ish "")))
    (is (nil? (data/parse-int-ish nil)))))
