(ns brazilian-soccer.normalize-test
  "BDD-style tests for team-name normalization (handles state suffixes,
   country codes, accents and the punctuation-insensitive match key)."
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.normalize :as norm]))

(deftest display-name-strips-suffixes
  (testing "Given raw team names with state/country tags"
    (testing "When normalized, Then the tag is removed"
      (is (= "Palmeiras" (norm/display-name "Palmeiras-SP")))
      (is (= "América"   (norm/display-name "América - MG")))
      (is (= "Nacional"  (norm/display-name "Nacional (URU)")))
      (is (= "Barcelona" (norm/display-name "Barcelona-EQU")))
      (is (= "Flamengo"  (norm/display-name "Flamengo"))))))

(deftest accent-insensitive-keys
  (testing "Given accented names, When keyed, Then accents/punctuation drop out"
    (is (= "saopaulo"  (norm/match-key "São Paulo-SP")))
    (is (= "gremio"    (norm/match-key "Grêmio")))
    (is (= (norm/match-key "São Paulo") (norm/match-key "Sao Paulo")))))

(deftest substring-matching
  (testing "Given a query, When matched against a full name, Then substrings match"
    (is (norm/matches? "flamengo" "Flamengo-RJ"))
    (is (norm/matches? "corinthians" "Sport Club Corinthians Paulista"))
    (is (norm/matches? "sao paulo" "São Paulo"))
    (is (not (norm/matches? "santos" "Flamengo")))
    (is (not (norm/matches? "" "Flamengo")))))
