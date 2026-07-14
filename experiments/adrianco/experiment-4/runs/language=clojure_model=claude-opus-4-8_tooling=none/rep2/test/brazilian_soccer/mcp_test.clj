(ns brazilian-soccer.mcp-test
  "Context
  =======
  BDD tests for the MCP/JSON-RPC layer: protocol handshake, tool discovery and
  tool invocation, exercising `handle-request` directly (transport-independent)."
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.string :as str]
            [brazilian-soccer.mcp :as mcp]))

(deftest initialize-handshake
  (testing "Scenario: client initialises the server"
    ;; When the client sends initialize
    (let [resp (mcp/handle-request {:jsonrpc "2.0" :id 1 :method "initialize"})]
      ;; Then the server returns protocol version, capabilities and info
      (is (= 1 (:id resp)))
      (is (= mcp/protocol-version (get-in resp [:result :protocolVersion])))
      (is (contains? (get-in resp [:result :capabilities]) :tools))
      (is (= "brazilian-soccer-mcp" (get-in resp [:result :serverInfo :name]))))))

(deftest notifications-have-no-response
  (testing "Scenario: notifications/initialized produces no reply"
    (is (nil? (mcp/handle-request {:jsonrpc "2.0" :method "notifications/initialized"})))))

(deftest tools-are-listed
  (testing "Scenario: tools/list advertises the tool catalogue"
    (let [resp (mcp/handle-request {:jsonrpc "2.0" :id 2 :method "tools/list"})
          names (set (map :name (get-in resp [:result :tools])))]
      (is (contains? names "find_matches"))
      (is (contains? names "team_record"))
      (is (contains? names "standings"))
      (is (contains? names "search_players"))
      ;; every tool has a name, description and input schema
      (doseq [t (get-in resp [:result :tools])]
        (is (string? (:name t)))
        (is (string? (:description t)))
        (is (= "object" (get-in t [:inputSchema :type])))))))

(defn- call [tool args]
  (mcp/handle-request {:jsonrpc "2.0" :id 9 :method "tools/call"
                       :params {:name tool :arguments args}}))

(defn- text [resp] (get-in resp [:result :content 0 :text]))

(deftest call-find-matches
  (testing "Scenario: tools/call find_matches returns formatted text"
    (let [resp (call "find_matches" {:team "Flamengo" :opponent "Fluminense"})]
      (is (false? (get-in resp [:result :isError])))
      (is (string? (text resp)))
      (is (str/includes? (text resp) "Flamengo")))))

(deftest call-standings
  (testing "Scenario: tools/call standings renders the league table"
    (let [resp (call "standings" {:competition "Brasileirão Série A" :season 2019})]
      (is (false? (get-in resp [:result :isError])))
      (is (str/includes? (text resp) "Flamengo"))
      (is (str/includes? (text resp) "90 pts")))))

(deftest call-team-record
  (testing "Scenario: tools/call team_record renders the record block"
    (let [resp (call "team_record" {:team "Flamengo" :season 2019
                                     :competition "Brasileirão Série A"})]
      (is (str/includes? (text resp) "Wins: 28"))
      (is (str/includes? (text resp) "Win rate: 73.7%")))))

(deftest call-search-players
  (testing "Scenario: tools/call search_players renders a ranked list"
    (let [resp (call "search_players" {:nationality "Brazil" :limit 3})]
      (is (str/includes? (text resp) "Neymar")))))

(deftest unknown-tool-is-an-error-result
  (testing "Scenario: calling an unknown tool yields an isError result"
    (let [resp (call "does_not_exist" {})]
      (is (true? (get-in resp [:result :isError])))
      (is (str/includes? (text resp) "Unknown tool")))))

(deftest unknown-method-returns-jsonrpc-error
  (testing "Scenario: an unknown method returns a JSON-RPC error object"
    (let [resp (mcp/handle-request {:jsonrpc "2.0" :id 7 :method "no/such"})]
      (is (= -32601 (get-in resp [:error :code]))))))
