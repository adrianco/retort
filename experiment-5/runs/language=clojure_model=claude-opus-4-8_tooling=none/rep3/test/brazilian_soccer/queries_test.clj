;; =============================================================================
;; brazilian-soccer.queries-test
;; -----------------------------------------------------------------------------
;; BDD (Given/When/Then) scenarios for the query & statistics layer, exercised
;; against the deterministic fixtures so expected counts are exact. Mirrors the
;; capability categories in the specification (match / team / player /
;; competition / statistics queries).
;; =============================================================================
(ns brazilian-soccer.queries-test
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.queries :as q]
            [brazilian-soccer.fixtures :as fx]))

(def M fx/matches)
(def P fx/players*)

;; ---- Feature: Match Queries -----------------------------------------------

(deftest find-matches-between-two-teams
  (testing "Scenario: Find matches between two teams"
    ;; Given the match data is loaded / When I search Flamengo vs Fluminense
    (let [res (q/matches-between M "Flamengo" "Fluminense")]
      ;; Then I receive the list, each with date and scores
      (is (= 2 (count res)))
      (is (every? :date res))
      (is (every? #(some? (:home-goal %)) res))
      ;; And results are sorted most-recent-first
      (is (= "2019-09-03" (:date (first res)))))))

(deftest find-matches-by-team-and-season
  (testing "Scenario: matches a team played in a season (across competitions)"
    (let [res (q/find-matches M {:team "Flamengo" :season 2019})]
      ;; 4 Brasileirão games + 1 Copa do Brasil final = 5
      (is (= 5 (count res)))
      (is (every? #(= 2019 (:season %)) res)))))

(deftest find-matches-by-competition
  (testing "Scenario: filter by competition (accent-insensitive substring)"
    (is (= 1 (count (q/find-matches M {:competition "Libertadores"}))))
    ;; Flamengo's two home Brasileirão games in 2019 (vs Fluminense, vs Grêmio)
    (is (= 2 (count (q/find-matches M {:competition "Brasileirão" :team "Flamengo" :home "Flamengo" :season 2019}))))))

(deftest find-matches-by-date-range
  (testing "Scenario: filter by inclusive date range"
    (let [res (q/find-matches M {:from "2019-09-01" :to "2019-09-30"})]
      (is (pos? (count res)))
      (is (every? #(<= 0 (compare (:date %) "2019-09-01")) res))
      (is (every? #(>= 0 (compare (:date %) "2019-09-30")) res)))))

(deftest head-to-head-scenario
  (testing "Scenario: head-to-head summary from one team's perspective"
    (let [h (q/head-to-head M "Flamengo" "Fluminense")]
      (is (= 2 (:played h)))
      (is (= 1 (:a-wins h)))      ; Flamengo won 2-1
      (is (= 1 (:b-wins h)))      ; Fluminense won 1-0
      (is (= 0 (:draws h)))
      (is (= 2 (:a-goals h)))
      (is (= 2 (:b-goals h))))))

;; ---- Feature: Team Queries ------------------------------------------------

(deftest team-record-overall
  (testing "Scenario: Get team statistics for Flamengo in 2019"
    (let [ms (q/find-matches M {:team "Flamengo" :season 2019})
          r  (q/team-record ms "Flamengo")]
      (is (= 5 (:played r)))      ; 4 league + 1 cup final
      (is (= 3 (:wins r)))        ; beat Fluminense, Grêmio, Palmeiras(away)
      (is (= 1 (:losses r)))      ; lost to Fluminense away
      (is (= 1 (:draws r)))       ; cup final 1-1 vs São Paulo
      (is (= 11 (:goals-for r)))  ; 2 + 0 + 5 + 3 + 1
      (is (= 4  (:goals-against r))) ; 1 + 1 + 0 + 1 + 1
      (is (< 0.59 (:win-rate r) 0.61)))))  ; 3/5

(deftest team-record-home-only
  (testing "Scenario: home record only counts home matches"
    (let [ms (q/find-matches M {:team "Flamengo" :season 2019})
          r  (q/team-record ms "Flamengo" :home)]
      (is (= 2 (:played r)))      ; vs Fluminense (2-1), vs Grêmio (5-0)
      (is (= 2 (:wins r)))
      (is (= 7 (:goals-for r))))))

;; ---- Feature: Player Queries ----------------------------------------------

(deftest find-brazilian-players
  (testing "Scenario: Find all Brazilian players, highest rated first"
    (let [res (q/find-players P {:nationality "Brazil"})]
      (is (= 6 (count res)))
      (is (= "Neymar Jr" (:name (first res))))
      (is (apply >= (map :overall res))))))

(deftest players-at-club-scenario
  (testing "Scenario: which players play for Flamengo"
    (let [res (q/players-at-club P "Flamengo")]
      (is (= 2 (count res)))
      (is (= #{"Gabriel Barbosa" "Bruno Henrique"} (set (map :name res)))))))

(deftest find-player-by-name
  (testing "Scenario: Who is Gabriel Barbosa"
    (let [res (q/find-players P {:name "Gabriel"})]
      (is (= 1 (count res)))
      (is (= "Gabriel Barbosa" (:name (first res)))))))

(deftest find-players-by-position
  (testing "Scenario: forwards only via position code"
    (is (= 1 (count (q/find-players P {:position "ST"}))))
    (is (= "Gabriel Barbosa" (:name (first (q/find-players P {:position "ST"})))))))

(deftest top-players-scenario
  (testing "Scenario: top N Brazilian players"
    (let [res (q/top-players P 3 "Brazil")]
      (is (= 3 (count res)))
      (is (= ["Neymar Jr" "Alisson" "Casemiro"] (map :name res))))))

;; ---- Feature: Competition Queries -----------------------------------------

(deftest standings-scenario
  (testing "Scenario: compute 2019 standings, Flamengo leads on points"
    (let [ms   (q/find-matches M {:competition "Brasileirão" :season 2019})
          rows (q/standings ms)
          flo  (first (filter #(= "Flamengo" (:team %)) rows))]
      (is (= "Flamengo" (:team (first rows))))
      (is (= 9 (:points flo)))   ; 3 wins x 3
      (is (= 3 (:wins flo))))))

(deftest champion-scenario
  (testing "Scenario: Who won the 2019 Brasileirão (from fixtures)"
    (let [ms (q/find-matches M {:competition "Brasileirão" :season 2019})]
      (is (= "Flamengo" (:team (q/champion ms)))))))

;; ---- Feature: Statistical Analysis ----------------------------------------

(deftest avg-goals-scenario
  (testing "Scenario: average goals per match over decided games"
    (is (< 0 (q/avg-goals M)))))

(deftest biggest-wins-scenario
  (testing "Scenario: biggest victories ranked by margin"
    (let [res (q/biggest-wins M 3)]
      (is (= 3 (count res)))
      ;; Santos 8-0 Bolivar is the largest margin in the fixtures
      (is (= 8 (:home-goal (first res))))
      (is (= "Santos" (:home (first res)))))))

(deftest home-win-rate-scenario
  (testing "Scenario: home win rate is a fraction in [0,1]"
    (let [r (q/home-win-rate M)]
      (is (<= 0.0 r 1.0)))))
