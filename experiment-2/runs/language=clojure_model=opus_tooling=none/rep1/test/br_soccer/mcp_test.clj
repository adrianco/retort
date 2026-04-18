(ns br-soccer.mcp-test
  (:require [clojure.test :refer [deftest is testing]]
            [br-soccer.mcp :as mcp]
            [clojure.data.json :as json]))

(deftest tools-list-test
  (let [resp (mcp/handle-request {"jsonrpc" "2.0" "id" 1 "method" "tools/list"})]
    (is (= 1 (:id resp)))
    (is (pos? (count (get-in resp [:result :tools]))))))

(deftest tools-call-team-stats-test
  (let [resp (mcp/handle-request
              {"jsonrpc" "2.0" "id" 2 "method" "tools/call"
               "params" {"name" "team_stats"
                         "arguments" {"team" "Flamengo" "season" 2019}}})
        text (-> resp :result :content first :text)
        parsed (json/read-str text :key-fn keyword)]
    (is (= "Flamengo" (:team parsed)))
    (is (pos? (:matches parsed)))))

(deftest tools-call-head-to-head-test
  (let [resp (mcp/handle-request
              {"jsonrpc" "2.0" "id" 3 "method" "tools/call"
               "params" {"name" "head_to_head"
                         "arguments" {"team_a" "Flamengo"
                                      "team_b" "Fluminense"}}})
        parsed (-> resp :result :content first :text (json/read-str :key-fn keyword))]
    (is (pos? (:matches parsed)))))

(deftest initialize-test
  (let [resp (mcp/handle-request {"jsonrpc" "2.0" "id" 0 "method" "initialize"})]
    (is (= "br-soccer-mcp" (get-in resp [:result :serverInfo :name])))))
