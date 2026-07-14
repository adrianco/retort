(ns brazilian-soccer.data-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [brazilian-soccer.data :as data])
  (:import [java.time LocalDate]))

(def ^:dynamic *db* nil)

(use-fixtures :once
  (fn [f]
    (binding [*db* (data/load-db "test/resources/kaggle")]
      (f))))

(deftest read-csv-test
  (testing "reads a CSV into a vector of maps keyed by header"
    (let [rows (data/read-csv "test/resources/kaggle/Brazilian_Cup_Matches.csv")]
      (is (= 1 (count rows)))
      (is (= "Athletico-PR" (get (first rows) "home_team"))))))

(deftest load-matches-test
  (testing "loads matches from every match file into a unified schema"
    (let [matches (:matches *db*)]
      ;; 3 brasileirao + 1 cup + 1 libertadores + 1 BR-dataset + 1 novo = 7
      (is (= 7 (count matches)))
      (testing "Brasileirão rows are normalized"
        (let [m (->> matches
                     (filter #(and (= "Brasileirão" (:competition %))
                                   (= 2019 (:season %))
                                   (= "Flamengo" (:home-team %))
                                   (= "Grêmio" (:away-team %))))
                     first)]
          (is (some? m))
          (is (= 5 (:home-goal m)))
          (is (= 0 (:away-goal m)))
          (is (= (LocalDate/of 2019 9 3) (:date m)))
          (is (= "20" (str (:round m))))))
      (testing "display team names have their state suffix stripped"
        (is (every? #(not (re-find #"-[A-Z]{2}$" (str (:home-team %))))
                    matches)))
      (testing "raw team names preserve the suffix for disambiguation"
        (let [m (->> matches
                     (filter #(and (= "Brasileirão" (:competition %))
                                   (= "Grêmio" (:away-team %))))
                     first)]
          (is (= "Flamengo-RJ" (:home-raw m)))
          (is (= "Grêmio-RS" (:away-raw m)))))
      (testing "every match carries a competition and source"
        (is (every? :competition matches))
        (is (every? :source matches)))
      (testing "competitions cover all files"
        (is (= #{"Brasileirão" "Copa do Brasil" "Libertadores"}
               (set (map :competition matches))))))))

(deftest select-best-source-test
  (testing "keeps only the richest source for each competition/season, avoiding
            the double-counting that overlapping files would otherwise cause"
    (let [mk (fn [src n] (repeat n {:competition "Brasileirão" :season 2019
                                    :source src :home-goal 1 :away-goal 0}))
          ;; two files cover 2019; novo has 3 rows, Brasileirao_Matches has 2
          matches (concat (mk "novo_campeonato_brasileiro.csv" 3)
                          (mk "Brasileirao_Matches.csv" 2))
          kept (data/select-best-source matches)]
      (is (= 3 (count kept)))
      (is (= #{"novo_campeonato_brasileiro.csv"} (set (map :source kept))))))
  (testing "on a tie the dedicated competition file wins over the broad dataset"
    (let [mk (fn [src n] (repeat n {:competition "Copa do Brasil" :season 2019
                                    :source src :home-goal 0 :away-goal 0}))
          matches (concat (mk "Brazilian_Cup_Matches.csv" 2)
                          (mk "BR-Football-Dataset.csv" 2))
          kept (data/select-best-source matches)]
      (is (= #{"Brazilian_Cup_Matches.csv"} (set (map :source kept))))))
  (testing "seasons present in only one source are kept untouched"
    (let [m {:competition "Brasileirão" :season 2008
             :source "novo_campeonato_brasileiro.csv" :home-goal 2 :away-goal 1}]
      (is (= 1 (count (data/select-best-source [m])))))))

(deftest load-players-test
  (testing "loads FIFA players into normalized maps"
    (let [players (:players *db*)]
      (is (= 3 (count players)))
      (let [neymar (first (filter #(= "Neymar Jr" (:name %)) players))]
        (is (= 92 (:overall neymar)))
        (is (= "Brazil" (:nationality neymar)))
        (is (= "Paris Saint-Germain" (:club neymar)))
        (is (= "LW" (:position neymar)))
        (is (= 27 (:age neymar)))))))
