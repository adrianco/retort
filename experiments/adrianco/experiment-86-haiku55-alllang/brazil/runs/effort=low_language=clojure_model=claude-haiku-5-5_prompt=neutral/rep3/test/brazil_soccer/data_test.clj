(ns brazil-soccer.data-test
  (:require [clojure.test :refer [deftest is testing]]
            [brazil-soccer.data :as data]
            [brazil-soccer.queries :as q]
            [brazil-soccer.support :refer [real-db]])
  (:import [java.time LocalDate]))

(deftest dates_in_every_source_format_parse
  (testing "Given ISO dates with and without a time, then they parse"
    (is (= (LocalDate/of 2023 9 24) (data/parse-date "2023-09-24")))
    (is (= (LocalDate/of 2012 5 19) (data/parse-date "2012-05-19 18:30:00"))))
  (testing "Given a Brazilian DD/MM/YYYY date, then it parses"
    (is (= (LocalDate/of 2003 3 29) (data/parse-date "29/03/2003"))))
  (testing "Given something that is not a date, then nil"
    (is (nil? (data/parse-date "")))
    (is (nil? (data/parse-date "not a date")))))

(deftest all_six_csv_files_are_loaded
  (testing "Given the Kaggle data directory, when loaded, then every match file contributes"
    (let [competitions (set (map :competition (:matches @real-db)))]
      (is (= #{:serie-a :serie-b :serie-c :copa-do-brasil :libertadores} competitions))))
  (testing "Given the FIFA file, when loaded, then all 18,207 players are present"
    (is (= 18207 (count (:players @real-db))))))

(deftest duplicate_fixtures_across_files_are_counted_once
  (testing "Given Flamengo's 2019 Brasileirão, which appears in two source files, then it has 38 matches"
    (let [ms (filter #(and (= :serie-a (:competition %)) (= 2019 (:season %))
                           (or (= "flamengo" (:home %)) (= "flamengo" (:away %))))
                     (:matches @real-db))]
      (is (= 38 (count ms))))))

(deftest a_known_match_is_queryable
  (testing "Given the Brasileirão data, then the 2019 Flamengo result is present with the right score"
    (let [ms (q/filter-matches @real-db {:team "Flamengo" :opponent "Cruzeiro"
                                         :competition "Serie A" :season 2019})]
      (is (= 2 (count ms)))
      (is (some #(and (= 3 (:home-goals %)) (= 1 (:away-goals %))) ms)))))
