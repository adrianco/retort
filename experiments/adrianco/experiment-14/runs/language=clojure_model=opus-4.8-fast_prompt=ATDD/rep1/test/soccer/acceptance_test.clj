(ns soccer.acceptance-test
  "Executable acceptance specification for the Brazilian Soccer MCP server.

   Every scenario is written from the perspective of an external MCP client.
   It boots a running-but-empty server over its own private dataset, then
   exercises the System Under Test *only* through the MCP protocol (tools/list
   and tools/call).  Assertions are expressed in the language of the problem
   domain — matches, head-to-head records, standings, players — and never
   reach into implementation internals."
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.string :as str]
            [soccer.test-helpers :as h]))

(defn fresh-server []
  (h/new-server (h/make-fixture-dir!)))

;; ---------------------------------------------------------------------------
;; Protocol surface
;; ---------------------------------------------------------------------------

(deftest server-advertises-its-soccer-tools
  (testing "an MCP client discovers tools covering every required capability"
    (let [srv   (fresh-server)
          tools (h/list-tools srv)]
      (is (contains? tools "find_matches"))
      (is (contains? tools "team_stats"))
      (is (contains? tools "compare_teams"))
      (is (contains? tools "search_players"))
      (is (contains? tools "competition_standings"))
      (is (contains? tools "competition_stats")))))

(deftest unknown-tool-is-reported-as-an-error
  (testing "calling a tool the server does not provide yields a JSON-RPC error"
    (let [srv  (fresh-server)
          resp (h/call-tool-raw srv "teleport" {})]
      (is (some? (:error resp)))
      (is (nil? (:result resp))))))

;; ---------------------------------------------------------------------------
;; 1. Match queries
;; ---------------------------------------------------------------------------

