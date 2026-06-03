(ns soccer.mcp-test
  "=============================================================================
   BDD (Given-When-Then) scenarios for the MCP JSON-RPC surface: initialize,
   tools/list and tools/call, exercised against the fixture dataset.
   ============================================================================="
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.data.json :as json]
            [soccer.fixtures :as fx]
            [soccer.mcp :as mcp]))

(defn- req [m] (mcp/handle-request fx/db m))

(deftest initialize-scenario
  (testing "Scenario: a client initializes the server"
    ;; When an initialize request is received
    (let [r (req {:id 1 :method "initialize" :params {}})]
      ;; Then the server returns its info and tool capability
      (is (= "2.0" (:jsonrpc r)))
      (is (= "brazilian-soccer-mcp" (get-in r [:result :serverInfo :name])))
      (is (contains? (get-in r [:result :capabilities]) :tools)))))

(deftest tools-list-scenario
  (testing "Scenario: a client lists available tools"
    ;; When a tools/list request is received
    (let [r (req {:id 2 :method "tools/list" :params {}})
          names (set (map :name (get-in r [:result :tools])))]
      ;; Then every required capability is exposed as a tool
      (is (every? names ["search_matches" "head_to_head" "team_stats"
                         "standings" "league_stats" "biggest_wins"
                         "search_players" "season_summary"]))
      ;; And each tool has a JSON input schema
      (is (every? :inputSchema (get-in r [:result :tools]))))))

(deftest tools-call-matches-scenario
  (testing "Scenario: calling search_matches returns text content"
    ;; When search_matches is called for the Fla-Flu meetings
    (let [r (req {:id 3 :method "tools/call"
                  :params {"name" "search_matches"
                           "arguments" {"team" "Flamengo" "team2" "Fluminense"}}})
          text (get-in r [:result :content 0 :text])]
      ;; Then a textual answer is returned mentioning both teams
      (is (= "text" (get-in r [:result :content 0 :type])))
      (is (re-find #"Flamengo" text))
      (is (re-find #"Fluminense" text)))))

(deftest tools-call-standings-scenario
  (testing "Scenario: calling standings returns the league leader"
    (let [r (req {:id 4 :method "tools/call"
                  :params {"name" "standings"
                           "arguments" {"competition" "Brasileirão Série A" "season" 2019}}})
          text (get-in r [:result :content 0 :text])]
      (is (re-find #"Flamengo" text))
      (is (re-find #"Standings" text)))))

(deftest tools-call-players-scenario
  (testing "Scenario: calling search_players finds Brazilians"
    (let [r (req {:id 5 :method "tools/call"
                  :params {"name" "search_players"
                           "arguments" {"nationality" "Brazil" "limit" 3}}})
          text (get-in r [:result :content 0 :text])]
      (is (re-find #"Neymar" text)))))

(deftest unknown-method-scenario
  (testing "Scenario: an unknown method yields a JSON-RPC error"
    (let [r (req {:id 6 :method "does/not/exist" :params {}})]
      (is (= -32601 (get-in r [:error :code]))))))

(deftest notification-scenario
  (testing "Scenario: notifications/initialized is not answered"
    ;; Then notifications produce no response
    (is (nil? (req {:id nil :method "notifications/initialized" :params {}})))))

(deftest roundtrip-scenario
  (testing "Scenario: responses serialize to valid JSON"
    (let [r (req {:id 7 :method "tools/list" :params {}})
          s (json/write-str r)]
      (is (string? s))
      (is (= 7 (get (json/read-str s) "id"))))))
