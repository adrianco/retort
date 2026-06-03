(ns soccer-mcp.queries-test
  "BDD-style tests for the query layer. Uses both small in-memory fixtures
   (for deterministic assertions) and the real bundled CSVs (for smoke
   coverage of the loaded shape)."
  (:require [clojure.test :refer [deftest is testing]]
            [soccer-mcp.data :as data]
            [soccer-mcp.queries :as q]))

;; ----------------------------------------------------------------------------
;; Deterministic fixture: a tiny league with two teams, three matches.

(def fixture
  {:matches
   [{:competition :brasileirao :date "2023-05-28" :datetime "2023-05-28"
     :home "Fluminense" :away "Flamengo"
     :home-goal 1 :away-goal 0 :season 2023 :round "8"
     :source-file "Brasileirao_Matches.csv"}
    {:competition :brasileirao :date "2023-09-03" :datetime "2023-09-03"
     :home "Flamengo" :away "Fluminense"
     :home-goal 2 :away-goal 1 :season 2023 :round "22"
     :source-file "Brasileirao_Matches.csv"}
    {:competition :copa-do-brasil :date "2023-07-12" :datetime "2023-07-12"
     :home "Palmeiras" :away "Flamengo"
     :home-goal 3 :away-goal 3 :season 2023 :round "QF"
     :source-file "Brazilian_Cup_Matches.csv"}
    {:competition :brasileirao :date "2023-10-01" :datetime "2023-10-01"
     :home "Palmeiras" :away "Fluminense"
     :home-goal 0 :away-goal 5 :season 2023 :round "30"
     :source-file "Brasileirao_Matches.csv"}
    {:competition :brasileirao :date "2022-08-08" :datetime "2022-08-08"
     :home "Flamengo" :away "Palmeiras"
     :home-goal 2 :away-goal 0 :season 2022 :round "12"
     :source-file "Brasileirao_Matches.csv"}]
   :players
   [{:id 1 :name "Neymar Jr"          :nationality "Brazil"    :overall 92
     :potential 92 :club "Paris SG"     :position "LW"   :age 31}
    {:id 2 :name "Gabriel Barbosa"    :nationality "Brazil"    :overall 83
     :potential 87 :club "Flamengo"     :position "ST"   :age 26}
    {:id 3 :name "Endrick"            :nationality "Brazil"    :overall 70
     :potential 90 :club "Palmeiras"    :position "ST"   :age 17}
    {:id 4 :name "Lionel Messi"       :nationality "Argentina" :overall 94
     :potential 94 :club "Inter Miami"  :position "RW"   :age 36}
    {:id 5 :name "Marcos Felipe"      :nationality "Brazil"    :overall 75
     :potential 80 :club "Fluminense"   :position "GK"   :age 27}]})

