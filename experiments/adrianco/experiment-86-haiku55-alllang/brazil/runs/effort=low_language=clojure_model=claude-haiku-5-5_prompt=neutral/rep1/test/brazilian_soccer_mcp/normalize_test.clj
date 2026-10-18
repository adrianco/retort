(ns brazilian-soccer-mcp.normalize-test
  (:require [clojure.test :refer [deftest is testing]]
            [brazilian-soccer-mcp.normalize :as n]))

(deftest team-key-strips-state-and-decorations
  (testing "hyphenated state suffix"
    (is (= {:base "palmeiras" :state "sp"} (n/team-key "Palmeiras-SP"))))
  (testing "spaced state suffix after a parenthetical note"
    (is (= {:base "boavista sport club" :state "rj"}
           (n/team-key "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"))))
  (testing "country code in parentheses carries no state"
    (is (= {:base "nacional" :state nil} (n/team-key "Nacional (URU)"))))
  (testing "unhyphenated upper-case state"
    (is (= {:base "botafogo" :state "rj"} (n/team-key "Botafogo RJ"))))
  (testing "a plain name with no suffix"
    (is (= {:base "sao paulo" :state nil} (n/team-key "Sao Paulo")))))

(deftest team-key-is-accent-and-alias-insensitive
  (is (= (n/team-key "São Paulo") (n/team-key "Sao Paulo")))
  (is (= (:base (n/team-key "Sport Club Corinthians Paulista")) (:base (n/team-key "Corinthians-SP"))))
  (is (= (:base (n/team-key "Vasco Da Gama RJ")) (:base (n/team-key "Vasco da Gama")))))

(deftest atletico-pr-is-not-atletico-mg
  (is (n/same-team? (n/team-key "Atletico pr") (n/team-key "Athletico Paranaense")))
  (is (n/same-team? (n/team-key "Athletico-PR") (n/team-key "Atletico Paranaense")))
  (is (not (n/same-team? (n/team-key "Atletico pr") (n/team-key "Atletico mg"))))
  (is (not (n/same-team? (n/team-key "Atletico mg") (n/team-key "Athletico-PR")))))

(deftest same-team-uses-state-only-when-both_sides_have_it
  (is (n/same-team? (n/team-key "Palmeiras-SP") (n/team-key "Palmeiras")))
  (is (n/same-team? (n/team-key "Palmeiras") (n/team-key "Palmeiras-SP")))
  (is (not (n/same-team? (n/team-key "Atletico-MG") (n/team-key "Atletico-GO"))))
  (is (not (n/same-team? (n/team-key "Palmeiras") (n/team-key "Santos")))))

(deftest display-name-drops-decorations
  (is (= "Palmeiras" (n/display-name "Palmeiras-SP")))
  (is (= "Nacional" (n/display-name "Nacional (URU)")))
  (is (= "São Paulo" (n/display-name "São Paulo"))))

(deftest parse-date-handles-each-source-format
  (is (= "2023-09-24" (str (n/parse-date "2023-09-24"))))
  (is (= "2012-05-19" (str (n/parse-date "2012-05-19 18:30:00"))))
  (is (= "2003-03-29" (str (n/parse-date "29/03/2003"))))
  (is (nil? (n/parse-date "not a date")))
  (is (nil? (n/parse-date "2023-13-45")))
  (is (nil? (n/parse-date nil))))
