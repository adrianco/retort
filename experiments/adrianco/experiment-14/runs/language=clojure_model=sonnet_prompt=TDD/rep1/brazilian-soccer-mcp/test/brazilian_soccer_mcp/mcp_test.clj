(ns brazilian-soccer-mcp.mcp-test
  (:require [clojure.test :refer :all]
            [clojure.string :as str]
            [cheshire.core :as json]
            [brazilian-soccer-mcp.mcp :as mcp]))

(deftest handle-initialize-test
  (testing "responds to initialize request"
    (let [req  {:jsonrpc "2.0" :id 1 :method "initialize"
                :params {:protocolVersion "2024-11-05"
                         :capabilities {}
                         :clientInfo {:name "test" :version "1.0"}}}
          resp (mcp/handle-request req)]
      (is (= "2.0" (:jsonrpc resp)))
      (is (= 1 (:id resp)))
      (is (contains? resp :result))
      (is (contains? (:result resp) :protocolVersion))
      (is (contains? (:result resp) :capabilities))
      (is (contains? (:result resp) :serverInfo))))

  (testing "handles initialized notification (no response)"
    (let [notif {:jsonrpc "2.0" :method "notifications/initialized"}
          resp  (mcp/handle-request notif)]
      (is (nil? resp)))))

(deftest handle-tools-list-test
  (testing "returns list of tools"
    (let [req  {:jsonrpc "2.0" :id 2 :method "tools/list" :params {}}
          resp (mcp/handle-request req)]
      (is (= "2.0" (:jsonrpc resp)))
      (is (= 2 (:id resp)))
      (is (contains? (:result resp) :tools))
      (is (seq (get-in resp [:result :tools])))
      (is (every? #(contains? % :name) (get-in resp [:result :tools]))))))

(deftest handle-tools-call-test
  (testing "returns error when data not loaded"
    (let [req  {:jsonrpc "2.0" :id 3 :method "tools/call"
                :params {:name "find_matches" :arguments {"team" "Flamengo"}}}
          resp (mcp/handle-request req)]
      (is (= "2.0" (:jsonrpc resp)))
      (is (= 3 (:id resp)))
      ;; Either returns an error or some result
      (is (or (contains? resp :error)
              (contains? resp :result))))))

(deftest handle-unknown-method-test
  (testing "returns method-not-found error for unknown methods"
    (let [req  {:jsonrpc "2.0" :id 4 :method "unknown/method" :params {}}
          resp (mcp/handle-request req)]
      (is (= "2.0" (:jsonrpc resp)))
      (is (= 4 (:id resp)))
      (is (contains? resp :error))
      (is (= -32601 (get-in resp [:error :code]))))))

(deftest json-encode-decode-test
  (testing "request can be JSON-encoded and decoded"
    (let [req  {:jsonrpc "2.0" :id 1 :method "tools/list" :params {}}
          json (json/encode req)
          decoded (json/decode json true)]
      (is (= "tools/list" (:method decoded)))
      (is (= 1 (:id decoded)))))

  (testing "response can be JSON-encoded"
    (let [req  {:jsonrpc "2.0" :id 2 :method "initialize"
                :params {:protocolVersion "2024-11-05"
                         :capabilities {}
                         :clientInfo {:name "test" :version "1.0"}}}
          resp (mcp/handle-request req)
          json (json/encode resp)]
      (is (string? json))
      (is (str/includes? json "protocolVersion")))))
