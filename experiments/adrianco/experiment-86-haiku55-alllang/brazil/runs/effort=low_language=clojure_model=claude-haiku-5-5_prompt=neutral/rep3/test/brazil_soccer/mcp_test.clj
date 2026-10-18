(ns brazil-soccer.mcp-test
  (:require [cheshire.core :as json]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [brazil-soccer.mcp :as mcp]
            [brazil-soccer.tools :as tools]
            [brazil-soccer.support :refer [small-db]])
  (:import [java.io StringReader StringWriter]))

(def ^:private registry (tools/tools small-db))

(defn- rpc [msg]
  (mcp/handle-message msg registry))

(deftest initialize_advertises_the_tools_capability
  (testing "Given an initialize request, then the server reports the protocol version and tools capability"
    (let [res (rpc {:id 1 :method "initialize" :params {}})]
      (is (= 1 (:id res)))
      (is (= mcp/protocol-version (get-in res [:result :protocolVersion])))
      (is (contains? (get-in res [:result :capabilities]) :tools))
      (is (= "brazilian-soccer-mcp" (get-in res [:result :serverInfo :name]))))))

(deftest notifications_get_no_reply
  (testing "Given a notification with no id, then no response is produced"
    (is (nil? (rpc {:method "notifications/initialized"})))))

(deftest tools_list_describes_every_tool
  (testing "Given tools/list, then each tool has a name, description and input schema"
    (let [tools (get-in (rpc {:id 2 :method "tools/list"}) [:result :tools])]
      (is (= 9 (count tools)))
      (is (every? #(and (:name %) (:description %) (:inputSchema %)) tools)))))

(deftest tools_call_returns_text_content
  (testing "Given a tools/call with arguments, then the reply is text content for the model"
    (let [res (rpc {:id 3 :method "tools/call"
                    :params {:name "team_record" :arguments {:team "Flamengo" :season 2020}}})]
      (is (false? (get-in res [:result :isError])))
      (is (str/includes? (get-in res [:result :content 0 :text]) "- Matches: 6"))))
  (testing "Given a tool failure, then the reply is marked as a tool error with the message"
    (let [res (rpc {:id 4 :method "tools/call"
                    :params {:name "find_matches" :arguments {:competition "Nope"}}})]
      (is (true? (get-in res [:result :isError])))
      (is (str/includes? (get-in res [:result :content 0 :text]) "Unknown competition")))))

(deftest protocol_errors_use_json_rpc_codes
  (testing "Given an unknown tool, then the error code is invalid params"
    (is (= -32602 (get-in (rpc {:id 5 :method "tools/call" :params {:name "nope"}}) [:error :code]))))
  (testing "Given an unknown method, then the error code is method not found"
    (is (= -32601 (get-in (rpc {:id 6 :method "resources/list"}) [:error :code])))))

(deftest serve_reads_lines_and_writes_one_reply_each
  (testing "Given a session with a notification and a malformed line, then only requests get a reply"
    (let [input (str/join "\n"
                          [(json/generate-string {:jsonrpc "2.0" :id 1 :method "initialize"})
                           (json/generate-string {:jsonrpc "2.0" :method "notifications/initialized"})
                           "{not json"
                           (json/generate-string {:jsonrpc "2.0" :id 2 :method "ping"})])
          out (StringWriter.)]
      (mcp/serve (StringReader. input) out registry)
      (let [replies (map #(json/parse-string % true) (str/split-lines (str out)))]
        (is (= 3 (count replies)))
        (is (= [1 nil 2] (map :id replies)))
        (is (= -32700 (get-in (second replies) [:error :code])))))))
