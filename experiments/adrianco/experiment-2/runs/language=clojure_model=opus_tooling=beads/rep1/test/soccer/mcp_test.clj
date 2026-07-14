(ns soccer.mcp-test
  (:require [clojure.data.json :as json]
            [clojure.test :refer [deftest is testing]]
            [soccer.mcp :as mcp]))

(deftest initialize-test
  (let [resp (mcp/handle-request {"id" 1 "method" "initialize" "params" {}})]
    (is (= 1 (:id resp)))
    (is (= mcp/protocol-version (-> resp :result :protocolVersion)))))

(deftest tools-list-test
  (let [resp (mcp/handle-request {"id" 2 "method" "tools/list" "params" {}})
        names (map :name (-> resp :result :tools))]
    (is (some #{"head_to_head"} names))
    (is (some #{"standings"} names))
    (is (some #{"search_players"} names))))

(deftest tools-call-head-to-head-test
  (let [resp (mcp/handle-request
              {"id" 3 "method" "tools/call"
               "params" {"name" "head_to_head"
                         "arguments" {"team_a" "Palmeiras"
                                      "team_b" "Santos"}}})
        body (json/read-str (-> resp :result :content first :text)
                            :key-fn keyword)]
    (is (pos? (:matches body)))))

(deftest tools-call-search-players-test
  (let [resp (mcp/handle-request
              {"id" 4 "method" "tools/call"
               "params" {"name" "search_players"
                         "arguments" {"nationality" "Brazil" "limit" 3}}})
        body (json/read-str (-> resp :result :content first :text)
                            :key-fn keyword)]
    (is (= 3 (count body)))
    (is (every? #(= "Brazil" (:nationality %)) body))))

(deftest unknown-method-test
  (let [resp (mcp/handle-request {"id" 9 "method" "bogus" "params" {}})]
    (is (= -32601 (-> resp :error :code)))))
