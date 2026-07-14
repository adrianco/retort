(ns brazilian-soccer-mcp.mcp-test
  "Tests for the MCP JSON-RPC layer."
  (:require [brazilian-soccer-mcp.data  :as data]
            [brazilian-soccer-mcp.mcp   :as mcp]
            [brazilian-soccer-mcp.tools :as tools]
            [cheshire.core :as json]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing use-fixtures]])
  (:import (java.io ByteArrayInputStream ByteArrayOutputStream)))

(def ^:dynamic *ds* nil)

(defn- with-dataset [t]
  (binding [*ds* (data/load-dataset "data/kaggle")]
    (t)))

(use-fixtures :once with-dataset)

(deftest initialize-response
  (testing "Scenario: initialize returns protocol metadata"
    (let [resp (mcp/handle-request *ds* {:jsonrpc "2.0" :id 1 :method "initialize"})]
      (is (= 1 (:id resp)))
      (is (some? (get-in resp [:result :protocolVersion])))
      (is (some? (get-in resp [:result :serverInfo :name]))))))

(deftest tools-list-response
  (testing "Scenario: tools/list returns every registered tool"
    (let [resp (mcp/handle-request *ds* {:id 2 :method "tools/list"})
          tools (get-in resp [:result :tools])]
      (is (= (count tools/tools) (count tools)))
      (is (every? #(and (:name %) (:description %) (:inputSchema %)) tools)))))

(deftest tools-call-response
  (testing "Scenario: tools/call invokes a tool and returns its text"
    (let [resp (mcp/handle-request *ds*
                 {:id 3 :method "tools/call"
                  :params {:name "dataset_summary" :arguments {}}})]
      (is (false? (get-in resp [:result :isError])))
      (is (str/includes?
            (get-in resp [:result :content 0 :text])
            "Matches loaded"))))

  (testing "Scenario: unknown tools return an error string in the content block"
    (let [resp (mcp/handle-request *ds*
                 {:id 4 :method "tools/call"
                  :params {:name "does_not_exist" :arguments {}}})]
      (is (str/includes? (get-in resp [:result :content 0 :text])
                         "Unknown tool"))))

  (testing "Scenario: search_matches honours filter arguments"
    (let [resp (mcp/handle-request *ds*
                 {:id 5 :method "tools/call"
                  :params {:name "search_matches"
                           :arguments {:team "Flamengo" :season 2019
                                       :competition "Brasileirão" :limit 5}}})
          text (get-in resp [:result :content 0 :text])]
      (is (str/includes? text "Matches found: 5"))
      (is (str/includes? text "Flamengo")))))

(deftest method-not-found
  (testing "Scenario: unknown JSON-RPC methods return error -32601"
    (let [resp (mcp/handle-request *ds* {:id 99 :method "bogus"})]
      (is (= -32601 (get-in resp [:error :code]))))))

(deftest stdio-roundtrip
  (testing "Scenario: a newline-delimited JSON-RPC client can drive the server"
    (let [in   (ByteArrayInputStream.
                 (.getBytes
                   (str
                     (json/generate-string {:jsonrpc "2.0" :id 1 :method "initialize"}) "\n"
                     (json/generate-string {:jsonrpc "2.0" :id 2 :method "tools/list"}) "\n"
                     (json/generate-string {:jsonrpc "2.0" :id 3 :method "tools/call"
                                            :params {:name "dataset_summary"}}) "\n")
                   "UTF-8"))
          out  (ByteArrayOutputStream.)]
      (mcp/serve! *ds* in out)
      (let [lines    (str/split (.toString out "UTF-8") #"\n")
            messages (mapv #(json/parse-string % true) (remove str/blank? lines))]
        (is (= 3 (count messages)))
        (is (= [1 2 3] (mapv :id messages)))
        (is (some? (get-in (first messages) [:result :protocolVersion])))
        (is (pos? (count (get-in (second messages) [:result :tools]))))
        (is (str/includes?
              (get-in (last messages) [:result :content 0 :text])
              "Matches loaded"))))))
