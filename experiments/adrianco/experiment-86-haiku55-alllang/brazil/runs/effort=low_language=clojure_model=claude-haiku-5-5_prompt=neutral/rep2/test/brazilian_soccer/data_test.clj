(ns brazilian-soccer.data-test
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.names :as names]
            [clojure.test :refer [deftest is testing]]))

(deftest parse-date-accepts-iso-and-brazilian-formats
  (is (= "2012-05-19" (data/parse-date "2012-05-19 18:30:00")))
  (is (= "2023-09-24" (data/parse-date "2023-09-24")))
  (is (= "2003-03-29" (data/parse-date "29/03/2003")))
  (is (nil? (data/parse-date "not a date"))))

(deftest parse-whole-reads-integers-and-float-strings
  (is (= 2 (data/parse-whole "2")))
  (is (= 1 (data/parse-whole "1.0")))
  (is (= 2 (data/parse-whole "2.0")))
  (is (nil? (data/parse-whole "")))
  (is (nil? (data/parse-whole "x"))))

;; Smoke tests against the real Kaggle files shipped in data/kaggle.
(def ^:private loaded (delay (data/load-all "data/kaggle")))

(deftest all-match-files-contribute
  (let [sources (set (map :source (:matches @loaded)))]
    (is (= #{"Brasileirao_Matches.csv" "Brazilian_Cup_Matches.csv" "Libertadores_Matches.csv"
             "novo_campeonato_brasileiro.csv" "BR-Football-Dataset.csv"}
           sources))))

(deftest matches-are-complete-and-consistent
  (doseq [m (:matches @loaded)]
    (is (re-matches #"\d{4}-\d{2}-\d{2}" (:date m)) (str "bad date " (:date m)))
    (is (= (:season m) (parse-long (subs (:date m) 0 4))))
    (is (number? (:home-goals m)))
    (is (number? (:away-goals m)))))

(deftest no-duplicate-matches-after-merging
  (let [ks (map (juxt :date :home-key :away-key :home-goals :away-goals) (:matches @loaded))]
    (is (= (count ks) (count (set ks))))))

(deftest real-data-contains-named-fixtures
  (is (seq (filter #(and (= "flamengo" (:home-key %)) (= "fluminense" (:away-key %)))
                   (:matches @loaded))))
  (is (seq (filter #(= "libertadores" (names/competition-key (:competition %))) (:matches @loaded))))
  (is (seq (filter #(= "copa do brasil" (names/competition-key (:competition %))) (:matches @loaded)))))

(deftest real-2019-season-has-one-copy-of-each-match
  (let [s19 (filter #(and (= 2019 (:season %)) (= "brasileirao" (names/competition-key (:competition %))))
                    (:matches @loaded))]
    (is (= 380 (count s19)))
    (is (every? #(= 38 %) (vals (frequencies (mapcat (juxt :home-key :away-key) s19)))))))

(deftest real-player-data-loads
  (let [ps (:players @loaded)]
    (is (> (count ps) 18000))
    (is (some #(= "Brazil" (:nationality %)) ps))
    (is (every? :name ps))))
