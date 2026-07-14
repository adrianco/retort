;; =============================================================================
;; brazilian-soccer.queries-test
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   BDD (Given/When/Then) tests for the query/aggregation layer of the
;;   Brazilian Soccer MCP server. Uses the hand-verifiable fixture dataset in
;;   brazilian-soccer.fixtures so every expected count is exact, plus a few
;;   smoke checks against the real datasets.
;; =============================================================================
(ns brazilian-soccer.queries-test
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.queries :as q]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.fixtures :as fx]))

(def ms fx/matches)
(def ps fx/players)

(deftest search-matches-by-team
  (testing "Given matches, When searching by team, Then all their games across competitions return"
    (is (= 7 (count (q/search-matches ms {:team "Flamengo"})))) ; 5 Brasileirão + Copa + Libertadores
    (is (= 4 (count (q/search-matches ms {:team "Santos"})))))

  (testing "When filtering by season, Then only that season returns"
    (is (= 6 (count (q/search-matches ms {:competition "Brasileirão" :season 2019})))))

  (testing "When filtering home only, Then away games are excluded"
    (is (= 2 (count (q/search-matches ms {:home "Flamengo" :season 2019
                                          :competition "Brasileirão"})))))

  (testing "When filtering by date range, Then only matches in range return"
    ;; May 2019: Flamengo 3-0 Palmeiras (1st) and the Copa do Brasil final (15th)
    (is (= 2 (count (q/search-matches ms {:from "2019-05-01" :to "2019-05-31"})))))

  (testing "Then results are sorted most-recent first"
    (let [dates (map :date (q/search-matches ms {:team "Flamengo"}))]
      (is (= dates (reverse (sort dates)))))))

(deftest head-to-head-record
  (testing "Given two rivals, When computing H2H, Then record is exact"
    (let [{:keys [record]} (q/head-to-head ms "Flamengo" "Palmeiras")]
      (is (= 3 (:total record)))
      (is (= 1 (:a-wins record)))
      (is (= 1 (:b-wins record)))
      (is (= 1 (:draws record)))
      (is (= 4 (:a-goals record)))
      (is (= 3 (:b-goals record))))))

(deftest team-statistics
  (testing "Given a team/season, When computing stats, Then W/D/L and goals match"
    (let [s (q/team-stats ms "Flamengo" {:season 2019 :competition "Brasileirão"})]
      (is (= 4 (:matches s)))
      (is (= 3 (:wins s)))
      (is (= 1 (:draws s)))
      (is (= 0 (:losses s)))
      (is (= 11 (:goals-for s)))
      (is (= 1 (:goals-against s)))
      (is (= 10 (:points s)))
      (is (= 75.0 (:win-rate s)))))

  (testing "When venue is home, Then only home games are counted"
    (let [s (q/team-stats ms "Flamengo" {:season 2019 :competition "Brasileirão"
                                         :venue :home})]
      (is (= 2 (:matches s)))
      (is (= 2 (:wins s)))
      (is (= 8 (:goals-for s))))))

(deftest league-standings
  (testing "Given a season's matches, When computing standings, Then order/points are exact"
    (let [table (q/standings ms "Brasileirão Série A" 2019)
          champ (first table)]
      (is (= 3 (count table)))
      (is (= "Flamengo" (:team champ)))
      (is (= 10 (:points champ)))
      (is (= 10 (:goal-diff champ)))
      (is (= ["Flamengo" "Palmeiras" "Santos"] (mapv :team table)))
      (is (= [10 5 1] (mapv :points table))))))

(deftest competition-statistics
  (testing "Given a competition/season, When aggregating, Then totals/rates match"
    (let [s (q/competition-stats ms {:competition "Brasileirão" :season 2019})]
      (is (= 6 (:matches s)))
      (is (= 15 (:total-goals s)))
      (is (= 2.5 (:avg-goals-per-match s)))
      (is (= 3 (:home-wins s)))
      (is (= 1 (:away-wins s)))
      (is (= 2 (:draws s))))))

(deftest biggest-wins-ranking
  (testing "Given matches, When ranking by margin, Then largest is first"
    (let [top (first (q/biggest-wins ms {:competition "Brasileirão" :season 2019}))]
      (is (= 5 (:margin top)))
      (is (= "Flamengo" (:home top)))
      (is (= "Santos" (:away top))))))

(deftest player-search
  (testing "Given players, When searching by club, Then club members return"
    (is (= 2 (count (q/search-players ps {:club "Flamengo"})))))

  (testing "When searching by nationality, Then sorted by rating desc"
    (let [br (q/search-players ps {:nationality "Brazil"})]
      (is (= 4 (count br)))
      (is (= "Neymar Jr" (:name (first br))))
      (is (= (reverse (sort (map :overall br))) (map :overall br)))))

  (testing "When filtering by min-overall, Then low-rated excluded"
    (is (= 1 (count (q/search-players ps {:nationality "Brazil" :min-overall 85})))))

  (testing "When taking top players, Then highest rated overall first"
    (is (= "Lionel Messi" (:name (first (q/top-players ps {})))))))

;; --- Smoke checks against the real datasets (cross-file, performance) -------

(deftest real-data-smoke
  (testing "Given real data, When querying a famous fixture, Then results return"
    (let [h2h (q/head-to-head "Flamengo" "Fluminense")]
      (is (pos? (:total (:record h2h)))))
    (let [neymar (q/search-players {:name "Neymar"})]
      (is (seq neymar))
      (is (every? #(= "Brazil" (:nationality %)) neymar)))
    (let [table (q/standings "Brasileirão Série A" 2019)
          champ (first table)]
      (is (>= (count table) 18))
      ;; 2019 Brasileirão was won by Flamengo with 90 pts in 38 games — a
      ;; published, verifiable result; confirms standings are not double-counted.
      (is (data/team-matches? "Flamengo" (:team champ)))
      (is (= 90 (:points champ)))
      (is (= 38 (:played champ)))))

  (testing "Given real data, When running an aggregate query, Then it is fast (<5s)"
    (let [start (System/nanoTime)
          _ (q/competition-stats {:competition "Brasileirão"})
          elapsed-ms (/ (- (System/nanoTime) start) 1e6)]
      (is (< elapsed-ms 5000) (str "elapsed-ms=" elapsed-ms)))))
