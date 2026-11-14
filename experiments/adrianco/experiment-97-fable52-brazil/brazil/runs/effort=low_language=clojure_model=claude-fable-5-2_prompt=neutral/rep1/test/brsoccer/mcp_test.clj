(ns brsoccer.mcp-test
  "Feature: the server speaks MCP (JSON-RPC 2.0, newline-delimited) correctly."
  (:require [brsoccer.data :as data]
            [brsoccer.mcp :as mcp]
            [brsoccer.tools :as tools]
            [clojure.data.json :as json]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]])
  (:import (java.io BufferedReader StringReader StringWriter)))

(def ^:private db (delay (data/db)))

(defn- rpc [msg]
  (some-> (mcp/handle-line db (json/write-str msg)) json/read-str))

(deftest initialize-handshake
  (testing "When a client initializes with a supported protocol version"
    (let [r (rpc {:jsonrpc "2.0" :id 1 :method "initialize"
                  :params {:protocolVersion "2024-11-05" :capabilities {}
                           :clientInfo {:name "test" :version "0"}}})]
      (testing "Then the server echoes that version and advertises tools"
        (is (= "2.0" (r "jsonrpc")))
        (is (= 1 (r "id")))
        (is (= "2024-11-05" (get-in r ["result" "protocolVersion"])))
        (is (map? (get-in r ["result" "capabilities" "tools"])))
        (is (= "brazilian-soccer-mcp" (get-in r ["result" "serverInfo" "name"]))))))
  (testing "When the client asks for an unknown version, the server offers its latest"
    (is (= (first mcp/supported-versions)
           (get-in (rpc {:jsonrpc "2.0" :id 2 :method "initialize" :params {:protocolVersion "1999-01-01"}})
                   ["result" "protocolVersion"]))))
  (testing "initialize does not force the data to load"
    (let [lazy (delay (throw (Exception. "should not load")))]
      (is (some? (mcp/handle-message lazy {"jsonrpc" "2.0" "id" 1 "method" "initialize" "params" {}})))
      (is (not (realized? lazy))))))

(deftest notifications-get-no-reply
  (is (nil? (rpc {:jsonrpc "2.0" :method "notifications/initialized"})))
  (is (nil? (rpc {:jsonrpc "2.0" :method "notifications/cancelled" :params {:requestId 3}})))
  (is (nil? (rpc {:jsonrpc "2.0" :method "some/unknown-notification"}))))

(deftest ping
  (is (= {"jsonrpc" "2.0" "id" "abc" "result" {}} (rpc {:jsonrpc "2.0" :id "abc" :method "ping"}))))

(deftest tools-list
  (let [ts (get-in (rpc {:jsonrpc "2.0" :id 1 :method "tools/list"}) ["result" "tools"])]
    (is (= (count tools/tools) (count ts)))
    (is (apply distinct? (map #(% "name") ts)))
    (doseq [t ts]
      (testing (t "name")
        (is (re-matches #"[a-z_]+" (t "name")))
        (is (not (str/blank? (t "description"))))
        (is (= "object" (get-in t ["inputSchema" "type"])))
        (is (every? #(and (% "type") true) (vals (get-in t ["inputSchema" "properties"]))))
        (is (every? (set (keys (get-in t ["inputSchema" "properties"])))
                    (get-in t ["inputSchema" "required"])))
        (is (not (contains? t "handler")))))))

(deftest tools-call
  (testing "When a tool is called with valid arguments"
    (let [r (rpc {:jsonrpc "2.0" :id 7 :method "tools/call"
                  :params {:name "standings" :arguments {:season 2019 :limit 3}}})]
      (is (= 7 (r "id")))
      (is (false? (get-in r ["result" "isError"])))
      (is (= "text" (get-in r ["result" "content" 0 "type"])))
      (is (str/includes? (get-in r ["result" "content" 0 "text"]) "1. Flamengo - 90 pts"))))
  (testing "When arguments are omitted for a tool that needs none"
    (is (false? (get-in (rpc {:jsonrpc "2.0" :id 8 :method "tools/call" :params {:name "dataset_info"}})
                        ["result" "isError"]))))
  (testing "When the tool rejects its input, the result is flagged isError (not a protocol error)"
    (let [r (rpc {:jsonrpc "2.0" :id 9 :method "tools/call"
                  :params {:name "team_stats" :arguments {:team "Xyzzy United"}}})]
      (is (true? (get-in r ["result" "isError"])))
      (is (str/includes? (get-in r ["result" "content" 0 "text"]) "Unknown team"))))
  (testing "When the tool does not exist, a JSON-RPC invalid-params error is returned"
    (is (= -32602 (get-in (rpc {:jsonrpc "2.0" :id 10 :method "tools/call" :params {:name "nope"}})
                          ["error" "code"])))
    (is (= -32602 (get-in (rpc {:jsonrpc "2.0" :id 11 :method "tools/call" :params {}})
                          ["error" "code"])))
    (is (= -32602 (get-in (rpc {:jsonrpc "2.0" :id 12 :method "tools/call"
                                :params {:name "standings" :arguments [2019]}})
                          ["error" "code"])))))

(deftest protocol-errors
  (testing "unknown method"
    (is (= -32601 (get-in (rpc {:jsonrpc "2.0" :id 1 :method "resources/list"}) ["error" "code"]))))
  (testing "malformed JSON"
    (let [r (json/read-str (mcp/handle-line db "{not json"))]
      (is (= -32700 (get-in r ["error" "code"])))
      (is (nil? (r "id")))))
  (testing "a JSON value that is not a request"
    (is (= -32600 (get-in (json/read-str (mcp/handle-line db "42")) ["error" "code"])))
    (is (= -32600 (get-in (json/read-str (mcp/handle-line db "[]")) ["error" "code"]))))
  (testing "a stray response from the client is ignored"
    (is (nil? (mcp/handle-line db "{\"jsonrpc\":\"2.0\",\"id\":5,\"result\":{}}")))))

(deftest stdio-session
  (testing "Given a full client session on the wire"
    (let [lines [(json/write-str {:jsonrpc "2.0" :id 1 :method "initialize"
                                  :params {:protocolVersion "2025-06-18"}})
                 (json/write-str {:jsonrpc "2.0" :method "notifications/initialized"})
                 ""
                 (json/write-str {:jsonrpc "2.0" :id 2 :method "tools/list"})
                 (json/write-str {:jsonrpc "2.0" :id 3 :method "tools/call"
                                  :params {:name "search_matches"
                                           :arguments {:team "São Paulo" :opponent "Grêmio" :limit 2}}})]
          out   (StringWriter.)]
      (mcp/serve db (BufferedReader. (StringReader. (str/join "\n" lines))) out)
      (let [replies (str/split-lines (str out))]
        (testing "Then exactly one single-line JSON reply is written per request"
          (is (= [1 2 3] (map #((json/read-str %) "id") replies))))
        (testing "And Portuguese characters go out as real UTF-8, not escapes"
          (is (str/includes? (last replies) "São Paulo vs Grêmio"))
          (is (not (str/includes? (last replies) "\\u00"))))))))
