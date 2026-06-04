;; =============================================================================
;; brazilian-soccer.knowledge-graph-test
;; -----------------------------------------------------------------------------
;; BDD coverage for graph construction, indexing and cross-source de-duplication.
;; =============================================================================
(ns brazilian-soccer.knowledge-graph-test
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.knowledge-graph :as kg]
            [brazilian-soccer.test-helper :as h]))

(deftest build-graph-test
  (testing "Given loaded data, When the graph is built, Then nodes/indexes exist"
    (let [g (h/graph)]
      (is (seq (:matches g)))
      (is (seq (:players g)))
      (is (map? (:teams g)))
      (is (map? (:competitions g)))
      (is (contains? (:by-team g) "flamengo")))))

(deftest dedup-test
  (testing "Given the same fixture in two sources, When de-duplicated, Then one edge remains with merged sources"
    (let [a {:competition "Brasileirão Série A" :season 2015
             :home "Palmeiras" :away "Santos" :home-key "palmeiras" :away-key "santos"
             :date "2015-09-13" :home-goals 6 :away-goals 0 :source :brasileirao :stats {}}
          b (assoc a :source :br-football :stats {:home-shots 18})
          out (kg/dedup-matches [a b])]
      (is (= 1 (count out)))
      (is (= #{:brasileirao :br-football} (:sources (first out))))
      (is (= 18 (get-in (first out) [:stats :home-shots])) "kept the richer record's stats"))))

(deftest dedup-keeps-distinct-test
  (testing "Given two genuinely different fixtures, When de-duplicated, Then both remain"
    (let [a {:competition "Copa do Brasil" :season 2019
             :home "Flamengo" :away "Athletico-PR" :home-key "flamengo" :away-key "athletico-pr"
             :date "2019-09-18" :home-goals 1 :away-goals 0 :source :cup :stats {}}
          b (assoc a :date "2019-09-25" :home "Athletico-PR" :away "Flamengo"
                   :home-key "athletico-pr" :away-key "flamengo" :home-goals 1 :away-goals 0)]
      (is (= 2 (count (kg/dedup-matches [a b])))))))

(deftest team-index-test
  (testing "Given a famous club, Then it appears in the team index with competitions"
    (let [fla (get-in (h/graph) [:teams "flamengo"])]
      (is (some? fla))
      (is (= "Flamengo" (:name fla)))
      (is (contains? (:competitions fla) "Brasileirão Série A")))))
