(ns brazilian-soccer.query-test
  "CONTEXT
  =======
  BDD (Given/When/Then) tests for the query layer, mirroring the scenarios in
  TASK.md's Testing Approach section:

    Scenario: Find matches between two teams
    Scenario: Get team statistics
    plus standings, players and statistical-analysis scenarios.

  Historical anchors used as expected values (all verifiable from the data
  and the public record): Flamengo won the 2019 Brasileirão with 90 points
  (28W 6D 4L), Cruzeiro won 2003 with 100, Flamengo won 2009 with 67,
  Palmeiras won 2022 with 81."
  (:require [clojure.test :refer [deftest is testing]]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.query :as query]))

(defn- db [] (data/db))

(deftest find-matches-between-two-teams
  (testing "Given the match data is loaded
            When I search for matches between \"Flamengo\" and \"Fluminense\"
            Then I should receive a list of matches
            And each match should have date, scores, and competition"
    (let [matches (query/search-matches (db) {:team "Flamengo" :opponent "Fluminense"})]
      (is (seq matches))
      (is (every? :date matches))
      (is (every? :competition matches))
      (is (every? #(and (contains? % :home-goals) (contains? % :away-goals)) matches))
      (testing "And every match involves both clubs"
        (let [fla (data/canonical-team "Flamengo")
              flu (data/canonical-team "Fluminense")]
          (is (every? #(= #{fla flu} #{(:home %) (:away %)}) matches)))))))

(deftest search-matches-filters
  (testing "Given the match data is loaded
            When I search with team/season/competition/date filters
            Then only matching matches are returned"
    (let [palmeiras-2023 (query/search-matches (db) {:team "Palmeiras" :season 2023})]
      (is (seq palmeiras-2023) "Palmeiras played matches in 2023")
      (is (every? #(= 2023 (:season %)) palmeiras-2023)))
    (let [lib (query/search-matches (db) {:competition "Libertadores" :season 2019})]
      (is (seq lib))
      (is (every? #(= "Copa Libertadores" (:competition %)) lib)))
    (let [finals (query/search-matches (db) {:competition "Libertadores" :stage "final"})]
      (is (seq finals) "Libertadores finals are findable by stage"))
    (let [window (query/search-matches (db) {:team "Santos"
                                             :date-from "2019-01-01"
                                             :date-to "2019-12-31"})]
      (is (seq window))
      (is (every? #(= 2019 (.getYear ^java.time.LocalDate (:date %))) window)))))

(deftest get-team-statistics
  (testing "Given the match data is loaded
            When I request statistics for \"Palmeiras\" in season \"2023\"
            Then I should receive wins, losses, draws, and goals"
    (let [r (query/team-record (db) "Palmeiras" {:season 2023})]
      (is (pos? (:played r)))
      (is (= (:played r) (+ (:wins r) (:draws r) (:losses r))))
      (is (number? (:goals-for r)))
      (is (number? (:goals-against r)))
      (is (<= 0.0 (:win-rate r) 1.0)))))

(deftest home-venue-statistics
  (testing "Given the match data is loaded
            When I request Corinthians' home record for the 2022 Brasileirão
            Then I get their real 19-match home campaign"
    (let [r (query/team-record (db) "Corinthians"
                               {:season 2022 :competition "Brasileirão Série A"
                                :venue "home"})]
      (is (= 19 (:played r)))
      (is (= 12 (:wins r)))
      (is (= 4 (:draws r)))
      (is (= 3 (:losses r)))
      (is (= 24 (:goals-for r)))
      (is (= 11 (:goals-against r))))))

(deftest head-to-head-summary
  (testing "Given the match data is loaded
            When I compare Flamengo and Fluminense head-to-head
            Then wins + draws account for every scored match"
    (let [h (query/head-to-head (db) "Flamengo" "Fluminense")]
      (is (pos? (:played h)))
      (is (= (:played h)
             (+ (:team1-wins h) (:team2-wins h) (:draws h))))
      (is (pos? (:team1-goals h)))
      (is (pos? (:team2-goals h))))))

(deftest league-standings-2019
  (testing "Given the match data is loaded
            When I calculate the 2019 Brasileirão standings
            Then Flamengo are champions with 90 points (28W 6D 4L)"
    (let [table (query/standings (db) 2019 nil)
          champion (first table)]
      (is (= 20 (count table)))
      (is (= (data/canonical-team "Flamengo") (:team champion)))
      (is (= 90 (:points champion)))
      (is (= 28 (:wins champion)))
      (is (= 6 (:draws champion)))
      (is (= 4 (:losses champion)))
      (is (= 86 (:goals-for champion)))
      (is (= 37 (:goals-against champion)))
      (testing "And every team played 38 matches"
        (is (every? #(= 38 (:played %)) table))))))

(deftest league-standings-other-seasons
  (testing "Given seasons covered by one, two or three overlapping files
            When standings are calculated
            Then the real champion tops each table"
    (doseq [[season club points] [[2003 "Cruzeiro" 100]
                                  [2009 "Flamengo" 67]
                                  [2012 "Fluminense" 77]
                                  [2016 "Palmeiras" 80]
                                  [2021 "Atlético Mineiro" 84]
                                  [2022 "Palmeiras" 81]]]
      (let [champion (first (query/standings (db) season nil))]
        (is (= (data/canonical-team club) (:team champion)) (str season " champion"))
        (is (= points (:points champion)) (str season " points"))))))

(deftest statistical-analysis
  (testing "Given the match data is loaded
            When I compute aggregate competition statistics
            Then averages and rates are plausible and consistent"
    (let [s (query/competition-stats (db) {:competition "Brasileirão Série A"})]
      (is (> (:matches s) 8000))
      (is (< 2.0 (:avg-goals s) 3.0))
      (is (> (:home-win-rate s) (:away-win-rate s)) "home advantage exists")
      (is (< 0.99 (+ (:home-win-rate s) (:draw-rate s) (:away-win-rate s)) 1.01)))))

(deftest biggest-wins-analysis
  (testing "Given the match data is loaded
            When I ask for the biggest wins
            Then they come back sorted by margin descending"
    (let [wins (query/biggest-wins (db) {:limit 10})]
      (is (= 10 (count wins)))
      (is (apply >= (map :margin wins)))
      (is (>= (:margin (first wins)) 6)))))

(deftest player-search
  (testing "Given the FIFA player data is loaded
            When I search by name, nationality, club and rating
            Then the right players are returned"
    (let [[neymar] (query/search-players (db) {:name "Neymar"})]
      (is (some? neymar))
      (is (= "Brazil" (:nationality neymar)))
      (is (= 92 (:overall neymar))))
    (testing "And accent-insensitive club search works"
      (let [gremio (query/search-players (db) {:club "Gremio"})]
        (is (seq gremio))
        (is (every? #(= "Grêmio" (:club %)) gremio))))
    (testing "And Brazilians can be filtered and ranked"
      (let [top (query/top-players (db) {:nationality "Brazil"} 10)]
        (is (= 10 (count top)))
        (is (= "Neymar Jr" (:name (first top))))
        (is (every? #(= "Brazil" (:nationality %)) top))
        (is (apply >= (map :overall top)))))
    (testing "And position + rating filters compose"
      (let [gks (query/search-players (db) {:nationality "Brazil" :position "GK"
                                            :min-overall 85})]
        (is (seq gks))
        (is (every? #(and (= "GK" (:position %)) (>= (:overall %) 85)) gks))))))

(deftest cross-file-club-and-match-queries
  (testing "Given player data and match data
            When I look at a club present in both (cross-file query)
            Then I can get its squad and its match record"
    (let [squad (query/search-players (db) {:club "Fluminense"})
          record (query/team-record (db) "Fluminense" {:season 2012})]
      (is (seq squad))
      (is (pos? (:played record)))
      (is (pos? (:wins record))))))

(deftest club-player-summary-test
  (testing "Given the FIFA player data
            When I summarize Brazilian players per club
            Then clubs come with counts and average ratings"
    (let [clubs (query/club-player-summary (db) {:nationality "Brazil" :min-players 3})]
      (is (seq clubs))
      (is (every? #(>= (:players %) 3) clubs))
      (is (every? #(< 40 (:avg-overall %) 100) clubs)))))
