(ns brazilian-soccer-mcp.acceptance-test
  "Executable acceptance tests for the Brazilian Soccer MCP server.
   Tests exercise the system through its public MCP tool interface only.
   Each test starts from a clean, freshly-loaded data state."
  (:require [clojure.test :refer [deftest is testing use-fixtures]]
            [brazilian-soccer-mcp.tools :as tools]
            [brazilian-soccer-mcp.data :as data]))

;; ---------------------------------------------------------------------------
;; Test fixture: load data once per namespace
;; ---------------------------------------------------------------------------

(def ^:private test-data-path
  (-> (java.io.File. ".")
      (.getCanonicalPath)
      (str "/../data/kaggle")))

(defonce ^:private loaded-data
  (delay (data/load-all-data test-data-path)))

(defn- get-data []
  @loaded-data)

;; ---------------------------------------------------------------------------
;; 1. Match Queries
;; ---------------------------------------------------------------------------

(deftest find-matches-by-two-teams
  (testing "Can find all matches between Flamengo and Fluminense"
    (let [result (tools/find-matches (get-data)
                                     {:team1 "Flamengo" :team2 "Fluminense"})]
      (is (map? result))
      (is (contains? result :matches))
      (is (seq (:matches result)) "Should find at least one Fla-Flu match")
      (is (every? #(let [home (str (:home-team %))
                         away (str (:away-team %))]
                     (or (and (re-find #"(?i)flamengo" home)
                              (re-find #"(?i)fluminense" away))
                         (and (re-find #"(?i)fluminense" home)
                              (re-find #"(?i)flamengo" away))))
                  (:matches result))
          "All matches should involve both Flamengo and Fluminense")
      (is (every? #(and (contains? % :home-team)
                        (contains? % :away-team)
                        (contains? % :home-goal)
                        (contains? % :away-goal)
                        (contains? % :date)
                        (contains? % :competition))
                  (:matches result))
          "Each match should have required fields"))))

(deftest find-matches-by-single-team
  (testing "Can find all Palmeiras matches in 2023"
    (let [result (tools/find-matches (get-data)
                                     {:team "Palmeiras" :season 2023})]
      (is (map? result))
      (is (seq (:matches result)) "Should find Palmeiras 2023 matches")
      (is (every? #(or (re-find #"(?i)palmeiras" (str (:home-team %)))
                       (re-find #"(?i)palmeiras" (str (:away-team %))))
                  (:matches result))
          "All matches should involve Palmeiras")
      (is (every? #(= (str (:season %)) "2023") (:matches result))
          "All matches should be from 2023"))))

(deftest find-matches-by-competition
  (testing "Can find Copa do Brasil matches"
    (let [result (tools/find-matches (get-data)
                                     {:competition "copa-do-brasil" :season 2023})]
      (is (seq (:matches result)) "Should find Copa do Brasil 2023 matches")
      (is (every? #(re-find #"(?i)copa|brasil|cup" (str (:competition %)))
                  (:matches result))
          "All matches should be from Copa do Brasil")))

  (testing "Can find Brasileirao matches"
    (let [result (tools/find-matches (get-data)
                                     {:competition "brasileirao" :season 2022})]
      (is (seq (:matches result)) "Should find Brasileirao 2022 matches")
      (is (> (count (:matches result)) 100)
          "Should find many Brasileirao matches")))

  (testing "Can find Copa Libertadores matches"
    (let [result (tools/find-matches (get-data)
                                     {:competition "libertadores" :season 2019})]
      (is (seq (:matches result)) "Should find Libertadores 2019 matches"))))

(deftest find-matches-by-date-range
  (testing "Can find matches within a date range"
    (let [result (tools/find-matches (get-data)
                                     {:date-from "2023-01-01" :date-to "2023-06-30"})]
      (is (seq (:matches result)) "Should find matches in first half of 2023")
      (is (every? #(let [d (str (:date %))]
                     (and (>= (compare d "2023-01-01") 0)
                          (<= (compare d "2023-06-30") 0)))
                  (:matches result))
          "All matches should be within the date range"))))

;; ---------------------------------------------------------------------------
;; 2. Team Queries
;; ---------------------------------------------------------------------------

(deftest get-team-home-record
  (testing "Can retrieve Corinthians home record in 2022 Brasileirao"
    (let [result (tools/get-team-stats (get-data)
                                       {:team "Corinthians"
                                        :competition "brasileirao"
                                        :season 2022
                                        :venue "home"})]
      (is (map? result))
      (is (contains? result :team))
      (is (contains? result :wins))
      (is (contains? result :draws))
      (is (contains? result :losses))
      (is (contains? result :goals-for))
      (is (contains? result :goals-against))
      (is (contains? result :matches-played))
      (is (= (+ (:wins result) (:draws result) (:losses result))
             (:matches-played result))
          "W+D+L should equal matches played")
      (is (pos? (:matches-played result))
          "Should have played some home matches"))))

(deftest get-team-overall-stats
  (testing "Can retrieve overall team statistics"
    (let [result (tools/get-team-stats (get-data)
                                       {:team "Flamengo"
                                        :competition "brasileirao"
                                        :season 2019})]
      (is (pos? (:matches-played result)))
      (is (number? (:win-rate result)))
      (is (<= 0.0 (:win-rate result) 1.0)
          "Win rate should be between 0 and 1"))))

;; ---------------------------------------------------------------------------
;; 3. Player Queries
;; ---------------------------------------------------------------------------

(deftest find-players-by-nationality
  (testing "Can find Brazilian players in the dataset"
    (let [result (tools/find-players (get-data)
                                     {:nationality "Brazil" :limit 500})]
      (is (map? result))
      (is (contains? result :players))
      (is (seq (:players result)) "Should find Brazilian players")
      (is (> (count (:players result)) 100)
          "Should find many Brazilian players")
      (is (every? #(contains? % :name) (:players result))
          "Each player should have a name")
      (is (every? #(contains? % :overall) (:players result))
          "Each player should have an overall rating")
      (is (every? #(contains? % :club) (:players result))
          "Each player should have a club"))))

(deftest find-players-by-name
  (testing "Can search players by name"
    (let [result (tools/find-players (get-data)
                                     {:name "Gabriel"})]
      (is (seq (:players result)) "Should find players named Gabriel")
      (is (every? #(re-find #"(?i)gabriel" (str (:name %)))
                  (:players result))
          "All results should have 'Gabriel' in the name"))))

(deftest find-players-by-club
  (testing "Can find players at Santos FC (has entries in FIFA data)"
    (let [result (tools/find-players (get-data)
                                     {:club "Santos"})]
      (is (seq (:players result)) "Should find Santos players")
      (is (every? #(re-find #"(?i)santos" (str (:club %)))
                  (:players result))
          "All results should be Santos players")))

  (testing "Can find players by position and club"
    (let [result (tools/find-players (get-data)
                                     {:club "Santos" :position "ST"})]
      (is (every? #(re-find #"(?i)santos" (str (:club %)))
                  (:players result))
          "All results should be Santos players"))))

(deftest find-top-rated-players
  (testing "Can find top-rated Brazilian players sorted by overall"
    (let [result (tools/find-players (get-data)
                                     {:nationality "Brazil"
                                      :min-overall 85
                                      :sort-key "overall"
                                      :limit 10})]
      (is (<= (count (:players result)) 10) "Should respect limit")
      (is (every? #(>= (:overall %) 85) (:players result))
          "All players should meet min-overall threshold")
      (let [ratings (map :overall (:players result))]
        (is (= ratings (sort > ratings))
            "Players should be sorted by overall rating descending")))))

;; ---------------------------------------------------------------------------
;; 4. Head-to-Head Queries
;; ---------------------------------------------------------------------------

(deftest get-head-to-head-record
  (testing "Can get head-to-head record between two teams"
    (let [result (tools/get-head-to-head (get-data)
                                         {:team1 "Flamengo"
                                          :team2 "Corinthians"})]
      (is (map? result))
      (is (contains? result :team1))
      (is (contains? result :team2))
      (is (contains? result :team1-wins))
      (is (contains? result :team2-wins))
      (is (contains? result :draws))
      (is (contains? result :total-matches))
      (is (= (+ (:team1-wins result) (:team2-wins result) (:draws result))
             (:total-matches result))
          "W1+W2+Draws should equal total matches")
      (is (pos? (:total-matches result))
          "Should find matches between these historic rivals"))))

;; ---------------------------------------------------------------------------
;; 5. Competition Standings
;; ---------------------------------------------------------------------------

(deftest get-brasileirao-standings
  (testing "Can calculate 2019 Brasileirao standings"
    (let [result (tools/get-standings (get-data)
                                      {:season 2019
                                       :competition "brasileirao"})]
      (is (map? result))
      (is (contains? result :standings))
      (is (seq (:standings result)) "Should have standings entries")
      (let [standings (:standings result)]
        (is (every? #(and (contains? % :team)
                          (contains? % :points)
                          (contains? % :wins)
                          (contains? % :draws)
                          (contains? % :losses)
                          (contains? % :goals-for)
                          (contains? % :goals-against)
                          (contains? % :position))
                    standings)
            "Each standing entry should have required fields")
        (let [points (map :points standings)]
          (is (= points (sort > points))
              "Standings should be sorted by points descending"))
        (is (= 1 (:position (first standings)))
            "First team should have position 1")
        (is (re-find #"(?i)flamengo" (str (:team (first standings))))
            "Flamengo won the 2019 Brasileirao")))))

(deftest get-historical-standings
  (testing "Can calculate standings from historical data"
    (let [result (tools/get-standings (get-data)
                                      {:season 2003
                                       :competition "brasileirao"})]
      (is (seq (:standings result))
          "Should compute standings for 2003 season"))))

;; ---------------------------------------------------------------------------
;; 6. Statistical Analysis
;; ---------------------------------------------------------------------------

(deftest get-biggest-wins
  (testing "Can find biggest victories in the dataset"
    (let [result (tools/get-statistics (get-data)
                                       {:stat-type "biggest-wins"
                                        :limit 10})]
      (is (map? result))
      (is (contains? result :results))
      (let [wins (:results result)]
        (is (<= (count wins) 10) "Should respect limit")
        (is (seq wins) "Should find some big wins")
        (let [margins (map #(Math/abs (- (:home-goal %) (:away-goal %))) wins)]
          (is (= margins (sort > margins))
              "Wins should be sorted by margin descending"))))))

(deftest get-average-goals
  (testing "Can calculate average goals per match for Brasileirao"
    (let [result (tools/get-statistics (get-data)
                                       {:stat-type "goals-per-match"
                                        :competition "brasileirao"})]
      (is (map? result))
      (is (contains? result :average-goals-per-match))
      (is (number? (:average-goals-per-match result)))
      (is (< 1.0 (:average-goals-per-match result) 6.0)
          "Average goals should be a realistic value"))))

(deftest get-home-away-record
  (testing "Can calculate home vs away win rates"
    (let [result (tools/get-statistics (get-data)
                                       {:stat-type "home-away-record"
                                        :competition "brasileirao"})]
      (is (map? result))
      (is (contains? result :home-win-rate))
      (is (contains? result :away-win-rate))
      (is (contains? result :draw-rate))
      (let [total (+ (:home-win-rate result)
                     (:away-win-rate result)
                     (:draw-rate result))]
        (is (< (Math/abs (- total 1.0)) 0.001)
            "Win rates should sum to 1.0")))))

(deftest get-top-scoring-teams
  (testing "Can find the top scoring teams in a season"
    (let [result (tools/get-statistics (get-data)
                                       {:stat-type "top-scoring-teams"
                                        :competition "brasileirao"
                                        :season 2023
                                        :limit 5})]
      (is (contains? result :results))
      (let [teams (:results result)]
        (is (<= (count teams) 5) "Should respect limit")
        (is (every? #(and (contains? % :team)
                          (contains? % :goals))
                    teams)
            "Each entry should have team and goals")
        (let [goals (map :goals teams)]
          (is (= goals (sort > goals))
              "Teams should be sorted by goals descending"))))))

;; ---------------------------------------------------------------------------
;; 7. Data coverage — all 6 CSV files load and are queryable
;; ---------------------------------------------------------------------------

(deftest all-data-files-loaded
  (testing "All 6 CSV datasets are loaded and have records"
    (let [d (get-data)]
      (is (seq (:brasileirao-matches d))
          "Brasileirao matches should be loaded")
      (is (seq (:cup-matches d))
          "Copa do Brasil matches should be loaded")
      (is (seq (:libertadores-matches d))
          "Libertadores matches should be loaded")
      (is (seq (:br-football d))
          "BR Football Dataset should be loaded")
      (is (seq (:historical-brasileirao d))
          "Historical Brasileirao (2003-2019) should be loaded")
      (is (seq (:fifa-players d))
          "FIFA player data should be loaded")
      (is (>= (count (:brasileirao-matches d)) 4000)
          "Should have ~4180 Brasileirao matches")
      (is (>= (count (:cup-matches d)) 1300)
          "Should have ~1337 Cup matches")
      (is (>= (count (:libertadores-matches d)) 1200)
          "Should have ~1255 Libertadores matches")
      (is (>= (count (:br-football d)) 10000)
          "Should have ~10296 BR Football records")
      (is (>= (count (:historical-brasileirao d)) 6800)
          "Should have ~6886 historical matches")
      (is (>= (count (:fifa-players d)) 18000)
          "Should have ~18207 FIFA players"))))

(deftest team-name-normalization
  (testing "Team name variations are handled correctly"
    (let [result1 (tools/find-matches (get-data) {:team "Palmeiras"})
          result2 (tools/find-matches (get-data) {:team "Palmeiras-SP"})]
      (is (seq (:matches result1)) "Should find Palmeiras by short name")
      (is (seq (:matches result2)) "Should find Palmeiras by name with state suffix")
      (is (= (count (:matches result1)) (count (:matches result2)))
          "Both name forms should return the same matches"))))

(deftest cross-file-player-and-match-query
  (testing "Can correlate player data with match data (Brazilian players + Flamengo matches)"
    (let [players (tools/find-players (get-data) {:nationality "Brazil" :limit 20})
          matches (tools/find-matches (get-data) {:team "Flamengo" :season 2019})]
      (is (seq (:players players)) "Should find Brazilian players")
      (is (seq (:matches matches)) "Should find Flamengo 2019 matches")
      (is (number? (count (:players players))))
      (is (number? (count (:matches matches)))))))
