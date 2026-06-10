(ns brazilian-soccer.queries-test
  "Feature: Match Queries

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between \"Flamengo\" and \"Fluminense\"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for \"Palmeiras\" in season \"2023\"
    Then I should receive wins, losses, draws, and goals"
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.queries :as q]
            [clojure.test :refer [deftest is testing]]))

(def db (delay @data/db))

;; ---------------------------------------------------------------------------
;; Feature: Match Queries

(deftest find-matches-between-two-teams
  (testing "When I search for matches between Flamengo and Fluminense"
    (let [ms (q/find-matches @db {:team "Flamengo" :opponent "Fluminense"})]
      (testing "Then I should receive a list of matches"
        (is (seq ms))
        (is (> (count ms) 15)))
      (testing "And each match should have date, scores, and competition"
        (doseq [m (filter q/played? ms)]
          (is (some? (:date m)))
          (is (int? (:home-goals m)))
          (is (int? (:away-goals m)))
          (is (string? (:competition m)))))
      (testing "And matches are ordered most recent first"
        (let [dates (keep :date ms)]
          (is (= dates (reverse (sort dates)))))))))

(deftest find-matches-by-team-and-season
  (testing "When I search for Palmeiras matches in 2023"
    (let [ms (q/find-matches @db {:team "Palmeiras" :season 2023})]
      (is (seq ms))
      (is (every? #(= 2023 (:season %)) ms))
      (is (every? (fn [m]
                    (let [tq (data/norm-team "Palmeiras")]
                      (or (data/team-matches? tq (:home m))
                          (data/team-matches? tq (:away m)))))
                  ms)))))

(deftest find-matches-by-competition
  (testing "When I filter by competition"
    (let [cup (q/find-matches @db {:team "Flamengo" :competition "Copa do Brasil"})
          lib (q/find-matches @db {:team "Flamengo" :competition "Libertadores"})]
      (is (seq cup))
      (is (every? #(= "Copa do Brasil" (:competition %)) cup))
      (is (seq lib))
      (is (every? #(= "Copa Libertadores" (:competition %)) lib)))))

(deftest find-matches-by-date-range
  (testing "When I filter by a date range"
    (let [ms (q/find-matches @db {:team "Santos"
                                  :date-from "2019-01-01"
                                  :date-to "2019-12-31"})]
      (is (seq ms))
      (is (every? #(= 2019 (.getYear ^java.time.LocalDate (:date %))) ms)))))

(deftest find-libertadores-finals
  (testing "When I search Libertadores by stage data present"
    (let [finals (filter #(= "final" (:stage %))
                         (q/find-matches @db {:competition "Libertadores"}))]
      (is (seq finals)))))

;; ---------------------------------------------------------------------------
;; Feature: Team Queries

(deftest get-team-statistics
  (testing "When I request statistics for Palmeiras in season 2023"
    (let [{:keys [played wins draws losses gf ga]}
          (q/team-stats @db {:team "Palmeiras" :season 2023})]
      (testing "Then I should receive wins, losses, draws, and goals"
        (is (pos? played))
        (is (= played (+ wins draws losses)))
        (is (nat-int? gf))
        (is (nat-int? ga))))))

(deftest corinthians-home-record-2022
  (testing "When I request Corinthians' home record for the 2022 Brasileirão"
    (let [rec (q/team-stats @db {:team "Corinthians" :season 2022
                                 :competition "brasileirao" :venue :home})]
      (is (= 19 (:played rec)) "a full home season is 19 matches")
      (is (= (:played rec) (+ (:wins rec) (:draws rec) (:losses rec)))))))

(deftest head-to-head-comparison
  (testing "When I compare Palmeiras and Santos head-to-head"
    (let [{:keys [team1-wins team2-wins draws matches]}
          (q/head-to-head @db "Palmeiras" "Santos")]
      (is (seq matches))
      (is (= (count (filter q/played? matches))
             (+ team1-wins team2-wins draws))
          "every completed match is a win, loss or draw")
      (testing "And both teams appear in every match"
        (let [t1 (data/norm-team "Palmeiras")
              t2 (data/norm-team "Santos")]
          (doseq [m matches]
            (is (or (and (data/team-matches? t1 (:home m))
                         (data/team-matches? t2 (:away m)))
                    (and (data/team-matches? t2 (:home m))
                         (data/team-matches? t1 (:away m)))))))))))

;; ---------------------------------------------------------------------------
;; Feature: Competition Queries

(deftest standings-2019-brasileirao
  (testing "When I calculate the 2019 Brasileirão standings"
    (let [rows (q/standings @db {:season 2019})]
      (testing "Then there are 20 teams playing 38 matches each"
        (is (= 20 (count rows)))
        (is (every? #(= 38 (:played %)) rows)))
      (testing "And Flamengo is champion with 90 points (28W 6D 4L)"
        (let [{:keys [display points wins draws losses]} (first rows)]
          (is (re-find #"Flamengo" display))
          (is (= 90 points))
          (is (= [28 6 4] [wins draws losses]))))
      (testing "And Avaí finished last"
        (is (re-find #"Avai" (:display (last rows))))))))

(deftest standings-2022-uses-backfilled-scores
  (testing "When the primary file has NA scores, results are filled from the extended dataset"
    (let [rows (q/standings @db {:season 2022})]
      (is (re-find #"Palmeiras" (:display (first rows))))
      (is (= 81 (:points (first rows))) "Palmeiras won the 2022 title with 81 points"))))

;; ---------------------------------------------------------------------------
;; Feature: Statistical Analysis

(deftest average-goals-per-match
  (testing "When I compute Brasileirão aggregate statistics"
    (let [s (q/competition-summary @db {:competition "brasileirao"})]
      (is (> (:matches s) 8000))
      (is (< 1.5 (:avg-goals s) 4.0) "sane goals-per-match average")
      (is (> (:home-win-rate s) (:away-win-rate s)) "home advantage exists")
      (is (< 99.9 (+ (:home-win-rate s) (:draw-rate s) (:away-win-rate s)) 100.1)))))

(deftest biggest-wins
  (testing "When I ask for the biggest victories"
    (let [ms (q/biggest-wins @db {} 5)]
      (is (= 5 (count ms)))
      (is (>= (abs (- (:home-goals (first ms)) (:away-goals (first ms)))) 5))
      (testing "And they are sorted by margin"
        (let [margins (map #(abs (- (:home-goals %) (:away-goals %))) ms)]
          (is (= margins (reverse (sort margins)))))))))

(deftest best-home-records
  (testing "When I rank teams by home win rate"
    (let [rows (q/best-records @db {:competition "brasileirao"} :home 50 5)]
      (is (= 5 (count rows)))
      (is (every? #(>= (:played %) 50) rows))
      (let [rates (map :win-rate rows)]
        (is (= rates (reverse (sort rates)))))
      (is (> (:win-rate (first rows)) 50.0)))))

;; ---------------------------------------------------------------------------
;; Feature: Player Queries

(deftest search-players-by-name
  (testing "When I search for Neymar"
    (let [p (q/find-player @db "Neymar")]
      (is (some? p))
      (is (= "Neymar Jr" (:name p)))
      (is (= "Brazil" (:nationality p)))
      (is (= 92 (:overall p))))))

(deftest search-brazilian-players
  (testing "When I filter players by Brazilian nationality"
    (let [ps (q/search-players @db {:nationality "Brazil"})]
      (is (= 827 (count ps)))
      (testing "And they are sorted by overall rating"
        (is (= (map :overall ps) (reverse (sort (map :overall ps))))))
      (testing "And the best Brazilian is Neymar Jr"
        (is (= "Neymar Jr" (:name (first ps))))))))

(deftest search-players-by-club-and-filters
  (testing "When I search players at a Brazilian club (accent-insensitive)"
    (let [ps (q/search-players @db {:club "Gremio"})]
      (is (seq ps))
      (is (every? #(re-find #"(?i)grêmio" (:club %)) ps))))
  (testing "When I combine position and rating filters"
    (let [ps (q/search-players @db {:nationality "Brazil" :position "GK" :min-overall 85})]
      (is (seq ps))
      (is (every? #(and (= "GK" (:position %)) (>= (:overall %) 85)) ps)))))

;; ---------------------------------------------------------------------------
;; Feature: Cross-file queries and extended stats

(deftest cross-file-player-and-match-data
  (testing "When I look up a club found in the player data within the match data"
    (let [club-players (q/search-players @db {:club "Grêmio"})
          club-matches (q/find-matches @db {:team "Grêmio"})]
      (is (seq club-players))
      (is (seq club-matches))
      (is (> (count club-matches) 500)))))

(deftest extended-corner-and-shot-stats
  (testing "When I ask for extended stats for Flamengo"
    (let [{:keys [matches averages]} (q/extended-stats @db {:team "Flamengo"})]
      (is (seq matches))
      (is (pos? (:corners-for averages)))
      (is (pos? (:shots-for averages))))))

(deftest competitions-overview
  (testing "When I list dataset coverage"
    (let [overview (q/competitions-overview @db)
          comps (set (map :competition overview))]
      (is (contains? comps "Brasileirão Série A"))
      (is (contains? comps "Copa do Brasil"))
      (is (contains? comps "Copa Libertadores"))
      (let [serie-a (first (filter #(= "Brasileirão Série A" (:competition %)) overview))]
        (is (= 2003 (first (:seasons serie-a))) "historical data reaches back to 2003")
        (is (>= (last (:seasons serie-a)) 2023) "extended data reaches 2023")))))

;; ---------------------------------------------------------------------------
;; Feature: Query performance

(deftest query-performance
  (let [_ @db] ; ensure data is loaded before timing
    (testing "Simple lookups respond in under 2 seconds"
      (let [t0 (System/nanoTime)
            _ (doall (q/find-matches @db {:team "Flamengo" :opponent "Corinthians"}))
            ms (/ (- (System/nanoTime) t0) 1e6)]
        (is (< ms 2000))))
    (testing "Aggregate queries respond in under 5 seconds"
      (let [t0 (System/nanoTime)
            _ (doall (q/standings @db {:season 2019}))
            _ (q/competition-summary @db {:competition "brasileirao"})
            ms (/ (- (System/nanoTime) t0) 1e6)]
        (is (< ms 5000))))))
