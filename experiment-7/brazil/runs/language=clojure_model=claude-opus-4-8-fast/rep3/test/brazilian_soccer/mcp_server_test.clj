;; =============================================================================
;; brazilian-soccer.mcp-server-test
;; -----------------------------------------------------------------------------
;; BDD coverage for the MCP JSON-RPC layer: initialize handshake, tools/list,
;; tools/call dispatch and a full stdio round-trip.
;; =============================================================================
(ns brazilian-soccer.mcp-server-test
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.data.json :as json]
            [clojure.string :as str]
            [brazilian-soccer.mcp-server :as mcp]
            [brazilian-soccer.test-helper :as h]))

(deftest initialize-test
  (testing "Given an initialize request, When handled, Then capabilities and serverInfo are returned"
    (let [resp (mcp/handle-request (h/graph)
                                   {:id 1 :method "initialize"
                                    :params {:protocolVersion "2024-11-05"}})]
      (is (= 1 (:id resp)))
      (is (= "2024-11-05" (get-in resp [:result :protocolVersion])))
      (is (contains? (get-in resp [:result :capabilities]) :tools))
      (is (= "brazilian-soccer-mcp" (get-in resp [:result :serverInfo :name]))))))

(deftest notifications-are-silent-test
  (testing "Given an initialized notification, When handled, Then no response is produced"
    (is (nil? (mcp/handle-request (h/graph) {:method "notifications/initialized"})))))

(deftest tools-list-test
  (testing "Given tools/list, When handled, Then every advertised tool has a schema"
    (let [resp (mcp/handle-request (h/graph) {:id 2 :method "tools/list"})
          tools (get-in resp [:result :tools])
          names (set (map :name tools))]
      (is (>= (count tools) 8))
      (is (contains? names "find_matches"))
      (is (contains? names "find_players"))
      (is (contains? names "standings"))
      (is (every? :inputSchema tools)))))

(deftest tools-call-find-players-test
  (testing "Given tools/call find_players for Brazilians, When handled, Then text content returns"
    (let [resp (mcp/handle-request
                (h/graph)
                {:id 3 :method "tools/call"
                 :params {:name "find_players"
                          :arguments {:nationality "Brazil" :limit 3}}})
          text (get-in resp [:result :content 0 :text])]
      (is (false? (get-in resp [:result :isError])))
      (is (string? text))
      (is (str/includes? text "Overall")))))

(deftest tools-call-unknown-test
  (testing "Given an unknown tool, When called, Then an error result (not a crash) returns"
    (let [resp (mcp/handle-request (h/graph)
                                   {:id 4 :method "tools/call"
                                    :params {:name "does_not_exist" :arguments {}}})]
      (is (true? (get-in resp [:result :isError]))))))

(deftest unknown-method-test
  (testing "Given an unknown request method, When handled, Then JSON-RPC error -32601"
    (let [resp (mcp/handle-request (h/graph) {:id 5 :method "no/such/method"})]
      (is (= -32601 (get-in resp [:error :code]))))))

(deftest stdio-roundtrip-test
  (testing "Given JSON-RPC lines on stdin, When served, Then JSON-RPC lines come back on stdout"
    (let [input (str (json/write-str {:jsonrpc "2.0" :id 1 :method "initialize" :params {}}) "\n"
                     (json/write-str {:jsonrpc "2.0" :method "notifications/initialized"}) "\n"
                     (json/write-str {:jsonrpc "2.0" :id 2 :method "tools/call"
                                      :params {:name "head_to_head"
                                               :arguments {:team_a "Flamengo" :team_b "Fluminense"}}}) "\n")
          out (java.io.StringWriter.)]
      (mcp/serve (h/graph)
                 (java.io.StringReader. input)
                 out)
      (let [lines (->> (str/split-lines (str out)) (remove str/blank?) (map json/read-str))]
        ;; two requests with ids -> two responses; the notification is silent
        (is (= 2 (count lines)))
        (is (= 1 (get (first lines) "id")))
        (is (contains? (get (first lines) "result") "serverInfo"))
        (is (= 2 (get (second lines) "id")))
        (is (str/includes? (get-in (second lines) ["result" "content" 0 "text"])
                           "head-to-head"))))))
