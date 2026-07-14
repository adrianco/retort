;; =============================================================================
;; Tests for brsoccer.mcp -- the JSON-RPC / MCP protocol layer.
;; Exercises the pure handle-request dispatch and a full stdio round-trip.
;; =============================================================================
(ns brsoccer.mcp-test
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.data.json :as json]
            [clojure.string :as str]
            [brsoccer.mcp :as mcp])
  (:import [java.io BufferedReader StringReader StringWriter]))

(deftest initialize-handshake
  (let [resp (mcp/handle-request {:id 1 :method "initialize" :params {}})]
    (is (= "2.0" (:jsonrpc resp)))
    (is (= 1 (:id resp)))
    (is (= mcp/protocol-version (get-in resp [:result :protocolVersion])))
    (is (= "brazilian-soccer-mcp" (get-in resp [:result :serverInfo :name])))))

(deftest tools-are-advertised
  (let [resp (mcp/handle-request {:id 2 :method "tools/list" :params {}})
        names (set (map :name (get-in resp [:result :tools])))]
    (is (contains? names "find_matches"))
    (is (contains? names "team_record"))
    (is (contains? names "search_players"))
    (is (contains? names "standings"))
    (is (contains? names "match_statistics"))
    (testing "every advertised tool has a description and input schema"
      (is (every? :description (get-in resp [:result :tools])))
      (is (every? :inputSchema (get-in resp [:result :tools]))))))

(deftest notifications-get-no-response
  (is (nil? (mcp/handle-request {:method "notifications/initialized"}))))

(deftest unknown-method-errors
  (let [resp (mcp/handle-request {:id 9 :method "does/not/exist" :params {}})]
    (is (= -32601 (get-in resp [:error :code])))))

(deftest tools-call-find-matches
  (let [resp (mcp/handle-request
               {:id 3 :method "tools/call"
                :params {:name "find_matches"
                         :arguments {:team "Flamengo" :opponent "Fluminense"}}})
        result (:result resp)]
    (is (false? (:isError result)))
    (is (str/includes? (get-in result [:content 0 :text]) "Head-to-head"))
    (is (some? (get-in result [:structuredContent :result])))))

(deftest tools-call-standings
  (let [resp (mcp/handle-request
               {:id 4 :method "tools/call"
                :params {:name "standings"
                         :arguments {:competition "Brasileirão Série A" :season 2019}}})
        text (get-in resp [:result :content 0 :text])]
    (is (str/includes? text "standings"))
    (is (str/includes? text "pts"))))

(deftest unknown-tool-is-flagged
  (let [resp (mcp/handle-request
               {:id 5 :method "tools/call"
                :params {:name "no_such_tool" :arguments {}}})]
    (is (true? (get-in resp [:result :isError])))))

(deftest full-stdio-round-trip
  (testing "newline-delimited JSON in -> JSON-RPC responses out; notifications produce nothing"
    (let [requests (str (json/write-str {:jsonrpc "2.0" :id 1 :method "initialize" :params {}}) "\n"
                        (json/write-str {:jsonrpc "2.0" :method "notifications/initialized"}) "\n"
                        (json/write-str {:jsonrpc "2.0" :id 2 :method "tools/list" :params {}}) "\n")
          in  (BufferedReader. (StringReader. requests))
          out (StringWriter.)]
      (mcp/serve! in out)
      (let [lines (->> (str/split-lines (str out)) (remove str/blank?))
            parsed (map #(json/read-str % :key-fn keyword) lines)]
        (testing "exactly two responses (the notification is not answered)"
          (is (= 2 (count parsed))))
        (is (= [1 2] (map :id parsed)))
        (is (= mcp/protocol-version (get-in (first parsed) [:result :protocolVersion])))
        (is (seq (get-in (second parsed) [:result :tools])))))))
