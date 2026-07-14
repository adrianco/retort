(ns brazilian-soccer.data-test
  "BDD scenarios for dataset loading, team-name normalization, date
  handling and cross-file deduplication.
  Structure: Given (fixtures) / When (action) / Then (assertions)."
  (:require [clojure.test :refer [deftest is testing]]
            [brazilian-soccer.data :as data]))

(deftest scenario-all-csv-files-are-loadable
  (testing "Given the six Kaggle CSV files in data/kaggle
            When all datasets are loaded
            Then every file contributes rows to the unified model"
    (let [matches @data/all-matches
          sources (set (map :source matches))]
      (is (contains? sources "Brasileirao_Matches.csv"))
      (is (contains? sources "Brazilian_Cup_Matches.csv"))
      (is (contains? sources "Libertadores_Matches.csv"))
      (is (contains? sources "BR-Football-Dataset.csv"))
      (is (contains? sources "novo_campeonato_brasileiro.csv"))
      (is (> (count matches) 15000) "unified match count after deduplication")
      (is (= 18207 (count @data/all-players)) "all FIFA players load"))))

(deftest scenario-team-name-variations-normalize
  (testing "Given team names written with state suffixes, accents or full
            official names
            When each variant is canonicalized
            Then they all map to one canonical team"
    (is (= "Palmeiras" (data/canonical-team "Palmeiras-SP")))
    (is (= "Palmeiras" (data/canonical-team "Sociedade Esportiva Palmeiras")))
    (is (= "Flamengo" (data/canonical-team "Flamengo-RJ")))
    (is (= "Corinthians" (data/canonical-team "Sport Club Corinthians Paulista")))
    (is (= "São Paulo" (data/canonical-team "Sao Paulo-SP")))
    (is (= "São Paulo" (data/canonical-team "São Paulo")))
    (is (= "Atlético Mineiro" (data/canonical-team "Atletico Mineiro")))
    (is (= "Atlético Mineiro" (data/canonical-team "Atlético-MG")))
    (is (= "América-MG" (data/canonical-team "América - MG")))
    (is (= "Vasco da Gama" (data/canonical-team "Vasco"))))

  (testing "Given two clubs that share a base name
            When their names are canonicalized
            Then the state suffix keeps them distinct"
    (is (not= (data/canonical-team "América-MG")
              (data/canonical-team "América-RN")))
    (is (not= (data/canonical-team "Atlético-MG")
              (data/canonical-team "Atlético-GO")))))

(deftest scenario-team-matching-is-tolerant
  (testing "Given a user query without accents or with partial names
            When matched against canonical team names
            Then the match still succeeds"
    (is (data/team-matches? "Sao Paulo" "São Paulo"))
    (is (data/team-matches? "flamengo" "Flamengo"))
    (is (data/team-matches? "Gremio" "Grêmio"))
    (is (not (data/team-matches? "Flamengo" "Fluminense")))))

(deftest scenario-multiple-date-formats-are-parsed
  (testing "Given the three date formats used across the CSV files
            When each is parsed
            Then all normalize to ISO yyyy-MM-dd"
    (is (= "2012-05-19" (data/parse-date "2012-05-19 18:30:00")))
    (is (= "2023-09-24" (data/parse-date "2023-09-24")))
    (is (= "2003-03-29" (data/parse-date "29/03/2003")))
    (is (nil? (data/parse-date "NA")))))

(deftest scenario-utf8-text-is-preserved
  (testing "Given Brazilian Portuguese names with accents and cedillas
            When the data is loaded
            Then accented canonical names appear in the match data"
    (let [teams (into #{} (mapcat (juxt :home :away)) @data/all-matches)]
      (is (contains? teams "São Paulo"))
      (is (contains? teams "Grêmio"))
      (is (contains? teams "Avaí")))))

(deftest scenario-overlapping-files-are-deduplicated
  (testing "Given that three files contain Série A fixtures
            When matches are combined
            Then each season has its true number of fixtures"
    (let [serie-a (filter #(= "Brasileirão Série A" (:competition %))
                          @data/all-matches)
          by-season (frequencies (map :season serie-a))]
      (is (= 380 (by-season 2019)) "20 teams, double round-robin")
      (is (= 380 (by-season 2014)))
      (is (= 552 (by-season 2003)) "the 2003 championship had 24 teams"))))
