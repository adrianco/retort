(ns brazilian-soccer-mcp.normalization-test
  (:require [clojure.test :refer :all]
            [brazilian-soccer-mcp.normalization :as norm]))

(deftest normalize-team-name-test
  (testing "removes state suffix from team names"
    (is (= "Palmeiras" (norm/normalize-team "Palmeiras-SP")))
    (is (= "Flamengo" (norm/normalize-team "Flamengo-RJ")))
    (is (= "Sport" (norm/normalize-team "Sport-PE")))
    (is (= "Portuguesa" (norm/normalize-team "Portuguesa-SP"))))

  (testing "leaves names without state suffix unchanged"
    (is (= "Flamengo" (norm/normalize-team "Flamengo")))
    (is (= "Palmeiras" (norm/normalize-team "Palmeiras")))
    (is (= "Nacional (URU)" (norm/normalize-team "Nacional (URU)"))))

  (testing "handles team names with dashes in the middle"
    (is (= "Athletico-PR" (norm/normalize-team "Athletico-PR")))
    (is (= "Botafogo" (norm/normalize-team "Botafogo-RJ"))))

  (testing "trims whitespace"
    (is (= "Flamengo" (norm/normalize-team " Flamengo-RJ "))))

  (testing "nil-safe"
    (is (nil? (norm/normalize-team nil)))
    (is (= "" (norm/normalize-team "")))))

(deftest team-matches-test
  (testing "exact match"
    (is (norm/team-matches? "Flamengo" "Flamengo")))

  (testing "match ignoring state suffix"
    (is (norm/team-matches? "Flamengo" "Flamengo-RJ"))
    (is (norm/team-matches? "Flamengo-RJ" "Flamengo")))

  (testing "case-insensitive match"
    (is (norm/team-matches? "flamengo" "Flamengo"))
    (is (norm/team-matches? "FLAMENGO" "Flamengo-RJ")))

  (testing "partial match (contains)"
    (is (norm/team-matches? "Corinthians" "Sport Club Corinthians Paulista"))
    (is (norm/team-matches? "São Paulo" "São Paulo FC")))

  (testing "no match"
    (is (not (norm/team-matches? "Flamengo" "Palmeiras")))
    (is (not (norm/team-matches? "Santos" "Flamengo-RJ")))))

(deftest canonical-name-test
  (testing "returns known canonical names"
    (is (= "Corinthians" (norm/canonical-name "Sport Club Corinthians Paulista")))
    (is (= "Athletico Paranaense" (norm/canonical-name "Athletico-PR")))
    (is (= "São Paulo" (norm/canonical-name "São Paulo FC"))))

  (testing "returns normalized name when no canonical known"
    (is (= "Flamengo" (norm/canonical-name "Flamengo-RJ")))
    (is (= "Palmeiras" (norm/canonical-name "Palmeiras-SP")))))
