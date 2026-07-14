(ns brazilian-soccer.server-test
  "BDD scenarios for the MCP JSON-RPC protocol layer: initialize handshake,
  tool listing, tool calls and error handling."
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [brazilian-soccer.server :as server]
            [brazilian-soccer.tools :as tools]))

(defn- request [id method params]
  {"jsonrpc" "2.0" "id" id "method" method "params" params})

(defn- call-tool-text
  "Round-trips a tools/call through the protocol handler, returns the text."
  [tool-name arguments]
  (let [resp (server/handle-request
              (request 1 "tools/call" {"name" tool-name
                                       "arguments" arguments}))]
    (is (false? (get-in resp [:result :isError])) (str tool-name " should not error"))
    (-> resp :result :content first :text)))

(deftest scenario-initialize-handshake
  (testing "Given a newly started server
            When the client sends an initialize request
            Then the server replies with protocol version, capabilities and info"
    (let [resp (server/handle-request
                (request 0 "initialize"
                         {"protocolVersion" "2024-11-05"
                          "capabilities" {}
                          "clientInfo" {"name" "test" "version" "0"}}))]
      (is (= "2.0" (:jsonrpc resp)))
      (is (= 0 (:id resp)))
      (is (= "2024-11-05" (get-in resp [:result :protocolVersion])))
      (is (= "brazilian-soccer-mcp" (get-in resp [:result :serverInfo :name])))
      (is (contains? (get-in resp [:result :capabilities]) :tools)))))

(deftest scenario-notifications-get-no-response
  (testing "Given the MCP handshake
            When the client sends the initialized notification (no id)
            Then the server stays silent"
    (is (nil? (server/handle-request {"jsonrpc" "2.0"
                                      "method" "notifications/initialized"})))))

(deftest scenario-list-tools
  (testing "Given an initialized server
            When the client requests tools/list
            Then every tool has a name, description and JSON Schema"
    (let [resp (server/handle-request (request 1 "tools/list" {}))
          listed (get-in resp [:result :tools])]
      (is (= (count tools/tools) (count listed)))
      (is (every? :name listed))
      (is (every? :description listed))
      (is (every? #(= "object" (get-in % [:inputSchema :type])) listed))
      (is (= #{"search_matches" "head_to_head" "get_team_stats" "get_standings"
               "search_players" "get_player" "get_competition_stats"
               "get_biggest_wins" "list_teams"}
             (set (map :name listed)))))))

(deftest scenario-call-each-tool-through-the-protocol
  (testing "Given an initialized server
            When each tool is called with typical arguments
            Then each returns non-empty text content"
    (is (str/includes? (call-tool-text "search_matches"
                                       {"team" "Flamengo" "opponent" "Fluminense"})
                       "Flamengo"))
    (is (str/includes? (call-tool-text "head_to_head"
                                       {"team1" "Palmeiras" "team2" "Corinthians"})
                       "head-to-head"))
    (is (str/includes? (call-tool-text "get_team_stats"
                                       {"team" "Corinthians" "season" 2022
                                        "competition" "brasileirao" "venue" "home"})
                       "Win rate"))
    (is (str/includes? (call-tool-text "get_standings" {"season" 2019})
                       "Flamengo - 90 pts"))
    (is (str/includes? (call-tool-text "search_players"
                                       {"nationality" "Brazil" "limit" 5})
                       "Neymar"))
    (is (str/includes? (call-tool-text "get_player" {"name" "Casemiro"})
                       "Overall"))
    (is (str/includes? (call-tool-text "get_competition_stats"
                                       {"competition" "brasileirao"})
                       "Average goals per match"))
    (is (str/includes? (call-tool-text "get_biggest_wins" {"limit" 3})
                       "margin"))
    (is (str/includes? (call-tool-text "list_teams"
                                       {"competition" "serie a" "season" 2019})
                       "Flamengo"))))

(deftest scenario-protocol-errors
  (testing "Given a running server
            When the client misbehaves
            Then JSON-RPC errors come back with the right codes"
    (let [unknown (server/handle-request (request 7 "no/such-method" {}))]
      (is (= -32601 (get-in unknown [:error :code])))
      (is (= 7 (:id unknown))))
    (let [bad-tool (server/handle-request
                    (request 8 "tools/call" {"name" "no_such_tool"
                                             "arguments" {}}))]
      (is (true? (get-in bad-tool [:result :isError]))
          "unknown tool is a tool-level error, not a protocol error"))
    (let [parse-err (json/read-str (server/handle-line "{not json"))]
      (is (= -32700 (get-in parse-err ["error" "code"]))))
    (is (nil? (server/handle-line "")) "blank lines are ignored")))

(deftest scenario-full-stdio-round-trip
  (testing "Given a request serialized as one line of JSON
            When it goes through the line handler
            Then a one-line JSON response comes back"
    (let [line (json/write-str (request 42 "tools/call"
                                        {"name" "search_matches"
                                         "arguments" {"team" "Santos"
                                                      "season" 2015
                                                      "limit" 3}}))
          resp (json/read-str (server/handle-line line))]
      (is (= 42 (get resp "id")))
      (is (not (str/includes? (server/handle-line line) "\n"))
          "stdio transport requires single-line responses")
      (is (str/includes? (get-in resp ["result" "content" 0 "text"]) "Santos")))))
