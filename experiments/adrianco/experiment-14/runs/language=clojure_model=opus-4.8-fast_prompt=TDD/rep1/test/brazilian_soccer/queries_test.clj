(ns brazilian-soccer.queries-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.queries :as q]))

(def ^:dynamic *db* nil)

(use-fixtures :once
  (fn [f]
    (binding [*db* (data/load-db "test/resources/kaggle")]
      (f))))

(deftest find-matches-by-team-test
  (testing "finds every match a team played, home or away, across files"
    (is (= 5 (count (q/find-matches *db* {:team "Flamengo"})))))
  (testing "matches team names regardless of state suffix in the query"
    (is (= 5 (count (q/find-matches *db* {:team "Flamengo-RJ"})))))
  (testing "filters by competition and season"
    (is (= 3 (count (q/find-matches *db* {:team "Flamengo"
                                          :competition "Brasileirão"
                                          :season 2019})))))
  (testing "filters to home-only and away-only"
    (is (= 2 (count (q/find-matches *db* {:team "Flamengo" :venue :home
                                          :competition "Brasileirão"}))))
    (is (= 1 (count (q/find-matches *db* {:team "Flamengo" :venue :away
                                          :competition "Brasileirão"}))))))

(deftest find-matches-between-teams-test
  (testing "filters to matches between two specific teams"
    (let [ms (q/find-matches *db* {:team "Flamengo" :opponent "Santos"})]
      (is (= 2 (count ms)))
      (is (every? #(or (= "Santos" (:home-team %))
                       (= "Santos" (:away-team %)))
                  ms)))))

(deftest find-matches-by-date-range-test
  (testing "filters by inclusive date range"
    (let [ms (q/find-matches *db* {:team "Flamengo"
                                   :from (java.time.LocalDate/of 2019 9 1)
                                   :to (java.time.LocalDate/of 2019 12 31)})]
      ;; Brasileirão R20 (2019-09-03) and Libertadores final (2019-11-23)
      (is (= 2 (count ms))))))

(deftest head-to-head-test
  (testing "tallies wins, draws and losses between two teams"
    (let [h (q/head-to-head *db* "Flamengo" "Santos")]
      (is (= 2 (:total h)))
      (is (= 1 (:team-a-wins h)))
      (is (= 0 (:team-b-wins h)))
      (is (= 1 (:draws h)))
      (is (= 3 (:team-a-goals h)))
      (is (= 1 (:team-b-goals h))))))

(deftest team-record-test
  (testing "computes W/D/L, goals and points for a team in a competition+season"
    (let [r (q/team-record *db* "Flamengo" {:competition "Brasileirão" :season 2019})]
      (is (= 3 (:matches r)))
      (is (= 2 (:wins r)))
      (is (= 1 (:draws r)))
      (is (= 0 (:losses r)))
      (is (= 8 (:goals-for r)))
      (is (= 1 (:goals-against r)))
      (is (= 7 (:points r)))
      (is (= 66.7 (:win-rate r))))))

(deftest standings-test
  (testing "builds a points table from match results"
    (let [table (q/standings *db* "Brasileirão" 2019)]
      (is (= ["Flamengo" "Santos" "Grêmio"] (map :team table)))
      (let [fla (first table)]
        (is (= 7 (:points fla)))
        (is (= 3 (:played fla)))
        (is (= 2 (:wins fla)))
        (is (= 8 (:goals-for fla)))
        (is (= 1 (:goals-against fla)))
        (is (= 7 (:goal-difference fla))))
      (is (= 1 (:points (second table)))))))

(defn- row-for [table name-substr]
  (first (filter #(clojure.string/includes? (:team %) name-substr) table)))

(deftest standings-merges-accent-variants-test
  (testing "team-name spelling variants collapse into one row, accented name shown"
    (let [db {:matches [{:competition "X" :season 1 :date nil :round nil
                         :home-raw "São Paulo" :home-team "São Paulo" :away-team "Santos"
                         :home-goal 1 :away-goal 0}
                        {:competition "X" :season 1 :date nil :round nil
                         :home-raw "Sao Paulo" :home-team "Sao Paulo" :away-team "Corinthians"
                         :home-goal 2 :away-goal 0}]}
          table (q/standings db "X" 1)
          sp (first (filter #(= 2 (:played %)) table))]
      (is (some? sp))
      (is (= "São Paulo" (:team sp)))
      (is (= 6 (:points sp))))))

(deftest standings-suffix-disambiguation-test
  (testing "a bare name and its single suffixed variant collapse to one club"
    (let [db {:matches [{:competition "X" :season 1 :date nil
                         :home-raw "Flamengo" :away-raw "Santos"
                         :home-goal 1 :away-goal 0}
                        {:competition "X" :season 1 :date nil
                         :home-raw "Flamengo-RJ" :away-raw "Santos"
                         :home-goal 2 :away-goal 0}]}
          table (q/standings db "X" 1)
          flamengos (filter #(= "Flamengo" (:team %)) table)]
      (is (= 1 (count flamengos)) "the two Flamengo spellings merge to one row")
      (is (= 2 (:played (first flamengos))))))
  (testing "two different states of the same base name stay separate"
    (let [db {:matches [{:competition "X" :season 1 :date nil
                         :home-raw "Atlético-MG" :away-raw "Santos"
                         :home-goal 1 :away-goal 0}
                        {:competition "X" :season 1 :date nil
                         :home-raw "Atlético-GO" :away-raw "Santos"
                         :home-goal 2 :away-goal 0}]}
          table (q/standings db "X" 1)
          atleticos (filter #(clojure.string/starts-with? (:team %) "Atlético") table)]
      (is (= 2 (count atleticos)) "Atlético-MG and Atlético-GO are distinct")
      (is (= #{"Atlético-MG" "Atlético-GO"} (set (map :team atleticos)))))))

(deftest search-players-test
  (testing "filters by nationality and sorts by overall rating descending"
    (let [ps (q/search-players *db* {:nationality "Brazil"})]
      (is (= ["Neymar Jr" "Gabriel Barbosa"] (map :name ps)))))
  (testing "fuzzy name search is accent and case insensitive"
    (is (= ["Gabriel Barbosa"]
           (map :name (q/search-players *db* {:name "gabriel"})))))
  (testing "filters by club"
    (is (= ["Gabriel Barbosa"]
           (map :name (q/search-players *db* {:club "Flamengo"})))))
  (testing "respects a result limit"
    (is (= 1 (count (q/search-players *db* {:nationality "Brazil" :limit 1}))))))

(deftest statistics-test
  (testing "average goals per match"
    (is (= 3.0 (q/avg-goals-per-match (:matches *db*)))))
  (testing "home win rate as a percentage"
    (is (= 71.4 (q/home-win-rate (:matches *db*)))))
  (testing "biggest wins ranked by goal margin"
    (let [top (first (q/biggest-wins (:matches *db*) 3))]
      (is (= "Flamengo" (:home-team top)))
      (is (= "Grêmio" (:away-team top)))
      (is (= 5 (:margin top))))))
