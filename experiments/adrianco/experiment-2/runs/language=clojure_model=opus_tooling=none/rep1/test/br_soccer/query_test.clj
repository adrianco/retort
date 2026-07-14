(ns br-soccer.query-test
  (:require [clojure.test :refer [deftest is testing]]
            [br-soccer.query :as q]))

(deftest matches-by-team-test
  (let [ms (q/matches-by-team "Flamengo")]
    (is (pos? (count ms)))
    (is (every? #(or (clojure.string/includes?
                      (clojure.string/lower-case (:home %)) "flamengo")
                     (clojure.string/includes?
                      (clojure.string/lower-case (:away %)) "flamengo"))
                ms))))

(deftest matches-between-test
  (let [ms (q/matches-between "Flamengo" "Fluminense")]
    (is (pos? (count ms)) "expected Fla-Flu derby matches in dataset")))

(deftest team-stats-test
  (let [s (q/team-stats "Palmeiras" {:season 2019})]
    (is (= "Palmeiras" (:team s)))
    (is (pos? (:matches s)))
    (is (= (:matches s) (+ (:win s) (:draw s) (:loss s))))
    (is (>= (:goals-for s) 0))))

(deftest head-to-head-test
  (let [r (q/head-to-head "Flamengo" "Fluminense")]
    (is (pos? (:matches r)))
    (is (= (:matches r)
           (+ (:team-a-wins r) (:team-b-wins r) (:draws r))))))

(deftest standings-test
  (let [table (q/standings "Brasileirão" 2019)]
    (is (pos? (count table)))
    ;; Higher-ranked team should have >= points than next
    (is (apply >= (map :points table)))))

(deftest avg-goals-test
  (let [avg (q/avg-goals-per-match)]
    (is (pos? avg))
    (is (< avg 10.0))))

(deftest biggest-wins-test
  (let [bw (q/biggest-wins 5)]
    (is (= 5 (count bw)))
    (is (every? #(and (:home-goal %) (:away-goal %)) bw))))

(deftest players-search-test
  (testing "search by name"
    (let [ps (q/players-by-name "Neymar")]
      (is (pos? (count ps)))))
  (testing "brazilian players"
    (let [ps (take 5 (q/players-by-nationality "Brazil"))]
      (is (= 5 (count ps)))
      (is (every? #(= "Brazil" (:nationality %)) ps))))
  (testing "top brazilian players"
    (let [ps (q/top-players 3 {:nationality "Brazil"})]
      (is (= 3 (count ps)))
      (is (apply >= (map :overall ps))))))
