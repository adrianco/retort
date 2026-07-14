(ns brazilian-soccer.mcp-test
  "=============================================================================
   mcp_test.clj — Given/When/Then tests for the MCP JSON-RPC layer
   -----------------------------------------------------------------------------
   Exercises the pure request handler directly (no process spawn) to confirm
   the handshake, tool discovery and tool invocation all behave per protocol.
   ============================================================================="
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.data.json :as json]
            [brazilian-soccer.mcp :as mcp]))

(deftest initialize-handshake
  (testing "Given an MCP client, When it sends initialize"
    (let [resp (mcp/handle-request {:id 1 :method "initialize" :params {}})]
      (testing "Then the server returns its info and capabilities"
        (is (= 1 (:id resp)))
        (is (= "brazilian-soccer-mcp" (get-in resp [:result :serverInfo :name])))
        (is (contains? (get-in resp [:result :capabilities]) :tools))))))

(deftest initialized-notification-has-no-reply
  (testing "Given the initialized notification, When handled, Then no response"
    (is (nil? (mcp/handle-request {:method "notifications/initialized"})))))

(deftest tools-list-exposes-all-tools
  (testing "Given a client, When it lists tools"
    (let [resp (mcp/handle-request {:id 2 :method "tools/list" :params {}})
          names (set (map :name (get-in resp [:result :tools])))]
      (testing "Then every documented tool is present with a schema"
        (is (= #{"search_matches" "team_stats" "head_to_head" "standings"
                 "competition_stats" "biggest_wins" "search_players"
                 "players_by_club"}
               names))
        (is (every? :inputSchema (get-in resp [:result :tools])))))))

(deftest call-search-matches-tool
  (testing "Given the data, When tools/call invokes search_matches for Flamengo"
    (let [resp (mcp/handle-request
                {:id 3 :method "tools/call"
                 :params {:name "search_matches"
                          :arguments {:team "Flamengo" :limit 3}}})
          text (get-in resp [:result :content 0 :text])]
      (testing "Then a non-error text payload mentioning Flamengo is returned"
        (is (false? (get-in resp [:result :isError])))
        (is (string? text))
        (is (re-find #"Flamengo" text))))))

(deftest call-team-stats-tool
  (testing "Given the data, When tools/call invokes team_stats"
    (let [resp (mcp/handle-request
                {:id 4 :method "tools/call"
                 :params {:name "team_stats"
                          :arguments {:team "Palmeiras" :season 2019}}})
          text (get-in resp [:result :content 0 :text])]
      (testing "Then a record report is returned"
        (is (false? (get-in resp [:result :isError])))
        (is (re-find #"Win rate" text))))))

(deftest call-standings-tool
  (testing "Given the data, When tools/call invokes standings for 2019"
    (let [resp (mcp/handle-request
                {:id 5 :method "tools/call"
                 :params {:name "standings"
                          :arguments {:competition "Brasileirão" :season 2019 :limit 5}}})
          text (get-in resp [:result :content 0 :text])]
      (testing "Then a ranked table is returned"
        (is (false? (get-in resp [:result :isError])))
        (is (re-find #"1\. " text))
        (is (re-find #"pts" text))))))

(deftest call-search-players-tool
  (testing "Given the FIFA data, When tools/call searches Brazilian players"
    (let [resp (mcp/handle-request
                {:id 6 :method "tools/call"
                 :params {:name "search_players"
                          :arguments {:nationality "Brazil" :limit 5}}})
          text (get-in resp [:result :content 0 :text])]
      (testing "Then up to 5 Brazilian players are listed"
        (is (false? (get-in resp [:result :isError])))
        (is (re-find #"Overall" text))))))

(deftest unknown-tool-is-reported-as-error
  (testing "Given an unknown tool, When called, Then isError is true"
    (let [resp (mcp/handle-request
                {:id 7 :method "tools/call"
                 :params {:name "nope" :arguments {}}})]
      (is (true? (get-in resp [:result :isError]))))))

(deftest unknown-method-returns-jsonrpc-error
  (testing "Given an unknown method with an id, When handled, Then -32601"
    (let [resp (mcp/handle-request {:id 8 :method "bogus/method" :params {}})]
      (is (= -32601 (get-in resp [:error :code]))))))

(deftest responses-serialize-to-json
  (testing "Given any response, When serialized, Then it is valid JSON"
    (let [resp (mcp/handle-request {:id 9 :method "tools/list" :params {}})]
      (is (string? (json/write-str resp))))))
