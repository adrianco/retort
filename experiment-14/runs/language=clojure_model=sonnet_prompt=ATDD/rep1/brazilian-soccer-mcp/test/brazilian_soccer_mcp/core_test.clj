(ns brazilian-soccer-mcp.core-test
  "Unit tests for normalize, data, and tools namespaces."
  (:require [clojure.test :refer [deftest is testing]]
            [brazilian-soccer-mcp.normalize :as norm]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.tools :as tools]))

;; ---------------------------------------------------------------------------
;; normalize tests
;; ---------------------------------------------------------------------------

(deftest canonicalize-known-aliases
  (testing "State-suffix forms map to canonical name"
    (is (= "Flamengo"    (norm/canonicalize "Flamengo-RJ")))
    (is (= "Palmeiras"   (norm/canonicalize "Palmeiras-SP")))
    (is (= "Grêmio"      (norm/canonicalize "Gremio")))
    (is (= "São Paulo"   (norm/canonicalize "Sao Paulo")))
    (is (= "Atlético-MG" (norm/canonicalize "Atletico Mineiro")))))

(deftest team-matches-handles-variants
  (testing "team-matches? handles name variants correctly"
    (is (norm/team-matches? "Flamengo"  "Flamengo-RJ"))
    (is (norm/team-matches? "Flamengo-RJ" "Flamengo"))
    (is (norm/team-matches? "Palmeiras" "Palmeiras-SP"))
    (is (not (norm/team-matches? "Flamengo" "Fluminense")))))

(deftest normalize-date-formats
  (testing "Date normalization handles all input formats"
    (is (= "2012-05-19" (data/normalize-date "2012-05-19 18:30:00")))
    (is (= "2003-03-29" (data/normalize-date "29/03/2003")))
    (is (= "2023-09-24" (data/normalize-date "2023-09-24")))
    (is (= "2019-06-15" (data/normalize-date "2019-06-15T20:00:00")))))
