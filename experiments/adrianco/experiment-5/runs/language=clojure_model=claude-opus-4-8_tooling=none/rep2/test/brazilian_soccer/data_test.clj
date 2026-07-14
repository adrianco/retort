;; =============================================================================
;; brazilian-soccer.data-test
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   BDD (Given/When/Then) tests for the data-access layer of the Brazilian
;;   Soccer MCP server: team-name normalisation, fuzzy matching, date parsing,
;;   integer coercion, and loading of all six real CSV datasets.
;; =============================================================================
(ns brazilian-soccer.data-test
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.data :as data]))

(deftest team-name-normalisation
  (testing "Given inconsistent team names, When cleaned, Then parens drop & suffix is kept"
    (is (= "Palmeiras-SP" (data/clean-name "Palmeiras-SP")))
    (is (= "América-MG" (data/clean-name "América - MG")))
    (is (= "Nacional" (data/clean-name "Nacional (URU)")))
    (is (= "Barcelona-EQU" (data/clean-name "Barcelona-EQU")))
    (is (= "Boavista Sport Club-RJ"
           (data/clean-name "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"))))

  (testing "Given accented names, When keyed, Then accents fold and suffix is retained"
    (is (= "sao paulo" (data/team-key "São Paulo")))
    (is (= "gremio rs" (data/team-key "Grêmio-RS")))
    (is (= "flamengo rj" (data/team-key "Flamengo-RJ"))))

  (testing "Given same-named clubs in different states, When keyed, Then keys are distinct"
    (is (not= (data/team-key "Atlético-MG") (data/team-key "Atlético-PR")))
    (is (not= (data/team-key "Atlético-MG") (data/team-key "Atlético-GO")))))

(deftest fuzzy-team-matching
  (testing "Given a query, When matched against a team name, Then variants match"
    (is (data/team-matches? "Flamengo" "Flamengo-RJ"))
    (is (data/team-matches? "flamengo" "Flamengo"))
    (is (data/team-matches? "São Paulo FC" "Sao Paulo"))
    (is (data/team-matches? "Gremio" "Grêmio - RS"))
    (is (not (data/team-matches? "Flamengo" "Fluminense")))))

(deftest date-parsing
  (testing "Given multiple date formats, When parsed, Then normalised to ISO"
    (is (= "2012-05-19" (data/parse-date "2012-05-19 18:30:00")))
    (is (= "2023-09-24" (data/parse-date "2023-09-24")))
    (is (= "2003-03-29" (data/parse-date "29/03/2003")))
    (is (nil? (data/parse-date "")))
    (is (nil? (data/parse-date nil)))))

(deftest integer-coercion
  (testing "Given numeric-ish strings, When coerced, Then handles decimals/blanks"
    (is (= 1 (data/to-int "1")))
    (is (= 1 (data/to-int "1.0")))
    (is (= 2019 (data/to-int "2019")))
    (is (nil? (data/to-int "")))
    (is (nil? (data/to-int nil)))))

(deftest real-datasets-load
  (testing "Given the provided CSVs, When loaded, Then all are present & non-trivial"
    (let [ms (data/all-matches)
          ps (data/all-players)
          sources (set (map :source ms))]
      ;; All five match files contributed rows.
      (is (contains? sources "Brasileirao_Matches.csv"))
      (is (contains? sources "Brazilian_Cup_Matches.csv"))
      (is (contains? sources "Libertadores_Matches.csv"))
      (is (contains? sources "BR-Football-Dataset.csv"))
      (is (contains? sources "novo_campeonato_brasileiro.csv"))
      ;; Sanity on volume (well over 20k matches combined, 18k players).
      (is (> (count ms) 20000) (str "matches=" (count ms)))
      (is (> (count ps) 18000) (str "players=" (count ps)))
      ;; Every loaded match has the required normalised fields.
      (is (every? (fn [m] (and (string? (:home m)) (string? (:away m))
                               (integer? (:home-goal m)) (integer? (:away-goal m))))
                  (take 1000 ms))))))
