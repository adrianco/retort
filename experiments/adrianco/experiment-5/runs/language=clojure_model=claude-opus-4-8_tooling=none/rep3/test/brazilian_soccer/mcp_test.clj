;; =============================================================================
;; brazilian-soccer.mcp-test
;; -----------------------------------------------------------------------------
;; BDD scenarios for the JSON-RPC / MCP protocol layer: initialize handshake,
;; tools/list, tools/call, notifications, and unknown-method errors. Tool calls
;; use injected fixtures so the protocol is tested without disk access.
;; =============================================================================
(ns brazilian-soccer.mcp-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [clojure.string :as str]
            [clojure.data.json :as json]
            [brazilian-soccer.mcp :as mcp]
            [brazilian-soccer.tools :as tools]
            [brazilian-soccer.fixtures :as fx])
  (:import [java.io BufferedReader StringReader StringWriter]))

(use-fixtures :each
  (fn [t]
    (binding [tools/*matches* fx/matches
              tools/*players* fx/players*]
      (t))))

(deftest initialize-scenario
  (testing "Scenario: initialize returns protocol version and capabilities"
    (let [resp (mcp/handle-request {:id 1 :method "initialize" :params {}})]
      (is (= "2.0" (:jsonrpc resp)))
      (is (= 1 (:id resp)))
      (is (= mcp/protocol-version (get-in resp [:result :protocolVersion])))
      (is (contains? (get-in resp [:result :capabilities]) :tools))
      (is (= "brazilian-soccer-mcp" (get-in resp [:result :serverInfo :name]))))))

(deftest notification-scenario
  (testing "Scenario: notifications/initialized produces no reply"
    (is (nil? (mcp/handle-request {:method "notifications/initialized"})))))

(deftest tools-list-scenario
  (testing "Scenario: tools/list returns the tool catalogue"
    (let [resp (mcp/handle-request {:id 2 :method "tools/list"})]
      (is (= 10 (count (get-in resp [:result :tools])))))))

(deftest tools-call-scenario
  (testing "Scenario: tools/call dispatches and returns content"
    (let [resp (mcp/handle-request
                {:id 3 :method "tools/call"
                 :params {"name" "head_to_head"
                          "arguments" {"team_a" "Flamengo" "team_b" "Fluminense"}}})
          txt  (get-in resp [:result :content 0 :text])]
      (is (str/includes? txt "Head-to-head")))))

(deftest unknown-method-scenario
  (testing "Scenario: unknown method returns JSON-RPC error -32601"
    (let [resp (mcp/handle-request {:id 9 :method "no/such/method"})]
      (is (= -32601 (get-in resp [:error :code]))))))

(deftest serve-roundtrip-scenario
  (testing "Scenario: end-to-end stdio roundtrip over the serve loop"
    (let [input (str/join "\n"
                          [(json/write-str
                            {:jsonrpc "2.0" :id 1 :method "initialize" :params {}})
                           (json/write-str
                            {:jsonrpc "2.0" :method "notifications/initialized"})
                           (json/write-str
                            {:jsonrpc "2.0" :id 2 :method "tools/list"})
                           (json/write-str
                            {:jsonrpc "2.0" :id 3 :method "tools/call"
                             :params {"name" "top_players"
                                      "arguments" {"nationality" "Brazil" "limit" 2}}})])
          out (StringWriter.)]
      (mcp/serve (BufferedReader. (StringReader. input)) out)
      (let [lines (->> (str/split-lines (str out))
                       (remove str/blank?)
                       (map json/read-str))]
        ;; initialize + tools/list + tools/call => 3 responses (notification silent)
        (is (= 3 (count lines)))
        (is (= "brazilian-soccer-mcp"
               (get-in (first lines) ["result" "serverInfo" "name"])))
        (is (str/includes?
             (get-in (last lines) ["result" "content" 0 "text"])
             "Neymar"))))))
