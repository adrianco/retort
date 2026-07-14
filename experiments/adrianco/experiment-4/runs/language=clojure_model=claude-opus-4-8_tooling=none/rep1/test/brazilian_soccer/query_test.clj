(ns brazilian-soccer.query-test
  "=============================================================================
   BDD tests (Given-When-Then) for the query engine.
   =============================================================================
   Exercises the five capability areas from the specification against the real
   loaded datasets: match queries, team queries, player queries, competition
   queries (standings/champion), and statistical analysis."
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.string :as str]
            [brazilian-soccer.fixtures :as fix]
            [brazilian-soccer.query :as q]))

(defn- involves-key?
  "True when canonical key substring `q` appears on either side of match `m`.
   Mirrors the substring containment the query layer uses, so suffixed keys
   like \"flamengo rj\" still count as involving \"flamengo\"."
  [m q]
  (or (str/includes? (:home-key m) q) (str/includes? (:away-key m) q)))

;; ---------------------------------------------------------------------------
;; Data loading
;; ---------------------------------------------------------------------------

(deftest data-loads
  (testing "Scenario: all six datasets load into the knowledge graph"
    ;; Given the data directory
    ;; When the database is loaded
    (let [db (fix/db)]
      ;; Then we have many matches, players and derived teams. (Counts reflect
      ;; the de-duplicated, single-authoritative-source-per-competition graph.)
      (is (> (count (:matches db)) 15000) "all match files combined")
      (is (> (count (:players db)) 18000) "FIFA players")
      (is (> (count (:teams db)) 50) "derived team nodes")
      (testing "and every match has a normalized schema"
        (let [m (first (:matches db))]
          (is (contains? m :home-key))
          (is (contains? m :competition)))))))

;; ---------------------------------------------------------------------------
;; 1. Match queries
;; ---------------------------------------------------------------------------

