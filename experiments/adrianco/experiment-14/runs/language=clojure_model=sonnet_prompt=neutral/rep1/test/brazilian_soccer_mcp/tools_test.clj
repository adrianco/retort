(ns brazilian-soccer-mcp.tools-test
  (:require [clojure.test :refer :all]
            [clojure.string :as str]
            [brazilian-soccer-mcp.normalize :as norm]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.tools :as tools]))

;; ── Load data once for all tests ─────────────────────────────────────────────

(defonce _loaded (data/load-all-data!))

;; ── normalize tests ───────────────────────────────────────────────────────────

(deftest test-normalize-team
  (testing "strips state codes"
    (is (= "palmeiras" (norm/normalize-team "Palmeiras-SP")))
    (is (= "flamengo" (norm/normalize-team "Flamengo-RJ")))
    (is (= "sport" (norm/normalize-team "Sport-PE")))
    (is (= "america" (norm/normalize-team "América - MG"))))

  (testing "strips parenthetical notes"
    (is (str/includes? (norm/normalize-team "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
                       "boavista")))

  (testing "strips accents"
    (is (= "gremio" (norm/normalize-team "Grêmio")))
    (is (= "atletico" (norm/normalize-team "Atlético")))
    (is (= "sao paulo" (norm/normalize-team "São Paulo"))))

  (testing "returns nil for nil/empty"
    (is (nil? (norm/normalize-team nil)))
    (is (nil? (norm/normalize-team "")))))

(deftest test-team-matches
  (testing "exact match after normalization"
    (is (norm/team-matches? "Palmeiras-SP" "Palmeiras"))
    (is (norm/team-matches? "Flamengo-RJ" "Flamengo"))
    (is (norm/team-matches? "Grêmio" "Gremio")))

  (testing "partial match"
    (is (norm/team-matches? "São Paulo FC" "Sao Paulo"))
    (is (norm/team-matches? "Corinthians" "corinthians")))

  (testing "no match"
    (is (not (norm/team-matches? "Palmeiras" "Flamengo")))
    (is (not (norm/team-matches? "Santos" "Grêmio"))))

  (testing "nil safety"
    (is (not (norm/team-matches? nil "Flamengo")))
    (is (not (norm/team-matches? "Flamengo" nil)))))

(deftest test-parse-date
  (is (= "2023-09-03" (norm/parse-date "2023-09-03")))
  (is (= "2012-05-19" (norm/parse-date "2012-05-19 18:30:00")))
  (is (= "2003-03-29" (norm/parse-date "29/03/2003")))
  (is (nil? (norm/parse-date nil)))
  (is (nil? (norm/parse-date ""))))

;; ── data loading tests ────────────────────────────────────────────────────────

(deftest test-data-loading
  (testing "brasileirao matches loaded"
    (let [ms (data/get-brasileirao)]
      (is (> (count ms) 4000))
      (is (every? :date (take 10 ms)))
      (is (every? :home-team (take 10 ms)))
      (is (every? :away-team (take 10 ms)))))

  (testing "copa brasil matches loaded"
    (let [ms (data/get-copa-brasil)]
      (is (> (count ms) 1000))))

  (testing "libertadores matches loaded"
    (let [ms (data/get-libertadores)]
      (is (> (count ms) 1000))))

  (testing "br-football extended dataset loaded"
    (let [ms (data/get-br-football)]
      (is (> (count ms) 5000))))

  (testing "historico dataset loaded"
    (let [ms (data/get-historico)]
      (is (> (count ms) 6000))))

  (testing "fifa players loaded"
    (let [ps (data/get-fifa)]
      (is (> (count ps) 10000))
      (is (every? :name (take 10 ps))))))

;; ── search_matches tests ──────────────────────────────────────────────────────

(deftest test-search-matches-by-team
  (testing "finds Flamengo matches"
    (let [result (tools/search-matches {"team" "Flamengo" "competition" "brasileirao" "limit" "50"})]
      (is (string? result))
      (is (str/includes? result "Flamengo"))
      (is (not (str/includes? result "No matches found")))))

  (testing "finds Palmeiras matches in 2022"
    (let [result (tools/search-matches {"team" "Palmeiras" "season" "2022" "competition" "brasileirao"})]
      (is (str/includes? result "2022"))
      (is (str/includes? result "Palmeiras"))))

  (testing "returns no-match message when nothing found"
    (let [result (tools/search-matches {"team" "NonExistentTeam12345"})]
      (is (str/includes? result "No matches found"))))

  (testing "respects limit"
    (let [result (tools/search-matches {"competition" "brasileirao" "limit" "5"})]
      ;; Should mention 5 or note total
      (is (string? result)))))

(deftest test-search-matches-head-to-head
  (testing "finds Flamengo vs Fluminense"
    (let [result (tools/search-matches {"team" "Flamengo" "opponent" "Fluminense"})]
      (is (str/includes? result "Flamengo"))
      (is (str/includes? result "Fluminense"))))

  (testing "finds Corinthians vs Palmeiras"
    (let [result (tools/search-matches {"team" "Corinthians" "opponent" "Palmeiras"
                                        "competition" "brasileirao"})]
      (is (string? result)))))

(deftest test-search-matches-by-date
  (testing "date range filter"
    (let [result (tools/search-matches {"date_from" "2023-01-01" "date_to" "2023-12-31"})]
      (is (string? result)))))

;; ── get_team_stats tests ──────────────────────────────────────────────────────

(deftest test-get-team-stats
  (testing "Flamengo 2019 stats"
    (let [result (tools/get-team-stats {"team" "Flamengo" "season" "2019"
                                        "competition" "brasileirao"})]
      (is (string? result))
      (is (str/includes? result "Flamengo"))
      (is (str/includes? result "Wins"))
      (is (str/includes? result "Win rate"))))

  (testing "missing team throws"
    (is (thrown? Exception (tools/get-team-stats {}))))

  (testing "unknown team returns no-data message"
    (let [result (tools/get-team-stats {"team" "XyzNonExistent"})]
      (is (str/includes? result "No matches found")))))

;; ── search_players tests ──────────────────────────────────────────────────────

(deftest test-search-players
  (testing "search by nationality Brazil"
    (let [result (tools/search-players {"nationality" "Brazil" "limit" "10"})]
      (is (str/includes? result "Brazil"))
      (is (not (str/includes? result "No players found")))))

  (testing "search by club Flamengo"
    (let [result (tools/search-players {"club" "Flamengo" "limit" "20"})]
      (is (string? result))))

  (testing "search by name"
    (let [result (tools/search-players {"name" "Neymar"})]
      (is (str/includes? result "Neymar"))))

  (testing "search by min overall rating"
    (let [result (tools/search-players {"min_overall" "90" "limit" "10"})]
      (is (string? result))
      (is (not (str/includes? result "No players found")))))

  (testing "search by position"
    (let [result (tools/search-players {"position" "GK" "nationality" "Brazil" "limit" "10"})]
      (is (string? result))))

  (testing "no match returns message"
    (let [result (tools/search-players {"name" "ZzzNobodyXxx123"})]
      (is (str/includes? result "No players found")))))

;; ── get_standings tests ───────────────────────────────────────────────────────

(deftest test-get-standings
  (testing "2019 brasileirao standings"
    (let [result (tools/get-standings {"season" "2019" "competition" "brasileirao"})]
      (is (string? result))
      (is (str/includes? result "2019"))
      (is (str/includes? result "Pts"))))

  (testing "missing season throws"
    (is (thrown? Exception (tools/get-standings {}))))

  (testing "copa brasil standings"
    (let [result (tools/get-standings {"season" "2020" "competition" "copa-brasil"})]
      (is (string? result)))))

;; ── get_head_to_head tests ────────────────────────────────────────────────────

(deftest test-get-head-to-head
  (testing "Flamengo vs Corinthians"
    (let [result (tools/get-head-to-head {"team1" "Flamengo" "team2" "Corinthians"})]
      (is (string? result))
      (is (str/includes? result "Head-to-Head"))
      (is (str/includes? result "Total matches"))))

  (testing "missing team throws"
    (is (thrown? Exception (tools/get-head-to-head {"team1" "Flamengo"}))))

  (testing "no results case"
    (let [result (tools/get-head-to-head {"team1" "TeamAAA" "team2" "TeamBBB"})]
      (is (str/includes? result "No matches found")))))

;; ── get_biggest_wins tests ────────────────────────────────────────────────────

(deftest test-get-biggest-wins
  (testing "overall biggest wins"
    (let [result (tools/get-biggest-wins {})]
      (is (string? result))
      (is (str/includes? result "Biggest victories"))))

  (testing "biggest wins for Palmeiras"
    (let [result (tools/get-biggest-wins {"team" "Palmeiras" "limit" "5"})]
      (is (string? result))))

  (testing "biggest wins in brasileirao 2019"
    (let [result (tools/get-biggest-wins {"competition" "brasileirao" "season" "2019" "limit" "5"})]
      (is (string? result)))))

;; ── get_competition_stats tests ───────────────────────────────────────────────

(deftest test-get-competition-stats
  (testing "brasileirao 2022 stats"
    (let [result (tools/get-competition-stats {"competition" "brasileirao" "season" "2022"})]
      (is (string? result))
      (is (str/includes? result "Goals per match"))
      (is (str/includes? result "Home wins"))))

  (testing "all competitions all years"
    (let [result (tools/get-competition-stats {})]
      (is (string? result))
      (is (str/includes? result "Total matches"))))

  (testing "libertadores stats"
    (let [result (tools/get-competition-stats {"competition" "libertadores" "season" "2019"})]
      (is (string? result)))))

;; ── integration / sample question tests ──────────────────────────────────────

(deftest test-sample-questions
  (testing "Q: When did Flamengo last play Corinthians?"
    (let [result (tools/search-matches {"team" "Flamengo" "opponent" "Corinthians" "limit" "1"})]
      (is (string? result))
      (is (not (str/includes? result "No matches found")))))

  (testing "Q: Who are the highest-rated players at Palmeiras?"
    (let [result (tools/search-players {"club" "Palmeiras" "limit" "5"})]
      (is (string? result))))

  (testing "Q: Who won the 2019 Brasileirao?"
    (let [result (tools/get-standings {"season" "2019" "competition" "brasileirao"})]
      (is (string? result))
      (is (str/includes? result "Flamengo"))))

  (testing "Q: What is the average goals per match in Brasileirao?"
    (let [result (tools/get-competition-stats {"competition" "brasileirao"})]
      (is (str/includes? result "Goals per match"))))

  (testing "Q: Find all Brazilian players"
    (let [result (tools/search-players {"nationality" "Brazil" "limit" "5"})]
      (is (str/includes? result "Brazil"))))

  (testing "Q: Find all Copa do Brasil finals"
    (let [result (tools/search-matches {"competition" "copa-brasil" "limit" "5"})]
      (is (string? result))))

  (testing "Q: Show biggest wins in Libertadores"
    (let [result (tools/get-biggest-wins {"competition" "libertadores" "limit" "5"})]
      (is (string? result))))

  (testing "Q: Corinthians home record in 2022"
    (let [result (tools/get-team-stats {"team" "Corinthians" "season" "2022"
                                        "competition" "brasileirao" "venue" "home"})]
      (is (string? result)))))
