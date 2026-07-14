(ns soccer-mcp.server-test
  "BDD-style tests for the MCP JSON-RPC dispatch and tool surface. Drives the
   pure handler directly (no stdio) so tests stay deterministic."
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [soccer-mcp.queries-test :as fix]
            [soccer-mcp.server :as server]))

(defn- req [id method params]
  (cond-> {"jsonrpc" "2.0" "method" method}
    id     (assoc "id" id)
    params (assoc "params" params)))

(defn- tool-call [id name args]
  (req id "tools/call" {"name" name "arguments" args}))

(deftest jsonrpc-handshake
  (testing "Feature: MCP handshake"
    (testing "Scenario: initialize returns server info and protocol version"
      (let [resp (server/handle-message fix/fixture (req 1 "initialize" {}))]
        (is (= 1 (:id resp)))
        (is (= server/protocol-version (-> resp :result :protocolVersion)))
        (is (= "soccer-mcp" (-> resp :result :serverInfo :name)))))

    (testing "Scenario: notifications produce no response"
      (is (nil? (server/handle-message
                 fix/fixture
                 (req nil "notifications/initialized" nil)))))

    (testing "Scenario: tools/list returns the tool catalogue"
      (let [resp (server/handle-message fix/fixture (req 2 "tools/list" {}))
            tools (-> resp :result :tools)
            names (set (map :name tools))]
        (is (contains? names "find_matches"))
        (is (contains? names "team_stats"))
        (is (contains? names "head_to_head"))
        (is (contains? names "standings"))
        (is (contains? names "biggest_wins"))
        (is (contains? names "league_averages"))
        (is (contains? names "find_players"))
        (is (contains? names "players_by_club"))))

    (testing "Scenario: unknown methods return error -32601"
      (let [resp (server/handle-message fix/fixture (req 9 "nonsense" {}))]
        (is (= -32601 (-> resp :error :code)))))))

(defn- text [resp]
  (-> resp :result :content first :text))

(deftest tools-call-find-matches
  (testing "Feature: find_matches tool"
    (testing "Scenario: returns a human-readable list"
      (let [resp (server/handle-message
                  fix/fixture
                  (tool-call 10 "find_matches"
                             {"team_a" "Flamengo" "team_b" "Fluminense"}))
            t    (text resp)]
        (is (string? t))
        (is (str/includes? t "Flamengo"))
        (is (str/includes? t "Fluminense"))
        (is (str/includes? t "match"))))))

(deftest tools-call-team-stats
  (testing "Feature: team_stats tool"
    (testing "Scenario: includes points and win rate"
      (let [resp (server/handle-message
                  fix/fixture
                  (tool-call 11 "team_stats" {"team" "Flamengo"}))
            t    (text resp)]
        (is (str/includes? t "Flamengo"))
        (is (str/includes? t "Played:"))
        (is (str/includes? t "Points:"))))))

(deftest tools-call-head-to-head
  (testing "Feature: head_to_head tool"
    (testing "Scenario: shows wins for both sides"
      (let [resp (server/handle-message
                  fix/fixture
                  (tool-call 12 "head_to_head"
                             {"team_a" "Flamengo" "team_b" "Fluminense"}))
            t    (text resp)]
        (is (str/includes? t "head-to-head"))
        (is (str/includes? t "Flamengo wins:"))
        (is (str/includes? t "Fluminense wins:"))))))

(deftest tools-call-standings
  (testing "Feature: standings tool"
    (testing "Scenario: returns a sorted table with header columns"
      (let [resp (server/handle-message
                  fix/fixture
                  (tool-call 13 "standings"
                             {"competition" "brasileirao" "season" 2023}))
            t    (text resp)]
        (is (str/includes? t "Team"))
        (is (str/includes? t "Pts"))
        (is (str/includes? t "Fluminense"))))))

(deftest tools-call-biggest-wins
  (testing "Feature: biggest_wins tool"
    (testing "Scenario: lists top-N by margin"
      (let [resp (server/handle-message
                  fix/fixture
                  (tool-call 14 "biggest_wins" {"n" 3}))
            t    (text resp)]
        (is (str/starts-with? t "1."))
        (is (str/includes? t "Palmeiras"))))))

(deftest tools-call-league-averages
  (testing "Feature: league_averages tool"
    (testing "Scenario: reports goals/match and home-win rate"
      (let [resp (server/handle-message
                  fix/fixture
                  (tool-call 15 "league_averages" {}))
            t    (text resp)]
        (is (str/includes? t "Average"))
        (is (str/includes? t "Home-win rate"))))))

(deftest tools-call-players
  (testing "Feature: find_players tool"
    (testing "Scenario: returns players with overall ratings"
      (let [resp (server/handle-message
                  fix/fixture
                  (tool-call 16 "find_players" {"nationality" "Brazil"}))
            t    (text resp)]
        (is (str/includes? t "Neymar"))
        (is (str/includes? t "Overall")))))

  (testing "Feature: players_by_club tool"
    (testing "Scenario: aggregates Brazilian players per club"
      (let [resp (server/handle-message
                  fix/fixture
                  (tool-call 17 "players_by_club" {}))
            t    (text resp)]
        (is (str/includes? t "players"))
        (is (str/includes? t "avg overall"))))))

(deftest tools-call-unknown-tool
  (testing "Feature: unknown tool name produces a JSON-RPC error"
    (let [resp (server/handle-message
                fix/fixture
                (tool-call 20 "wat" {}))]
      (is (some? (:error resp))))))

(deftest json-round-trip
  (testing "Feature: every tool response can be serialized to JSON for transport"
    (doseq [tname ["find_matches" "team_stats" "head_to_head" "standings"
                   "biggest_wins" "league_averages" "find_players"
                   "players_by_club"]
            :let [args (case tname
                         "team_stats"   {"team" "Flamengo"}
                         "head_to_head" {"team_a" "Flamengo"
                                         "team_b" "Fluminense"}
                         {})]]
      (let [resp (server/handle-message fix/fixture
                                        (tool-call 50 tname args))
            s    (json/write-str resp)]
        (is (string? s))
        (is (pos? (count s)))))))
