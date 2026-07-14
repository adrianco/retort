;; =============================================================================
;; soccer.mcp-test — BDD tests for the MCP protocol layer & tool dispatch
;; -----------------------------------------------------------------------------
;; Project: brazilian-soccer-mcp
;; =============================================================================
(ns soccer.mcp-test
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.string :as str]
            [clojure.data.json :as json]
            [soccer.mcp :as mcp]
            [soccer.tools :as tools]
            [soccer.query-test :as fix])
  (:import [java.io ByteArrayInputStream ByteArrayOutputStream]))

(def db fix/fixture)

(deftest initialize-handshake
  (testing "Given an initialize request, When handled, Then protocol info is returned"
    (let [resp (mcp/handle-request db {:method "initialize" :id 1 :params {}})]
      (is (= "2.0" (:jsonrpc resp)))
      (is (= 1 (:id resp)))
      (is (string? (get-in resp [:result :protocolVersion])))
      (is (= "brazilian-soccer-mcp" (get-in resp [:result :serverInfo :name]))))))

(deftest initialized-notification-has-no-reply
  (testing "Given the initialized notification, When handled, Then there is no response"
    (is (nil? (mcp/handle-request db {:method "notifications/initialized"})))))

(deftest tools-list-advertises-all-tools
  (testing "Given tools/list, When handled, Then every tool spec is advertised"
    (let [resp (mcp/handle-request db {:method "tools/list" :id 2 :params {}})
          names (set (map :name (get-in resp [:result :tools])))]
      (is (contains? names "search_matches"))
      (is (contains? names "team_record"))
      (is (contains? names "head_to_head"))
      (is (contains? names "standings"))
      (is (contains? names "search_players"))
      (is (= (count tools/tool-specs) (count (get-in resp [:result :tools])))))))

(deftest tools-call-returns-text-content
  (testing "Given a tools/call for search_matches, When handled, Then text content returns"
    (let [resp (mcp/handle-request
                db {:method "tools/call" :id 3
                    :params {"name" "search_matches"
                             "arguments" {"team" "Flamengo" "opponent" "Palmeiras"}}})
          text (get-in resp [:result :content 0 :text])]
      (is (= "text" (get-in resp [:result :content 0 :type])))
      (is (str/includes? text "Flamengo"))
      (is (str/includes? text "Palmeiras")))))

(deftest unknown-tool-is-rpc-error
  (testing "Given an unknown tool, When called, Then a JSON-RPC method-not-found error returns"
    (let [resp (mcp/handle-request
                db {:method "tools/call" :id 4
                    :params {"name" "does_not_exist" "arguments" {}}})]
      (is (= -32601 (get-in resp [:error :code]))))))

(deftest full-stdio-roundtrip
  (testing "Given JSON lines on stdin, When served, Then valid JSON-RPC lines come back"
    (let [requests (str (json/write-str {:jsonrpc "2.0" :id 1 :method "initialize" :params {}}) "\n"
                        (json/write-str {:jsonrpc "2.0" :method "notifications/initialized"}) "\n"
                        (json/write-str {:jsonrpc "2.0" :id 2 :method "tools/list" :params {}}) "\n"
                        (json/write-str {:jsonrpc "2.0" :id 3 :method "tools/call"
                                         :params {:name "list_competitions" :arguments {}}}) "\n")
          in  (ByteArrayInputStream. (.getBytes requests "UTF-8"))
          out (ByteArrayOutputStream.)]
      (mcp/serve db in out)
      (let [lines (->> (str/split-lines (str out)) (remove str/blank?))
            msgs  (map #(json/read-str % :key-fn keyword) lines)]
        ;; initialize + tools/list + tools/call => 3 replies (notification is silent)
        (is (= 3 (count msgs)))
        (is (= [1 2 3] (map :id msgs)))
        (is (str/includes? (get-in (last msgs) [:result :content 0 :text])
                           "Competitions"))))))

(deftest call-tool-coerces-string-args
  (testing "Given numeric args as strings, When calling, Then they are coerced"
    (let [text (tools/call-tool db "standings" {"season" "2023"})]
      (is (str/includes? text "standings"))
      (is (str/includes? text "Flamengo")))))
