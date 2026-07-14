;; =============================================================================
;; brazilian-soccer.normalize-test
;; -----------------------------------------------------------------------------
;; BDD (Given/When/Then) scenarios for team-name normalisation: stripping state
;; suffixes, country codes and descriptors, accent folding, and fuzzy matching.
;; =============================================================================
(ns brazilian-soccer.normalize-test
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.normalize :as norm]))

(deftest strip-accents-scenario
  (testing "Given accented Portuguese names, When folded, Then accents are removed"
    (is (= "Sao Paulo" (norm/strip-accents "São Paulo")))
    (is (= "Gremio"    (norm/strip-accents "Grêmio")))
    (is (= "Avai"      (norm/strip-accents "Avaí")))))

(deftest clean-team-scenario
  (testing "Given raw team strings with suffixes, When cleaned, Then suffix is dropped"
    (is (= "Palmeiras" (norm/clean-team "Palmeiras-SP")))
    (is (= "Flamengo"  (norm/clean-team "Flamengo-RJ")))
    (is (= "América"   (norm/clean-team "América - MG")))
    (is (= "Nacional"  (norm/clean-team "Nacional (URU)")))
    (is (= "Barcelona" (norm/clean-team "Barcelona-EQU"))))
  (testing "Given a descriptor in parentheses, When cleaned, Then it is removed"
    (is (= "Boavista Sport Club"
           (norm/clean-team "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"))))
  (testing "Given blank input, When cleaned, Then nil is returned"
    (is (nil? (norm/clean-team "   ")))
    (is (nil? (norm/clean-team nil)))))

(deftest match-key-scenario
  (testing "Given differently-formatted names of the same team, Then keys agree"
    (is (= (norm/match-key "Palmeiras-SP") (norm/match-key "Palmeiras")))
    (is (= (norm/match-key "São Paulo")    (norm/match-key "Sao Paulo")))
    (is (= "flamengo" (norm/match-key "Flamengo-RJ")))))

(deftest team-uid-scenario
  (testing "Given a state column, Then the two Brasileirão spellings align"
    (is (= (norm/team-uid "Flamengo-RJ" "RJ")
           (norm/team-uid "Flamengo" "RJ")))
    (is (= "flamengo rj" (norm/team-uid "Flamengo-RJ" "RJ"))))
  (testing "Given same base name different states, Then identities stay distinct"
    (is (not= (norm/team-uid "Atlético-MG" "MG")
              (norm/team-uid "Atlético-GO" "GO")))
    (is (= "atletico mg" (norm/team-uid "Atlético-MG" "MG"))))
  (testing "Given no state column, Then a dash-style suffix is kept in the key"
    (is (= "barcelona equ" (norm/team-uid "Barcelona-EQU" nil)))))

(deftest matches-team?-scenario
  (testing "Given a stored key, When queried, Then symmetric-substring matching holds"
    (is (norm/matches-team? "flamengo" "Flamengo"))
    (is (norm/matches-team? "flamengo" "Flamengo-RJ"))
    (is (norm/matches-team? "sao paulo fc" "São Paulo"))
    (is (norm/matches-team? "sao paulo" "São Paulo FC"))
    (is (not (norm/matches-team? "flamengo" "Fluminense")))
    (is (not (norm/matches-team? "flamengo" "")))))
