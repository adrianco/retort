(ns brazilian-soccer.server-test
  "CONTEXT
  =======
  BDD (Given/When/Then) tests for the MCP JSON-RPC layer: the initialize
  handshake, tools/list, tools/call, notifications and error codes, exercised
  through handle-line (string in, string out) exactly as the stdio loop does."
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.data.json :as json]
            [brazilian-soccer.server :as server]))

(defn- rpc
  "Send one JSON-RPC message (as a map) through the server; returns the
  parsed response map, or nil for notifications."
  [msg]
  (some-> (server/handle-line (json/write-str msg))
          (json/read-str :key-fn keyword)))

(deftest initialize-handshake
  (testing "Given an MCP client
            When it sends initialize
            Then the server replies with protocol version, capabilities and identity"
    (let [resp (rpc {:jsonrpc "2.0" :id 1 :method "initialize"
                     :params {:protocolVersion "2025-06-18"
                              :capabilities {}
                              :clientInfo {:name "test-client" :version "0.0"}}})]
      (is (= "2.0" (:jsonrpc resp)))
      (is (= 1 (:id resp)))
      (is (= "2025-06-18" (get-in resp [:result :protocolVersion])))
      (is (= "brazilian-soccer-mcp" (get-in resp [:result :serverInfo :name])))
      (is (contains? (get-in resp [:result :capabilities]) :tools))))
  (testing "And an unknown requested protocol version falls back to a supported one"
    (let [resp (rpc {:jsonrpc "2.0" :id 2 :method "initialize"
                     :params {:protocolVersion "1999-01-01"}})]
      (is (contains? server/supported-protocol-versions
                     (get-in resp [:result :protocolVersion]))))))

(deftest notifications-get-no-response
  (testing "Given the protocol rule that notifications are not answered
            When notifications/initialized arrives
            Then the server stays silent"
    (is (nil? (rpc {:jsonrpc "2.0" :method "notifications/initialized"})))
    (is (nil? (rpc {:jsonrpc "2.0" :method "notifications/cancelled"
                    :params {:requestId 1}})))))

(deftest ping
  (testing "When a ping request arrives, Then an empty result returns"
    (let [resp (rpc {:jsonrpc "2.0" :id 7 :method "ping"})]
      (is (= {} (:result resp))))))

(deftest tools-list
  (testing "Given an initialized session
            When tools/list is requested
            Then every tool descriptor has name, description and inputSchema"
    (let [resp (rpc {:jsonrpc "2.0" :id 3 :method "tools/list"})
          tools (get-in resp [:result :tools])]
      (is (>= (count tools) 10))
      (doseq [t tools]
        (is (string? (:name t)))
        (is (seq (:description t)))
        (is (= "object" (get-in t [:inputSchema :type]))))
      (is (contains? (set (map :name tools)) "search_matches")))))

(deftest tools-call
  (testing "Given the tool registry
            When tools/call invokes head_to_head
            Then a text content block with the answer returns"
    (let [resp (rpc {:jsonrpc "2.0" :id 4 :method "tools/call"
                     :params {:name "head_to_head"
                              :arguments {:team1 "Flamengo" :team2 "Fluminense"}}})
          content (get-in resp [:result :content])]
      (is (false? (get-in resp [:result :isError])))
      (is (= "text" (:type (first content))))
      (is (.contains ^String (:text (first content)) "Head-to-head")))))

(deftest error-codes
  (testing "When an unknown tool is called, Then error -32602"
    (let [resp (rpc {:jsonrpc "2.0" :id 5 :method "tools/call"
                     :params {:name "does_not_exist" :arguments {}}})]
      (is (= -32602 (get-in resp [:error :code])))))
  (testing "When an unknown method is requested, Then error -32601"
    (let [resp (rpc {:jsonrpc "2.0" :id 6 :method "no/such/method"})]
      (is (= -32601 (get-in resp [:error :code])))))
  (testing "When the line is not valid JSON, Then parse error -32700"
    (let [resp (json/read-str (server/handle-line "{nope") :key-fn keyword)]
      (is (= -32700 (get-in resp [:error :code])))))
  (testing "When the JSON is not an object, Then invalid request -32600"
    (let [resp (json/read-str (server/handle-line "[1,2,3]") :key-fn keyword)]
      (is (= -32600 (get-in resp [:error :code]))))))

(deftest full-session
  (testing "Given a complete MCP session transcript
            When initialize, initialized, tools/list and a query run in order
            Then each step succeeds end to end"
    (let [init (rpc {:jsonrpc "2.0" :id 1 :method "initialize"
                     :params {:protocolVersion "2024-11-05"}})
          _ (rpc {:jsonrpc "2.0" :method "notifications/initialized"})
          tools (rpc {:jsonrpc "2.0" :id 2 :method "tools/list"})
          answer (rpc {:jsonrpc "2.0" :id 3 :method "tools/call"
                       :params {:name "league_standings"
                                :arguments {:season 2019 :limit 5}}})]
      (is (= "2024-11-05" (get-in init [:result :protocolVersion])))
      (is (seq (get-in tools [:result :tools])))
      (is (.contains ^String (get-in answer [:result :content 0 :text])
                     "Flamengo - 90 pts")))))
