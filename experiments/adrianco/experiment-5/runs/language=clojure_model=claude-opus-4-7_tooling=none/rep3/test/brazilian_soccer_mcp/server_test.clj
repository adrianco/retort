(ns brazilian-soccer-mcp.server-test
  "BDD tests for the MCP JSON-RPC server surface (initialize, tools/list,
   tools/call). We bypass stdio and call handle-request directly with a
   tiny in-memory db."
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.data.json :as json]
            [brazilian-soccer-mcp.server :as server]))

(def ^:private db
  {:matches
   [{:competition "Brasileirão Série A" :season 2023 :round 1
     :date "2023-04-15" :home "Palmeiras-SP" :away "Santos-SP"
     :home-goal 3 :away-goal 0}
    {:competition "Brasileirão Série A" :season 2023 :round 2
     :date "2023-04-22" :home "Flamengo-RJ" :away "Palmeiras-SP"
     :home-goal 1 :away-goal 1}
    {:competition "Copa do Brasil" :season 2023
     :date "2023-08-01" :home "Flamengo-RJ" :away "São Paulo"
     :home-goal 0 :away-goal 1}]
   :players
   [{:name "Neymar Jr" :nationality "Brazil" :overall 91
     :club "Paris Saint-Germain" :position "LW"}
    {:name "Gabriel Barbosa" :nationality "Brazil" :overall 84
     :club "Flamengo" :position "ST"}]})

(defn- req [method params]
  (-> (server/handle-request db {"id" 1 "method" method "params" params})
      (json/write-str)
      (json/read-str)))

(deftest initialize-returns-server-info
  (testing "Scenario: initialize handshake"
    (let [r (req "initialize" {})]
      (is (= 1 (get r "id")))
      (is (= "2024-11-05" (get-in r ["result" "protocolVersion"])))
      (is (= "brazilian-soccer-mcp" (get-in r ["result" "serverInfo" "name"]))))))

(deftest tools-list-includes-expected-tools
  (testing "Scenario: tools/list enumerates the catalog"
    (let [r     (req "tools/list" {})
          names (set (map #(get % "name") (get-in r ["result" "tools"])))]
      (is (contains? names "search_matches"))
      (is (contains? names "head_to_head"))
      (is (contains? names "team_stats"))
      (is (contains? names "standings"))
      (is (contains? names "search_players"))
      (is (contains? names "biggest_wins"))
      (is (contains? names "average_goals"))
      (is (contains? names "home_win_rate")))))

(deftest tools-call-team-stats
  (testing "Scenario: team_stats returns a text content block"
    (let [r    (req "tools/call" {"name" "team_stats"
                                  "arguments" {"team" "Palmeiras"
                                               "season" 2023}})
          text (get-in r ["result" "content" 0 "text"])]
      (is (string? text))
      (is (re-find #"Palmeiras" text))
      (is (re-find #"matches" text)))))

(deftest tools-call-head-to-head
  (testing "Scenario: head_to_head returns aggregated counts"
    (let [r    (req "tools/call" {"name" "head_to_head"
                                  "arguments" {"team_a" "Flamengo"
                                               "team_b" "Palmeiras"}})
          text (get-in r ["result" "content" 0 "text"])]
      (is (re-find #"1 match" text)))))

(deftest tools-call-search-players
  (testing "Scenario: search_players by nationality"
    (let [r    (req "tools/call" {"name" "search_players"
                                  "arguments" {"nationality" "Brazil"}})
          text (get-in r ["result" "content" 0 "text"])]
      (is (re-find #"Neymar" text))
      (is (re-find #"Gabriel Barbosa" text)))))

(deftest unknown-tool-returns-error
  (testing "Scenario: a bad tool name yields a JSON-RPC error"
    (let [r (req "tools/call" {"name" "no_such_tool" "arguments" {}})]
      (is (contains? r "error"))
      (is (= -32601 (get-in r ["error" "code"]))))))

(deftest unknown-method-returns-error
  (testing "Scenario: an unknown JSON-RPC method yields -32601"
    (let [r (req "frobnicate" {})]
      (is (= -32601 (get-in r ["error" "code"]))))))
