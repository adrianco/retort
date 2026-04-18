(ns brazilian-soccer-mcp.tools-test
  (:require [clojure.test :refer [deftest is testing use-fixtures]]
            [clojure.string :as str]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.tools :as tools]))

(use-fixtures :once (fn [f] (data/load-all!) (f)))

;; ---------------------------------------------------------------------------
;; Match queries
;; ---------------------------------------------------------------------------

(deftest find-matches-by-teams-test
  (testing "returns matches between two teams"
    (let [result (tools/find-matches-by-teams {:team-a "Flamengo" :team-b "Fluminense"})]
      (is (map? result))
      (is (> (:total-found result) 0))
      (is (seq (:matches result)))
      (is (map? (:head-to-head result)))))
  (testing "head-to-head sums are consistent"
    (let [result (tools/find-matches-by-teams {:team-a "Palmeiras" :team-b "Santos"})
          h2h    (:head-to-head result)
          total  (:total-found result)]
      (is (= total (+ (:a-wins h2h) (:b-wins h2h) (:draws h2h))))))
  (testing "returns empty for non-existent teams"
    (let [result (tools/find-matches-by-teams {:team-a "NonExistentTeamXYZ123" :team-b "AnotherFakeTeam"})]
      (is (= 0 (:total-found result))))))

(deftest find-matches-by-team-test
  (testing "finds Flamengo matches"
    (let [result (tools/find-matches-by-team {:team "Flamengo"})]
      (is (> (:total-found result) 10))))
  (testing "season filter works"
    (let [result (tools/find-matches-by-team {:team "Palmeiras" :season 2023})]
      (is (>= (:total-found result) 0))))
  (testing "competition filter works"
    (let [result (tools/find-matches-by-team {:team "Flamengo" :competition "Brasileirao"})]
      (is (>= (:total-found result) 0))))
  (testing "limit is respected"
    (let [result (tools/find-matches-by-team {:team "Flamengo" :limit 5})]
      (is (<= (count (:matches result)) 5)))))

(deftest find-matches-by-date-range-test
  (testing "finds matches in range"
    (let [result (tools/find-matches-by-date-range {:from-date "2023-01-01" :to-date "2023-12-31"})]
      (is (> (:total-found result) 0))))
  (testing "empty range returns empty"
    (let [result (tools/find-matches-by-date-range {:from-date "1900-01-01" :to-date "1900-12-31"})]
      (is (= 0 (:total-found result))))))

(deftest find-matches-by-season-test
  (testing "returns matches for 2019"
    (let [result (tools/find-matches-by-season {:season 2019})]
      (is (> (:total-found result) 0))))
  (testing "2019 Brasileirao has expected matches"
    (let [result (tools/find-matches-by-season {:season 2019 :competition "Brasileirao" :limit 500})]
      (is (>= (:total-found result) 380)))))

;; ---------------------------------------------------------------------------
;; Team queries
;; ---------------------------------------------------------------------------

(deftest get-team-stats-test
  (testing "returns stats for Flamengo 2019"
    (let [result (tools/get-team-stats {:team "Flamengo" :season 2019 :competition "Brasileirao"})]
      (is (map? (:overall result)))
      (is (> (get-in result [:overall :matches]) 0))
      (is (>= (get-in result [:overall :wins]) 0))
      (is (some? (get-in result [:overall :points])))))
  (testing "wins + draws + losses = matches"
    (let [result (tools/get-team-stats {:team "Palmeiras"})
          o      (:overall result)]
      (is (= (:matches o) (+ (:wins o) (:draws o) (:losses o)))))))

(deftest compare-teams-head-to-head-test
  (testing "returns comparison map"
    (let [result (tools/compare-teams-head-to-head {:team-a "Corinthians" :team-b "Palmeiras"})]
      (is (pos? (:total-matches result)))
      (is (map? (:head-to-head result))))))

;; ---------------------------------------------------------------------------
;; Player queries
;; ---------------------------------------------------------------------------

(deftest find-players-test
  (testing "finds Neymar by name"
    (let [result (tools/find-players {:name "Neymar"})]
      (is (pos? (:total-found result)))
      (is (seq (:players result)))))
  (testing "finds Brazilian players"
    (let [result (tools/find-players {:nationality "Brazil" :limit 10})]
      (is (= 10 (count (:players result))))))
  (testing "finds players at a club"
    (let [result (tools/find-players {:club "Barcelona"})]
      (is (pos? (:total-found result)))))
  (testing "no results for gibberish"
    (let [result (tools/find-players {:name "XYZnonexistent99"})]
      (is (zero? (:total-found result))))))

(deftest find-brazilian-players-test
  (testing "returns multiple Brazilian players"
    (let [result (tools/find-brazilian-players {:limit 20})]
      (is (= 20 (count (:players result)))))))

(deftest top-players-at-club-test
  (testing "returns top players sorted by overall"
    (let [result (tools/top-players-at-club {:club "Barcelona" :limit 5})]
      (is (<= (count (:players result)) 5)))))

;; ---------------------------------------------------------------------------
;; Competition / standings
;; ---------------------------------------------------------------------------

(deftest calculate-standings-test
  (testing "calculates 2019 Brasileirao standings"
    (let [result (tools/calculate-standings {:season 2019 :competition "Brasileirao"})]
      (is (seq (:standings result)))
      (is (> (count (:standings result)) 10))
      ;; Flamengo should be near the top in 2019
      (is (str/includes? (first (:standings result)) "Flamengo"))))
  (testing "standings are non-empty for valid seasons"
    (let [result (tools/calculate-standings {:season 2022 :competition "Brasileirao"})]
      (is (>= (count (:standings result)) 10)))))

(deftest get-season-winner-test
  (testing "2019 Brasileirao winner is Flamengo"
    (let [result (tools/get-season-winner {:season 2019 :competition "Brasileirao"})]
      (is (str/includes? (str (:winner result)) "Flamengo")))))

;; ---------------------------------------------------------------------------
;; Statistical analysis
;; ---------------------------------------------------------------------------

(deftest goals-per-match-avg-test
  (testing "returns positive average"
    (let [result (tools/goals-per-match-avg {:competition "Brasileirao" :season 2022})]
      (is (pos? (:total-matches result)))
      (is (some? (:avg-goals-per-match result))))))

(deftest biggest-wins-test
  (testing "returns top wins sorted by margin"
    (let [result (tools/biggest-wins {:limit 5})]
      (is (= 5 (count (:matches result)))))))

(deftest home-vs-away-stats-test
  (testing "returns valid percentages"
    (let [result (tools/home-vs-away-stats {:competition "Brasileirao Serie A"})]
      (is (pos? (:total-matches result)))
      (is (some? (:home-win-pct result))))))

(deftest best-home-records-test
  (testing "returns teams"
    (let [result (tools/best-home-records {:competition "Brasileirao" :limit 5})]
      (is (seq (:teams result))))))

(deftest top-scoring-teams-test
  (testing "returns sorted team list"
    (let [result (tools/top-scoring-teams {:competition "Brasileirao" :limit 5})]
      (is (= 5 (count (:teams result)))))))