(deftest match-search
  (testing "Feature: Match queries"
    (testing "Scenario: Find matches between two teams"
      ;; Given the match data is loaded
      ;; When I search for matches between "Flamengo" and "Fluminense"
      ;; Then I should receive only matches involving both teams
      (let [ms (q/find-matches fixture
                               {:team-a "Flamengo" :team-b "Fluminense"})]
        (is (= 2 (count ms)))
        (is (every? #(and (#{"Flamengo" "Fluminense"} (:home %))
                          (#{"Flamengo" "Fluminense"} (:away %))) ms))))

    (testing "Scenario: Filter by team and season"
      (let [ms (q/find-matches fixture {:team "Palmeiras" :season 2023})]
        (is (= 2 (count ms)))
        (is (every? #(= 2023 (:season %)) ms))))

    (testing "Scenario: Filter by competition"
      (let [ms (q/find-matches fixture {:competition "copa-do-brasil"})]
        (is (= 1 (count ms)))
        (is (= :copa-do-brasil (-> ms first :competition)))))

    (testing "Scenario: Filter by date range"
      (let [ms (q/find-matches fixture
                               {:from "2023-06-01" :to "2023-09-30"})]
        (is (= 2 (count ms)))
        (is (every? #(and (>= (compare (:date %) "2023-06-01") 0)
                          (<= (compare (:date %) "2023-09-30") 0)) ms))))

    (testing "Scenario: Side filter restricts to home or away"
      (let [home (q/find-matches fixture {:team "Flamengo" :side "home"})
            away (q/find-matches fixture {:team "Flamengo" :side "away"})]
        (is (every? #(= "Flamengo" (:home %)) home))
        (is (every? #(= "Flamengo" (:away %)) away))))))

(deftest team-statistics
  (testing "Feature: Team statistics"
    (testing "Scenario: Get a team's W/D/L and goals"
      ;; Given the match data is loaded
      ;; When I request statistics for "Flamengo" across all comps
      ;; Then the totals reflect every match Flamengo played
      (let [s (q/team-stats fixture {:team "Flamengo"})]
        (is (= 4 (:played s)))         ;; in fixture Flamengo played 4 times
        (is (= 2 (:wins s)))           ;; 2023-09-03 vs Flu, 2022-08-08 vs Pal
        (is (= 1 (:draws s)))          ;; 2023-07-12 vs Pal 3-3
        (is (= 1 (:losses s)))         ;; 2023-05-28 vs Flu
        (is (= 7 (:points s)))         ;; 2*3 + 1
        ;; Goals for: 0+2+3+2 = 7, against: 1+1+3+0 = 5, diff = +2
        (is (= 7 (:goals-for s)))
        (is (= 5 (:goals-against s)))
        (is (= 2 (:goal-diff s)))))

    (testing "Scenario: Side filter restricts the team-stats"
      (let [s (q/team-stats fixture {:team "Flamengo" :side "home"})]
        (is (every? pos? [(:played s)]))
        (is (= 2 (:played s))))) ;; Flamengo was home in 2 fixture matches

    (testing "Scenario: Competition + season filter"
      (let [s (q/team-stats fixture
                            {:team "Palmeiras"
                             :competition "brasileirao"
                             :season 2023})]
        (is (= 1 (:played s))) ;; only the 0-5 loss to Fluminense
        (is (= 1 (:losses s)))
        (is (= 0 (:wins s)))
        (is (= 0 (:draws s)))))))

(deftest head-to-head-record
  (testing "Feature: Head-to-head"
    (testing "Scenario: Flamengo vs Fluminense in fixture"
      ;; In the fixture: Fla 2-1 Flu (Fla win), Flu 1-0 Fla (Flu win)
      (let [h (q/head-to-head fixture
                              {:team-a "Flamengo" :team-b "Fluminense"})]
        (is (= 2 (:matches h)))
        (is (= 1 (:a-wins h)))
        (is (= 1 (:b-wins h)))
        (is (= 0 (:draws h)))
        (is (= 2 (:a-goals h))) ;; 2 + 0 from Fla side
        (is (= 2 (:b-goals h))))))) ;; 1 + 1 from Flu side

(deftest standings-calculation
  (testing "Feature: Standings"
    (testing "Scenario: Brasileirão 2023 table in fixture"
      ;; In the fixture, the 2023 Brasileirão matches are:
      ;;   Flu 1-0 Fla, Fla 2-1 Flu, Pal 0-5 Flu
      ;; Expected: Fluminense 6pts/+5, Flamengo 3pts/0, Palmeiras 0/-5
      (let [rows (q/standings fixture
                              {:competition "brasileirao" :season 2023})]
        (is (= ["Fluminense" "Flamengo" "Palmeiras"]
               (mapv :team rows)))
        (is (= 6 (-> rows first :points)))
        (is (= 0 (-> rows last :points)))))))

(deftest biggest-wins-rank
  (testing "Feature: Biggest victories"
    (testing "Scenario: Rank by goal difference"
      (let [bs (q/biggest-wins fixture {:n 3})]
        (is (= 3 (count bs)))
        ;; First match should be the 5-goal margin
        (is (= 5 (Math/abs
                  (long (- (:home-goal (first bs))
                           (:away-goal (first bs)))))))))))

(deftest averages-and-rates
  (testing "Feature: League averages"
    (testing "Scenario: average goals per match across fixture"
      (let [{:keys [matches goals avg]} (q/average-goals fixture {})]
        (is (= 5 matches))
        ;; 1 + 3 + 6 + 5 + 2 = 17 goals
        (is (= 17 goals))
        (is (< 3.39 avg 3.41))))

    (testing "Scenario: home-win rate across fixture"
      (let [{:keys [matches home-wins rate]} (q/home-win-rate fixture {})]
        (is (= 5 matches))
        ;; Home wins: Flu 1-0 Fla, Fla 2-1 Flu, Fla 2-0 Pal => 3 of 5
        (is (= 3 home-wins))
        (is (< 0.59 rate 0.61))))))

(deftest player-search
  (testing "Feature: Player queries"
    (testing "Scenario: Find a player by name"
      (let [ps (q/find-players fixture {:name "gabriel"})]
        (is (= 1 (count ps)))
        (is (= "Gabriel Barbosa" (-> ps first :name)))))

    (testing "Scenario: All Brazilian players sorted by overall"
      (let [ps (q/find-players fixture {:nationality "Brazil"})]
        (is (= 4 (count ps)))
        (is (= "Neymar Jr" (-> ps first :name))) ;; highest overall
        (is (= [92 83 75 70] (mapv :overall ps)))))

    (testing "Scenario: Filter by club and position"
      (let [ps (q/find-players fixture
                               {:club "Flamengo" :position "ST"})]
        (is (= 1 (count ps)))
        (is (= "Gabriel Barbosa" (-> ps first :name)))))

    (testing "Scenario: Filter by minimum overall"
      (let [ps (q/find-players fixture {:min-overall 90})]
        (is (= 2 (count ps)))
        (is (every? #(>= (:overall %) 90) ps))))

    (testing "Scenario: Players grouped by club"
      (let [rows (q/players-by-club fixture {:nationality "Brazil"})]
        (is (every? #(contains? % :club) rows))
        ;; Flamengo, Palmeiras, Fluminense, Paris SG each have 1 Brazilian
        (is (= 4 (count rows)))))))

;; ----------------------------------------------------------------------------
;; Smoke tests against the real bundled CSVs.

(def ^:private real-dataset (delay (data/load-all "data/kaggle")))

(deftest real-dataset-smoke
  (testing "Feature: queries work on the real bundled data"
    (let [ds @real-dataset]
      (testing "Scenario: find at least one Flamengo match"
        (let [ms (q/find-matches ds {:team "Flamengo" :limit 10})]
          (is (pos? (count ms)))
          (is (every? #(or (data/team-matches? (:home %) "Flamengo")
                           (data/team-matches? (:away %) "Flamengo")) ms))))

      (testing "Scenario: at least one Brazilian player exists"
        (let [ps (q/find-players ds {:nationality "Brazil" :limit 5})]
          (is (pos? (count ps)))
          (is (every? #(= "Brazil" (:nationality %)) ps))))

      (testing "Scenario: league averages are non-trivial"
        (let [{:keys [matches avg]} (q/average-goals ds {})]
          (is (pos? matches))
          (is (< 1.0 avg 5.0)))))))
