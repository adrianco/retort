(ns brazilian-soccer-mcp.normalize-test
  (:require [clojure.test :refer [deftest is testing]]
            [brazilian-soccer-mcp.normalize :as norm]))

(deftest normalize-preserves-state-but-bare-strips
  (testing "normalize keeps the state code (so MG vs GO stay distinct)"
    (is (not= (norm/normalize "Atlético-MG") (norm/normalize "Atlético-GO")))
    (is (= (norm/normalize "Atlético-MG") (norm/normalize "Atletico MG"))))
  (testing "normalize-bare strips state for fuzzy matching"
    (is (= (norm/normalize-bare "Palmeiras-SP") (norm/normalize-bare "Palmeiras")))
    (is (= (norm/normalize-bare "Flamengo-RJ")  (norm/normalize-bare "Flamengo")))))

(deftest normalize-handles-accents
  (testing "São Paulo == Sao Paulo after normalization"
    (is (= (norm/normalize "São Paulo-SP") (norm/normalize "Sao Paulo-SP")))
    (is (= (norm/normalize "Grêmio-RS")    (norm/normalize "Gremio-RS")))
    (is (= (norm/normalize "Atlético-MG")  (norm/normalize "Atletico MG")))))

(deftest normalize-bare-does-not-strip-non-state-suffix
  (testing "trailing word that isn't a state code stays put"
    (is (= "atletico mineiro" (norm/normalize-bare "Atletico Mineiro")))))

(deftest athletico-paranaense-merges
  (testing "Athletico-PR and Atletico-PR are the same club"
    (is (= (norm/normalize "Athletico-PR") (norm/normalize "Atletico-PR")))))

(deftest matches-is-loose
  (testing "containment counts as a match for partial names"
    (is (norm/matches? "Flamengo"        "Flamengo-RJ"))
    (is (norm/matches? "São Paulo"       "Sao Paulo-SP"))
    (is (not (norm/matches? "Flamengo"   "Fluminense")))))