(deftest match-queries
  (let [db (fix/db)]
    (testing "Scenario: find matches between two teams"
      ;; When I search for matches between Flamengo and Fluminense
      (let [ms (q/search-matches db {:team "Flamengo" :opponent "Fluminense" :limit 1000})]
        ;; Then I receive a non-empty list
        (is (seq ms))
        ;; And each match has a date, scores and competition
        (is (every? #(contains? % :competition) ms))
        (is (every? #(involves-key? % "flamengo") ms))
        (is (every? #(involves-key? % "fluminense") ms))))

    (testing "Scenario: filter matches by team and season"
      (let [ms (q/search-matches db {:team "Palmeiras" :season 2019 :limit 1000})]
        (is (seq ms))
        (is (every? #(= 2019 (:season %)) ms))))

    (testing "Scenario: filter matches by competition"
      (let [ms (q/search-matches db {:competition "Libertadores" :limit 50})]
        (is (seq ms))
        (is (every? #(= "Copa Libertadores" (:competition %)) ms))))

    (testing "Scenario: results are sorted most-recent first"
      (let [ms (q/search-matches db {:team "Santos" :limit 20})
            dates (keep :date ms)]
        (is (= dates (reverse (sort dates))))))

    (testing "Scenario: when did two teams last play"
      (let [m (q/last-match db "Flamengo" "Corinthians")]
        (is (some? m))
        (is (some? (:date m)))))))

;; ---------------------------------------------------------------------------
;; 2. Team queries
;; ---------------------------------------------------------------------------

(deftest team-queries
  (let [db (fix/db)]
    (testing "Scenario: get team statistics for a season"
      ;; When I request Palmeiras stats for 2019
      (let [s (q/team-stats db "Palmeiras" {:season 2019})]
        ;; Then I receive wins, draws, losses and goals that are internally consistent
        (is (some? s))
        (is (= (:matches s) (+ (:win s) (:draw s) (:loss s))))
        (is (<= 0.0 (:win-rate s) 100.0))
        (is (>= (:goals-for s) 0))))

    (testing "Scenario: home record only"
      (let [s (q/team-stats db "Corinthians" {:season 2022 :venue :home
                                              :competition "Brasileirão Série A"})]
        (is (some? s))
        (is (= :home (:venue s)))))

    (testing "Scenario: head-to-head between two clubs"
      (let [h (q/head-to-head db "Palmeiras" "Santos")]
        (is (some? h))
        (is (= (:total h) (+ (:team1-wins h) (:team2-wins h) (:draws h))))
        (is (pos? (:total h)))))

    (testing "Scenario: resolving an unknown team yields nil stats"
      (is (nil? (q/team-stats db "Nonexistent United FC" {}))))))

;; ---------------------------------------------------------------------------
;; 3. Player queries
;; ---------------------------------------------------------------------------

(deftest player-queries
  (let [db (fix/db)]
    (testing "Scenario: search a player by name"
      (let [ps (q/search-players db {:name "Neymar"})]
        (is (seq ps))
        (is (some #(re-find #"(?i)neymar" (:name %)) ps))))

    (testing "Scenario: find Brazilian players sorted by rating"
      (let [ps (q/top-players db {:nationality "Brazil" :limit 10})]
        (is (= 10 (count ps)))
        (is (every? #(= "Brazil" (:nationality %)) ps))
        ;; sorted descending by overall
        (is (= (map :overall ps) (reverse (sort (map :overall ps)))))))

    (testing "Scenario: filter players by club and minimum rating"
      (let [ps (q/search-players db {:club "Santos" :min-overall 70 :limit 100})]
        (is (every? #(>= (:overall %) 70) ps))))

    (testing "Scenario: club roster reports squad size and average rating"
      (let [r (q/club-roster db "Santos")]
        (is (pos? (:count r)))
        (is (number? (:avg-overall r)))
        (is (= (:count r) (count (:players r))))))

    (testing "Scenario: exact-match-first club search excludes lookalike clubs"
      ;; A query for Santos (FC) must not pull in the distinct \"Santos Laguna\".
      (let [r (q/club-roster db "Santos")]
        (is (every? #(= "santos" (:club-key %)) (:players r))
            "only Santos FC players, not Santos Laguna")))))

(deftest performance
  (let [db (fix/db)]
    (testing "Scenario: a simple lookup responds well under 2 seconds"
      (let [start (System/nanoTime)
            _ (q/search-matches db {:team "Flamengo" :opponent "Fluminense"})
            ms (/ (- (System/nanoTime) start) 1e6)]
        (is (< ms 2000.0) (format "simple lookup took %.0f ms" ms))))
    (testing "Scenario: an aggregate query responds well under 5 seconds"
      (let [start (System/nanoTime)
            _ (q/standings db {:competition "Brasileirão Série A" :season 2019})
            _ (q/competition-stats db {:competition "Brasileirão Série A"})
            ms (/ (- (System/nanoTime) start) 1e6)]
        (is (< ms 5000.0) (format "aggregate query took %.0f ms" ms))))))

;; ---------------------------------------------------------------------------
;; 4. Competition queries
;; ---------------------------------------------------------------------------

(deftest competition-queries
  (let [db (fix/db)]
    (testing "Scenario: who won the 2019 Brasileirão"
      ;; When I compute the 2019 standings
      (let [rows (q/standings db {:competition "Brasileirão Série A" :season 2019})
            champ (q/champion db {:competition "Brasileirão Série A" :season 2019})]
        ;; Then there is a full table ranked by points
        (is (>= (count rows) 16))
        (is (= 1 (:rank (first rows))))
        ;; And Flamengo are the calculated 2019 champions
        (is (= "Flamengo" (:team champ)))
        (is (>= (:points champ) (:points (second rows))))))

    (testing "Scenario: a league season is a coherent single-source table"
      ;; Regression guard for the de-duplication / single-source design:
      ;; the 2019 Série A must be a 20-team, 380-match double round-robin with
      ;; Flamengo as champions on exactly 90 points (28W, 6D, 4L).
      (let [rows (q/standings db {:competition "Brasileirão Série A" :season 2019})
            champ (first rows)]
        (is (= 20 (count rows)) "20 teams")
        (is (every? #(= 38 (:played %)) rows) "38 games each")
        (is (= "Flamengo" (:team champ)))
        (is (= 90 (:points champ)))
        (is (= [28 6 4] [(:win champ) (:draw champ) (:loss champ)]))))

    (testing "Scenario: standings are internally consistent"
      (let [rows (q/standings db {:competition "Brasileirão Série A" :season 2018})]
        (is (every? #(= (:points %) (+ (* 3 (:win %)) (:draw %))) rows))
        (is (every? #(= (:played %) (+ (:win %) (:draw %) (:loss %))) rows))))

    (testing "Scenario: list available competitions and seasons"
      (is (some #{"Copa do Brasil"} (q/list-competitions db)))
      (is (some #{"Copa Libertadores"} (q/list-competitions db)))
      (is (seq (q/list-seasons db "Brasileirão Série A"))))))

;; ---------------------------------------------------------------------------
;; 5. Statistical analysis
;; ---------------------------------------------------------------------------

(deftest statistical-analysis
  (let [db (fix/db)]
    (testing "Scenario: average goals per match for the Brasileirão"
      (let [s (q/competition-stats db {:competition "Brasileirão Série A"})]
        (is (pos? (:matches s)))
        (is (< 1.0 (:avg-goals-per-match s) 5.0))
        (is (<= 0.0 (:home-win-rate s) 100.0))
        (is (= (:matches s) (+ (:home-wins s) (:away-wins s) (:draws s))))))

    (testing "Scenario: biggest wins are ordered by margin"
      (let [ms (q/biggest-wins db {:limit 10})
            margins (map #(Math/abs (- (:home-goal %) (:away-goal %))) ms)]
        (is (= 10 (count ms)))
        (is (= margins (reverse (sort margins))))
        (is (>= (first margins) 5))))

    (testing "Scenario: best home record ranks teams by win rate"
      (let [rows (q/best-record db {:competition "Brasileirão Série A" :season 2019
                                    :venue :home :min-matches 5 :limit 5})]
        (is (seq rows))
        (is (= (map :win-rate rows) (reverse (sort (map :win-rate rows)))))))))
