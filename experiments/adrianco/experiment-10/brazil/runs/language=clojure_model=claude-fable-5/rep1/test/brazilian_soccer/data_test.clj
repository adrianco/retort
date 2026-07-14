(ns brazilian-soccer.data-test
  "CONTEXT
  =======
  BDD (Given/When/Then) tests for the data layer: CSV loading, team-name
  normalization, date parsing and cross-file de-duplication.

  Expected counts come straight from the files in data/kaggle/ (rows minus
  header): 4180 + 1337 + 1255 + 6886 + 10296 matches and 18207 players."
  (:require [clojure.test :refer [deftest is testing]]
            [brazilian-soccer.data :as data]))

(deftest loading-all-csv-files
  (testing "Given the six Kaggle CSV files in data/kaggle/
            When the database is loaded
            Then every file contributes its full row count"
    (let [{:keys [file-counts matches players]} (data/db)]
      (is (= 4180 (:brasileirao file-counts)) "Brasileirao_Matches.csv")
      (is (= 1337 (:cup file-counts)) "Brazilian_Cup_Matches.csv")
      (is (= 1255 (:libertadores file-counts)) "Libertadores_Matches.csv")
      (is (= 6886 (:historical file-counts)) "novo_campeonato_brasileiro.csv")
      (is (= 10296 (:extended file-counts)) "BR-Football-Dataset.csv")
      (is (= 18207 (:players file-counts)) "fifa_data.csv")
      (is (= 18207 (count players)))
      (testing "And overlapping files are de-duplicated into fewer unique matches"
        (is (< (count matches) 23954))
        (is (> (count matches) 15000))))))

(deftest date-parsing
  (testing "Given the three date formats used by the datasets
            When they are parsed
            Then each yields the right LocalDate, and junk yields nil"
    (is (= "2023-09-24" (str (data/parse-date "2023-09-24"))))
    (is (= "2012-05-19" (str (data/parse-date "2012-05-19 18:30:00"))))
    (is (= "2003-03-29" (str (data/parse-date "29/03/2003"))))
    (is (nil? (data/parse-date "NA")))
    (is (nil? (data/parse-date nil)))
    (is (nil? (data/parse-date "")))))

(deftest numeric-parsing
  (testing "Given goal values as ints, floats and NA
            When parsed
            Then ints and floats become longs and NA becomes nil"
    (is (= 2 (data/parse-long* "2")))
    (is (= 3 (data/parse-long* "3.0")))
    (is (nil? (data/parse-long* "NA")))
    (is (nil? (data/parse-long* "-")))
    (is (nil? (data/parse-long* nil)))))

(deftest team-name-normalization
  (testing "Given the naming conventions of the different files
            When raw team names are canonicalized
            Then variants of the same club share one id"
    (is (= (data/canonical-team "Palmeiras-SP") (data/canonical-team "Palmeiras")))
    (is (= (data/canonical-team "São Paulo") (data/canonical-team "Sao Paulo-SP")))
    (is (= (data/canonical-team "Grêmio") (data/canonical-team "Gremio-RS")))
    (is (= (data/canonical-team "Flamengo - RJ") (data/canonical-team "Flamengo")))
    (is (= (data/canonical-team "Vasco da Gama-RJ") (data/canonical-team "Vasco")))
    (is (= (data/canonical-team "Sport Club Corinthians Paulista")
           (data/canonical-team "Corinthians-SP")))
    (is (= (data/canonical-team "Atletico Mineiro") (data/canonical-team "Atlético - MG")))
    (is (= (data/canonical-team "Athletico Paranaense") (data/canonical-team "Atletico-PR")))
    (is (= (data/canonical-team "EC Bahia") (data/canonical-team "Bahia - BA")))
    (is (= (data/canonical-team "Fortaleza EC") (data/canonical-team "Fortaleza - CE"))))
  (testing "And clubs that differ only by state stay distinct"
    (is (not= (data/canonical-team "Atlético - MG") (data/canonical-team "Atlético - GO")))
    (is (not= (data/canonical-team "América - MG") (data/canonical-team "América - RN")))
    (is (not= (data/canonical-team "Botafogo - RJ") (data/canonical-team "Botafogo - PB"))))
  (testing "And foreign clubs keep their country qualifier"
    (is (not= (data/canonical-team "Nacional (URU)") (data/canonical-team "Nacional")))))

(deftest utf8-handling
  (testing "Given accented Brazilian Portuguese team names
            When the data is loaded
            Then accented and unaccented spellings reach the same club"
    (let [matches (:matches (data/db))
          gremio (data/canonical-team "Grêmio")]
      (is (pos? (count (filter #(or (= gremio (:home %)) (= gremio (:away %))) matches)))
          "Grêmio matches are findable via the accented name"))))

(deftest deduplication
  (testing "Given Serie A seasons that appear in up to three files
            When matches are de-duplicated
            Then each double-round-robin season has exactly its real matches"
    (let [matches (:matches (data/db))
          serie-a (fn [yr] (filter #(and (= "Brasileirão Série A" (:competition %))
                                         (= yr (:season %)))
                                   matches))]
      ;; 20-team double round robin = 380 matches
      (doseq [yr [2012 2016 2019 2020 2021 2022]]
        (is (= 380 (count (serie-a yr))) (str "season " yr)))
      ;; 24-team era
      (is (= 552 (count (serie-a 2003)))))))
