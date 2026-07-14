(ns brazilian-soccer-mcp.queries-test
  "BDD-style Given/When/Then tests against a hand-built tiny dataset.
   These tests do not touch disk — they verify the query semantics."
  (:require [clojure.test :refer [deftest is testing]]
            [brazilian-soccer-mcp.queries :as q]))

;; ---- fixture -----------------------------------------------------------

(def ^:private sample-matches
  [{:competition "Brasileirão Série A" :season 2023 :round 22
    :date "2023-09-03" :home "Flamengo-RJ" :away "Fluminense-RJ"
    :home-goal 2 :away-goal 1}

   {:competition "Brasileirão Série A" :season 2023 :round 8
    :date "2023-05-28" :home "Fluminense-RJ" :away "Flamengo-RJ"
    :home-goal 1 :away-goal 0}

   {:competition "Brasileirão Série A" :season 2023 :round 1
    :date "2023-04-15" :home "Palmeiras-SP" :away "Santos-SP"
    :home-goal 3 :away-goal 0}

   {:competition "Brasileirão Série A" :season 2023 :round 2
    :date "2023-04-22" :home "Santos-SP" :away "Palmeiras-SP"
    :home-goal 0 :away-goal 2}

   {:competition "Brasileirão Série A" :season 2023 :round 3
    :date "2023-04-29" :home "Flamengo-RJ" :away "Palmeiras-SP"
    :home-goal 1 :away-goal 1}

   {:competition "Copa do Brasil" :season 2023
    :date "2023-08-01" :home "Flamengo-RJ" :away "São Paulo"
    :home-goal 0 :away-goal 1}

   {:competition "Copa Libertadores" :season 2023 :stage "group stage"
    :date "2023-04-04" :home "Flamengo-RJ" :away "Aucas"
    :home-goal 2 :away-goal 1}])

(def ^:private sample-players
  [{:id 1 :name "Neymar Jr"      :nationality "Brazil"    :overall 91
    :club "Paris Saint-Germain"  :position "LW"}
   {:id 2 :name "Casemiro"       :nationality "Brazil"    :overall 89
    :club "Manchester United"    :position "CDM"}
   {:id 3 :name "Gabriel Barbosa":nationality "Brazil"    :overall 84
    :club "Flamengo"             :position "ST"}
   {:id 4 :name "L. Messi"       :nationality "Argentina" :overall 94
    :club "Paris Saint-Germain"  :position "RW"}
   {:id 5 :name "Rodrygo"        :nationality "Brazil"    :overall 79
    :club "Real Madrid"          :position "RW"}])

(def ^:private db {:matches sample-matches :players sample-players})

;; ---- Feature: Match Queries -------------------------------------------

(deftest feature-match-queries
  (testing "Scenario: Find matches between two teams"
    ;; Given the match data is loaded
    ;; When I search for matches between Flamengo and Fluminense
    (let [ms (q/matches-between db "Flamengo" "Fluminense")]
      ;; Then I should receive a list of matches
      (is (= 2 (count ms)))
      ;; And each match should have date, scores, and competition
      (is (every? :date ms))
      (is (every? :competition ms))
      (is (every? #(and (:home-goal %) (:away-goal %)) ms))))

  (testing "Scenario: Filter matches by competition"
    (let [libs (q/matches-by-team db "Flamengo" {:competition "Libertadores"})]
      (is (= 1 (count libs)))
      (is (= "Copa Libertadores" (:competition (first libs))))))

  (testing "Scenario: Name variants resolve to the same team"
    (let [a (q/matches-by-team db "Flamengo")
          b (q/matches-by-team db "Flamengo-RJ")]
      (is (= (count a) (count b)))
      (is (pos? (count a))))))

;; ---- Feature: Head-to-Head --------------------------------------------

(deftest feature-head-to-head
  (testing "Scenario: Aggregate Flamengo vs Fluminense"
    (let [h (q/head-to-head db "Flamengo" "Fluminense")]
      (is (= 2 (:total h)))
      (is (= 1 (:a-wins h)))
      (is (= 1 (:b-wins h)))
      (is (= 0 (:draws h))))))

;; ---- Feature: Team Stats ----------------------------------------------

(deftest feature-team-stats
  (testing "Scenario: Palmeiras 2023 season aggregate"
    ;; Given the match data is loaded
    ;; When I request statistics for Palmeiras in season 2023
    (let [s (q/team-stats db "Palmeiras" {:season 2023})]
      ;; Then I should receive wins, losses, draws, and goals
      (is (= 3 (:matches s)))
      (is (= 2 (:wins s)))
      (is (= 1 (:draws s)))
      (is (= 0 (:losses s)))
      (is (= 6 (:goals-for s)))      ;; 3 + 2 + 1
      (is (= 1 (:goals-against s)))  ;; 0 + 0 + 1
      (is (= 7 (:points s)))))       ;; 2*3 + 1
  (testing "Scenario: Goals for/against are correct from either side"
    (let [s (q/team-stats db "Santos")]
      (is (= 2 (:matches s)))
      (is (= 0 (:goals-for s)))
      (is (= 5 (:goals-against s))))))

;; ---- Feature: Standings -----------------------------------------------

(deftest feature-standings
  (testing "Scenario: Calculated 2023 Brasileirão table from sample data"
    (let [t (q/standings db 2023 {:competition "Brasileirão"})
          rank (into {} (map-indexed (fn [i r] [(:team r) (inc i)]) t))]
      (is (every? #(pos? (:matches %)) t))
      (is (<= (rank "Palmeiras-SP" 99)
              (rank "Santos-SP"    99))))))

;; ---- Feature: Stats ---------------------------------------------------

(deftest feature-statistics
  (testing "Scenario: Average goals per match"
    (let [avg (q/avg-goals-per-match db)]
      (is (< 2.0 avg 4.5))))
  (testing "Scenario: Biggest wins listed first"
    (let [bw (q/biggest-wins db {:limit 3})]
      (is (= 3 (count bw)))
      (let [diff (Math/abs (- (:home-goal (first bw))
                              (:away-goal (first bw))))]
        (is (= diff 3)))))
  (testing "Scenario: Home win rate is between 0 and 1"
    (let [r (q/home-win-rate db)]
      (is (and (>= r 0.0) (<= r 1.0))))))

;; ---- Feature: Player Queries ------------------------------------------

(deftest feature-player-queries
  (testing "Scenario: Search by partial name"
    (let [ps (q/players-by-name db "Gabriel")]
      (is (= 1 (count ps)))
      (is (= "Gabriel Barbosa" (:name (first ps))))))

  (testing "Scenario: Filter Brazilian players, sorted by overall"
    (let [ps (q/players-by-nationality db "Brazil")]
      (is (= 4 (count ps)))
      (is (= "Neymar Jr" (:name (first ps))))))

  (testing "Scenario: Filter by club"
    (let [ps (q/players-by-club db "Flamengo")]
      (is (= 1 (count ps)))
      (is (= "Gabriel Barbosa" (:name (first ps))))))

  (testing "Scenario: Min overall threshold"
    (let [ps (q/players-by-nationality db "Brazil" {:min-overall 85})]
      (is (= 2 (count ps)))
      (is (every? #(>= (:overall %) 85) ps)))))

;; ---- Feature: Formatting ----------------------------------------------

(deftest feature-formatting
  (testing "Scenario: Match formatting is human-readable"
    (let [s (q/format-match (first sample-matches))]
      (is (re-find #"Flamengo" s))
      (is (re-find #"2-1" s))
      (is (re-find #"Brasileirão" s)))))
