(ns brazilian-soccer.normalize-test
  "Context
  =======
  BDD (Given/When/Then) tests for team-name normalisation — the foundation that
  lets the same club be recognised across the datasets' many spellings."
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.normalize :as nz]))

(deftest accent-and-suffix-normalisation
  (testing "Scenario: accented and suffixed spellings collapse to one key"
    ;; Given two spellings of the same club
    ;; When normalised to a match key
    ;; Then the keys are equal
    (is (= (nz/match-key "Grêmio-RS") (nz/match-key "Gremio")))
    (is (= (nz/match-key "Avaí-SC") (nz/match-key "Avai")))
    (is (= (nz/match-key "São Paulo") (nz/match-key "Sao Paulo")))))

(deftest country-code-suffix
  (testing "Scenario: parenthesised and dashed country codes are stripped"
    (is (= (nz/match-key "Nacional (URU)") (nz/match-key "Nacional")))
    (is (= (nz/match-key "Barcelona-EQU") (nz/match-key "Barcelona")))))

(deftest ambiguous-atletico-clubs-stay-distinct
  (testing "Scenario: Mineiro, Paranaense and Goianiense are different clubs"
    ;; Given the three Atlético clubs in their various spellings
    ;; Then Mineiro != Paranaense != Goianiense
    (is (not= (nz/match-key "Atlético") (nz/match-key "Athletico")))
    (is (= (nz/match-key "Atletico-MG") (nz/match-key "Atletico Mineiro")))
    (is (= (nz/match-key "Atletico-PR") (nz/match-key "Athletico Paranaense")))
    (is (not= (nz/match-key "Atletico-MG") (nz/match-key "Atletico-GO")))))

(deftest corporate-and-city-reductions
  (testing "Scenario: corporate/city qualifiers do not split a club"
    (is (= (nz/match-key "EC Bahia") (nz/match-key "Bahia")))
    (is (= (nz/match-key "Fortaleza FC") (nz/match-key "Fortaleza")))
    (is (= (nz/match-key "Vasco Da Gama RJ") (nz/match-key "Vasco")))
    (is (= (nz/match-key "Botafogo RJ") (nz/match-key "Botafogo")))))

(deftest fuzzy-team-matching
  (testing "Scenario: a short query matches a longer official name"
    ;; Given a full legal name in the data
    ;; When the user queries with a common short name
    ;; Then team-matches? is true
    (is (nz/team-matches? "Corinthians" "Sport Club Corinthians Paulista"))
    (is (nz/team-matches? "Flamengo" "Flamengo-RJ"))
    (is (not (nz/team-matches? "Flamengo" "Fluminense")))))
