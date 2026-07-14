(ns brazilian-soccer-mcp.queries-test
  "BDD-style Given/When/Then tests for the query layer. Each `deftest`
  represents a feature; each `testing` block is one scenario."
  (:require [brazilian-soccer-mcp.data    :as data]
            [brazilian-soccer-mcp.queries :as q]
            [clojure.test :refer [deftest is testing use-fixtures]]))

;; ---------------------------------------------------------------------------
;; Shared dataset fixture — load once for the whole test namespace.
;; ---------------------------------------------------------------------------

(def ^:dynamic *ds* nil)

(defn- with-dataset [t]
  (binding [*ds* (data/load-dataset "data/kaggle")]
    (t)))

(use-fixtures :once with-dataset)

;; ---------------------------------------------------------------------------
;; Feature: Match Queries
;; ---------------------------------------------------------------------------

(deftest feature-match-queries
  (testing "Scenario: find matches between two teams"
    ;; Given the match data is loaded
    ;; When I search for matches between Flamengo and Fluminense
    (let [ms (q/filter-matches *ds* {:team-a "Flamengo" :team-b "Fluminense"})]
      ;; Then I should receive a list of matches
      (is (pos? (count ms)) "expected at least one Fla-Flu derby")
      ;; And each match should have date, scores, and competition
      (doseq [m (take 5 ms)]
        (is (some? (:date m)))
        (is (some? (:home m)))
        (is (some? (:away m)))
        (is (some? (:competition m))))))

  (testing "Scenario: filter matches by season"
    (let [ms (q/filter-matches *ds* {:team "Palmeiras" :season 2019 :competition "Brasileirão"})]
      (is (= 38 (count ms))
          "Palmeiras play 38 Brasileirão matches in a season")
      (is (every? #(= 2019 (:season %)) ms))))

  (testing "Scenario: filter matches by competition"
    (let [ms (q/filter-matches *ds* {:competition "Copa Libertadores" :limit 5})]
      (is (= 5 (count ms)))
      (is (every? #(= "Copa Libertadores" (:competition %)) ms))))

  (testing "Scenario: filter by date range"
    (let [ms (q/filter-matches *ds* {:date-from "2019-01-01" :date-to "2019-12-31"
                                     :competition "Brasileirão" :limit 1000})]
      (is (every? #(and (>= (compare (:date %) "2019-01-01") 0)
                        (<= (compare (:date %) "2019-12-31") 0)) ms)))))

;; ---------------------------------------------------------------------------
;; Feature: Team Statistics
;; ---------------------------------------------------------------------------

(deftest feature-team-statistics
  (testing "Scenario: get team statistics for a season"
    ;; Given the match data is loaded
    ;; When I request statistics for "Flamengo" in season 2019 Brasileirão
    (let [s (q/team-stats *ds* "Flamengo" {:season 2019 :competition "Brasileirão"})]
      ;; Then I should receive wins, losses, draws, and goals
      (is (= 38 (:matches s)))
      (is (= 28 (:wins s))   "Flamengo's actual 2019 wins")
      (is (= 6  (:draws s)))
      (is (= 4  (:losses s)))
      (is (>= (:goals-for s) 80))
      (is (= (:matches s) (+ (:wins s) (:draws s) (:losses s))))))

  (testing "Scenario: head-to-head aggregation"
    (let [h (q/head-to-head *ds* "Flamengo" "Fluminense")
          {:keys [a-wins b-wins draws]} (:aggregate h)]
      (is (> (:total h) 10))
      (is (= (:total h) (+ a-wins b-wins draws))
          "wins + draws should account for every match in the head-to-head"))))

;; ---------------------------------------------------------------------------
;; Feature: Competition Standings
;; ---------------------------------------------------------------------------

(deftest feature-competition-standings
  (testing "Scenario: 2019 Brasileirão champion is Flamengo with 90 points"
    (let [rows (q/standings *ds* {:season 2019 :competition "Brasileirão"})
          champ (first rows)]
      (is (= "flamengo-rj" (data/normalize-team (:team champ))))
      (is (= 90 (:points champ)))
      (is (= 28 (:wins champ)))))

  (testing "Scenario: standings rows sum to a consistent W/D/L per team"
    (let [rows (q/standings *ds* {:season 2019 :competition "Brasileirão"})]
      (doseq [r (take 10 rows)]
        (is (= (:matches r) (+ (:wins r) (:draws r) (:losses r)))
            (str (:team r) " matches should equal W+D+L"))
        (is (= (:points r) (+ (* 3 (:wins r)) (:draws r))))))))

;; ---------------------------------------------------------------------------
;; Feature: Statistical Analysis
;; ---------------------------------------------------------------------------

(deftest feature-statistical-analysis
  (testing "Scenario: average goals per match is a reasonable football number"
    (let [{:keys [matches avg-goals]} (q/average-goals *ds* {:competition "Brasileirão"})]
      (is (pos? matches))
      (is (< 1.5 avg-goals 4.0) "average goals should be in football range")))

  (testing "Scenario: home win rate"
    (let [{:keys [home-win-rate away-win-rate draw-rate]}
          (q/home-win-rate *ds* {:competition "Brasileirão"})]
      (is (< 0.3 home-win-rate 0.7))
      (is (> home-win-rate away-win-rate)
          "home advantage means home win rate > away win rate")
      (is (< (Math/abs (- 1.0 (+ home-win-rate away-win-rate draw-rate))) 0.001))))

  (testing "Scenario: biggest wins are sorted by margin"
    (let [ms (q/biggest-wins *ds* {:limit 5})]
      (is (= 5 (count ms)))
      (let [margins (map #(Math/abs (- (:home-goal %) (:away-goal %))) ms)]
        (is (apply >= margins) "biggest-wins must be sorted by margin desc")))))

;; ---------------------------------------------------------------------------
;; Feature: Player Queries
;; ---------------------------------------------------------------------------

(deftest feature-player-queries
  (testing "Scenario: search by name"
    (let [ps (q/search-players *ds* {:name "Neymar" :limit 5})]
      (is (some #(re-find #"(?i)neymar" (:name %)) ps))))

  (testing "Scenario: filter by nationality returns only Brazilians"
    (let [ps (q/search-players *ds* {:nationality "Brazil" :limit 50})]
      (is (= 50 (count ps)))
      (is (every? #(= "Brazil" (:nationality %)) ps))))

  (testing "Scenario: minimum overall filter"
    (let [ps (q/search-players *ds* {:nationality "Brazil" :min-overall 85 :limit 100})]
      (is (every? #(>= (:overall %) 85) ps))
      (is (pos? (count ps)))))

  (testing "Scenario: players are sorted by overall rating descending by default"
    (let [ps (q/search-players *ds* {:nationality "Brazil" :limit 5})
          os (map :overall ps)]
      (is (apply >= os)))))

;; ---------------------------------------------------------------------------
;; Feature: Pretty-printers
;; ---------------------------------------------------------------------------

(deftest feature-formatting
  (testing "Scenario: match formatter includes both teams and a score"
    (let [m (first (q/filter-matches *ds* {:competition "Brasileirão"}))
          line (q/format-match m)]
      (is (.contains line (:home m)))
      (is (.contains line (:away m)))))

  (testing "Scenario: team stats formatter mentions W/D/L"
    (let [s (q/team-stats *ds* "Palmeiras" {:season 2019})
          text (q/format-team-stats s)]
      (is (.contains text "W/D/L")))))