(deftest find-all-matches-between-two-teams
  (testing "find matches between Flamengo and Fluminense with a head-to-head"
    (let [srv (fresh-server)
          ans (h/call-tool srv "find_matches" {:team "Flamengo" :opponent "Fluminense"})]
      ;; Exactly the two Fla-Flu meetings in the dataset, in either direction.
      (is (str/includes? ans "Flamengo"))
      (is (str/includes? ans "Fluminense"))
      (is (str/includes? ans "2019-05-12"))
      (is (str/includes? ans "2019-09-03"))
      ;; ...and not an unrelated fixture.
      (is (not (str/includes? ans "Corinthians")))
      ;; Head-to-head: Flamengo won both meetings.
      (is (re-find #"Flamengo.*2 win" ans)))))

(deftest find-matches-a-team-played-in-a-season
  (testing "list every match Palmeiras played in the 2019 season"
    (let [srv (fresh-server)
          ans (h/call-tool srv "find_matches" {:team "Palmeiras" :season 2019})]
      ;; Palmeiras played four matches in the fixture season.
      (is (= 4 (count (re-seq #"Palmeiras" ans))))
      (is (str/includes? ans "Corinthians"))
      (is (str/includes? ans "Flamengo"))
      (is (str/includes? ans "Santos")))))

(deftest find-matches-can-be-restricted-by-competition
  (testing "Copa do Brasil filter returns only cup matches, not league ones"
    (let [srv (fresh-server)
          ans (h/call-tool srv "find_matches" {:competition "Copa do Brasil"})]
      (is (str/includes? ans "Internacional"))
      (is (not (str/includes? ans "Corinthians"))))))

;; ---------------------------------------------------------------------------
;; 2. Team queries
;; ---------------------------------------------------------------------------

(deftest team-home-record-for-a-season
  (testing "Corinthians' home record in 2019 is computed from match results"
    (let [srv (fresh-server)
          ans (h/call-tool srv "team_stats"
                           {:team "Corinthians" :season 2019 :venue "home"})]
      ;; Corinthians played 3 home matches: 2W 1D 0L, GF 3, GA 1.
      (is (re-find #"(?i)matches:?\s*3" ans))
      (is (re-find #"(?i)wins:?\s*2" ans))
      (is (re-find #"(?i)draws:?\s*1" ans))
      (is (re-find #"(?i)losses:?\s*0" ans))
      (is (re-find #"(?i)(goals for|for):?\s*3" ans))
      (is (re-find #"(?i)(goals against|against):?\s*1" ans))
      (is (str/includes? ans "66.7")))))

(deftest team-name-variations-are-normalized
  (testing "querying the bare name matches rows stored with a state suffix"
    (let [srv      (fresh-server)
          bare     (h/call-tool srv "team_stats" {:team "Flamengo"})
          suffixed (h/call-tool srv "team_stats" {:team "Flamengo-RJ"})]
      ;; Flamengo played 5 matches overall (4W 1D 0L) regardless of how named.
      (is (re-find #"(?i)matches:?\s*5" bare))
      (is (re-find #"(?i)matches:?\s*5" suffixed))
      (is (re-find #"(?i)wins:?\s*4" bare)))))

;; ---------------------------------------------------------------------------
;; Head-to-head comparison
;; ---------------------------------------------------------------------------

(deftest compare-two-teams-head-to-head
  (testing "Palmeiras vs Santos head-to-head record across the dataset"
    (let [srv (fresh-server)
          ans (h/call-tool srv "compare_teams" {:team1 "Palmeiras" :team2 "Santos"})]
      ;; Two meetings: Palmeiras 3-0 Santos (Pal win) and Santos 1-1 Palmeiras (draw).
      (is (re-find #"Palmeiras.*1 win" ans))
      (is (re-find #"Santos.*0 win" ans))
      (is (re-find #"1 draw" ans)))))

;; ---------------------------------------------------------------------------
;; 3. Player queries
;; ---------------------------------------------------------------------------

(deftest find-a-player-by-name
  (testing "Gabriel Barbosa is found in the player database"
    (let [srv (fresh-server)
          ans (h/call-tool srv "search_players" {:name "Gabriel"})]
      (is (str/includes? ans "Gabriel Barbosa"))
      (is (str/includes? ans "82"))
      (is (str/includes? ans "Flamengo")))))

(deftest find-players-by-club-sorted-by-rating
  (testing "highest-rated Flamengo players are returned, best first"
    (let [srv (fresh-server)
          ans (h/call-tool srv "search_players" {:club "Flamengo"})]
      (is (str/includes? ans "Gabriel Barbosa"))
      (is (str/includes? ans "Bruno Henrique"))
      (is (str/includes? ans "Gerson"))
      (is (not (str/includes? ans "Messi")))
      ;; Sorted by overall rating descending -> Gabriel (82) before Gerson (78).
      (is (< (.indexOf ans "Gabriel Barbosa") (.indexOf ans "Gerson"))))))

(deftest find-brazilian-players
  (testing "filtering by nationality returns only Brazilians, top rated first"
    (let [srv (fresh-server)
          ans (h/call-tool srv "search_players" {:nationality "Brazil"})]
      (is (str/includes? ans "Neymar"))
      (is (str/includes? ans "Gabriel Barbosa"))
      (is (not (str/includes? ans "Messi")))
      ;; Neymar (92) is the top-rated Brazilian.
      (is (< (.indexOf ans "Neymar") (.indexOf ans "Gabriel Barbosa"))))))

;; ---------------------------------------------------------------------------
;; 4. Competition queries
;; ---------------------------------------------------------------------------

(deftest league-champion-from-calculated-standings
  (testing "the 2019 Brasileirão standings name Flamengo as champion"
    (let [srv (fresh-server)
          ans (h/call-tool srv "competition_standings"
                           {:competition "Brasileirão" :season 2019})]
      ;; Flamengo top the table with 13 points (4W 1D 0L).
      (is (re-find #"(?m)^\s*1\.\s+Flamengo" ans))
      (is (re-find #"Flamengo.*13" ans))
      ;; Last in this fixture is Fluminense (3 pts); Corinthians are 2nd.
      (is (< (.indexOf ans "Flamengo") (.indexOf ans "Corinthians"))))))

;; ---------------------------------------------------------------------------
;; 5. Statistical analysis
;; ---------------------------------------------------------------------------

(deftest aggregate-competition-statistics
  (testing "average goals per match, home win rate and biggest win are reported"
    (let [srv (fresh-server)
          ans (h/call-tool srv "competition_stats"
                           {:competition "Brasileirão" :season 2019})]
      ;; 29 goals across 12 matches -> 2.42; 8 of 12 home wins -> 66.7%.
      (is (str/includes? ans "2.42"))
      (is (str/includes? ans "66.7"))
      ;; Biggest victory in the fixture is Palmeiras 3-0 Santos.
      (is (re-find #"Palmeiras 3-0 Santos" ans)))))
