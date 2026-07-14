(ns brazilian-soccer.data-test
  "Feature: Data loading and normalization

  Scenario: All six CSV files are loadable and queryable
  Scenario: Team name variations are normalized for consistent matching
  Scenario: Multiple date formats are handled
  Scenario: UTF-8 / accented text is handled"
  (:require [brazilian-soccer.data :as data]
            [clojure.test :refer [deftest is testing]]))

(def db (delay @data/db))

(deftest all-csv-files-load
  (testing "Given the data directory, when all datasets are loaded"
    (let [{:keys [matches extended players]} @db
          sources (set (map :source matches))]
      (testing "then every CSV file contributes rows"
        (is (contains? sources :brasileirao) "Brasileirao_Matches.csv")
        (is (contains? sources :historical) "novo_campeonato_brasileiro.csv")
        (is (contains? sources :cup) "Brazilian_Cup_Matches.csv")
        (is (contains? sources :libertadores) "Libertadores_Matches.csv")
        (is (contains? sources :extended) "BR-Football-Dataset.csv")
        (is (= 10296 (count extended)) "all BR-Football rows kept for stats")
        (is (= 18207 (count players)) "fifa_data.csv"))
      (testing "and overlapping seasons are deduplicated, not double counted"
        (let [serie-a-2015 (filter #(and (= "Brasileirão Série A" (:competition %))
                                         (= 2015 (:season %)))
                                   matches)]
          (is (= 380 (count serie-a-2015))
              "a 20-team double round-robin season has exactly 380 matches"))))))

(deftest team-name-normalization
  (testing "Given names in different conventions, when normalized, then they match"
    (letfn [(same? [a b] (= (:key (data/norm-team a)) (:key (data/norm-team b))))]
      (is (data/team-matches? (data/norm-team "Palmeiras") (data/norm-team "Palmeiras-SP"))
          "state suffix")
      (is (data/team-matches? (data/norm-team "São Paulo") (data/norm-team "Sao Paulo"))
          "accents")
      (is (same? "América - MG" "America MG") "spaced suffix vs plain state word")
      (is (same? "Athletico Paranaense" "Atlético-PR") "alias to canonical club")
      (is (same? "Atletico Mineiro" "Atlético-MG") "alias with accent")
      (is (same? "Fortaleza FC" "Fortaleza") "club-type token stripped")
      (is (same? "EC Juventude" "Juventude") "leading club-type token stripped")
      (is (same? "Vasco da Gama" "Vasco") "long-form name")
      (is (not (same? "Atlético-MG" "Athletico-PR"))
          "clubs sharing a base name stay distinct by state")
      (is (not (data/team-matches? (data/norm-team "América - RN") (data/norm-team "América - MG")))
          "state conflict blocks a match")
      (is (not (data/team-matches? (data/norm-team "America") (data/norm-team "Americano RJ")))
          "no partial-word false positives"))))

(deftest date-parsing
  (testing "Given the three date formats in the data, when parsed"
    (is (= "2023-09-24" (str (data/parse-date "2023-09-24"))) "ISO date")
    (is (= "2012-05-19" (str (data/parse-date "2012-05-19 18:30:00"))) "ISO with time")
    (is (= "2003-03-29" (str (data/parse-date "29/03/2003"))) "Brazilian format")
    (is (nil? (data/parse-date "")) "blank")
    (is (nil? (data/parse-date "NA")) "not-available marker")))

(deftest score-parsing
  (testing "Given the score encodings in the data, when parsed"
    (is (= 2 (data/parse-num "2")) "plain integer")
    (is (= 2 (data/parse-num "2.0")) "float-encoded integer")
    (is (nil? (data/parse-num "NA")) "missing score")
    (is (nil? (data/parse-num "")) "blank score")))

(deftest competition-normalization
  (testing "Given free-form competition names, when normalized"
    (is (= "Brasileirão Série A" (data/norm-competition "brasileirao")))
    (is (= "Brasileirão Série A" (data/norm-competition "Serie A")))
    (is (= "Brasileirão Série A" (data/norm-competition "Brasileirão Série A")))
    (is (= "Copa do Brasil" (data/norm-competition "copa do brasil")))
    (is (= "Copa Libertadores" (data/norm-competition "Libertadores")))
    (is (= "Brasileirão Série B" (data/norm-competition "serie b")))
    (is (nil? (data/norm-competition "premier league")))))

(deftest utf8-handling
  (testing "Given accented Brazilian team names, when loaded, then they survive intact"
    (let [raws (into #{} (mapcat (juxt :home-raw :away-raw)) (:matches @db))]
      (is (some #(re-find #"Grêmio" %) raws) "Grêmio kept its accent")
      (is (some #(re-find #"Atlético" %) raws) "Atlético kept its accent"))))
