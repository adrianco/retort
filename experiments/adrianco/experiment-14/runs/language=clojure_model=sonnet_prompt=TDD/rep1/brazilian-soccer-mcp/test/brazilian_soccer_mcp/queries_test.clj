(ns brazilian-soccer-mcp.queries-test
  (:require [clojure.test :refer :all]
            [brazilian-soccer-mcp.queries :as q]
            [brazilian-soccer-mcp.data :as data]))

(def sample-matches
  [{:home-team "Flamengo" :away-team "Palmeiras" :home-goal 2 :away-goal 1
    :season 2023 :competition "brasileirao" :round 22
    :date (java.time.LocalDate/of 2023 9 3)}
   {:home-team "Fluminense" :away-team "Flamengo" :home-goal 1 :away-goal 0
    :season 2023 :competition "brasileirao" :round 8
    :date (java.time.LocalDate/of 2023 5 28)}
   {:home-team "Palmeiras" :away-team "Corinthians" :home-goal 3 :away-goal 1
    :season 2022 :competition "brasileirao" :round 10
    :date (java.time.LocalDate/of 2022 6 15)}
   {:home-team "Flamengo" :away-team "Corinthians" :home-goal 0 :away-goal 0
    :season 2022 :competition "brasileirao" :round 5
    :date (java.time.LocalDate/of 2022 4 10)}
   {:home-team "Santos" :away-team "Flamengo" :home-goal 1 :away-goal 3
    :season 2023 :competition "copa-do-brasil" :round "semi-final"
    :date (java.time.LocalDate/of 2023 8 10)}])

(deftest find-matches-by-team-test
  (testing "finds matches where team played as home"
    (let [results (q/find-matches sample-matches {:team "Flamengo" :role :home})]
      (is (= 2 (count results)))
      (is (every? #(= "Flamengo" (:home-team %)) results))))

  (testing "finds matches where team played as away"
    (let [results (q/find-matches sample-matches {:team "Flamengo" :role :away})]
      (is (= 2 (count results)))
      (is (every? #(= "Flamengo" (:away-team %)) results))))

  (testing "finds all matches with team (home or away)"
    (let [results (q/find-matches sample-matches {:team "Flamengo"})]
      (is (= 4 (count results)))))

  (testing "finds matches for a team not present"
    (let [results (q/find-matches sample-matches {:team "Grêmio"})]
      (is (empty? results)))))

(deftest find-matches-by-season-test
  (testing "filters matches by season"
    (let [results (q/find-matches sample-matches {:season 2023})]
      (is (= 3 (count results)))
      (is (every? #(= 2023 (:season %)) results))))

  (testing "returns empty for unknown season"
    (let [results (q/find-matches sample-matches {:season 2019})]
      (is (empty? results)))))

(deftest find-matches-by-competition-test
  (testing "filters by competition"
    (let [results (q/find-matches sample-matches {:competition "brasileirao"})]
      (is (= 4 (count results)))))

  (testing "filters copa-do-brasil"
    (let [results (q/find-matches sample-matches {:competition "copa-do-brasil"})]
      (is (= 1 (count results))))))

(deftest find-matches-combined-filters-test
  (testing "filters by team AND season"
    (let [results (q/find-matches sample-matches {:team "Flamengo" :season 2023})]
      (is (= 3 (count results)))))

  (testing "filters by team AND competition"
    (let [results (q/find-matches sample-matches {:team "Flamengo" :competition "brasileirao"})]
      (is (= 3 (count results)))))

  (testing "head-to-head: finds matches between two specific teams"
    (let [results (q/find-matches sample-matches {:team1 "Flamengo" :team2 "Palmeiras"})]
      (is (= 1 (count results))))))

(deftest calculate-team-stats-test
  (testing "calculates win/draw/loss from matches"
    (let [stats (q/calculate-team-stats sample-matches "Flamengo")]
      (is (= 4 (:matches stats)))
      (is (= 2 (:wins stats)))
      (is (= 1 (:draws stats)))
      (is (= 1 (:losses stats)))
      (is (= 5 (:goals-for stats)))
      (is (= 3 (:goals-against stats)))))

  (testing "stats for team with no matches"
    (let [stats (q/calculate-team-stats sample-matches "Grêmio")]
      (is (= 0 (:matches stats)))
      (is (= 0 (:wins stats))))))

(deftest calculate-standings-test
  (testing "calculates standings sorted by points"
    (let [standings (q/calculate-standings sample-matches)]
      (is (seq standings))
      (let [first-team (first standings)]
        (is (contains? first-team :team))
        (is (contains? first-team :points))
        (is (contains? first-team :wins))
        (is (contains? first-team :draws))
        (is (contains? first-team :losses)))))

  (testing "standings are sorted by points descending"
    (let [standings (q/calculate-standings sample-matches)
          points (map :points standings)]
      (is (= points (sort > points))))))

(deftest biggest-wins-test
  (testing "returns matches sorted by goal difference descending"
    (let [wins (q/biggest-wins sample-matches 3)]
      (is (<= (count wins) 3))
      (let [diffs (map #(Math/abs (- (:home-goal %) (:away-goal %))) wins)]
        (is (= diffs (sort > diffs))))))

  (testing "returns up to n results"
    (let [wins (q/biggest-wins sample-matches 2)]
      (is (= 2 (count wins))))))

(deftest head-to-head-stats-test
  (testing "calculates head-to-head record"
    (let [stats (q/head-to-head-stats sample-matches "Flamengo" "Corinthians")]
      (is (= 1 (:total stats)))
      (is (= 0 (:team1-wins stats)))
      (is (= 1 (:draws stats)))
      (is (= 0 (:team2-wins stats))))))
