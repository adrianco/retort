(ns brazilian-soccer.mcp-test
  "JSON-RPC / MCP protocol conformance.

  CONTEXT
  -------
  Drives the server the way a client does - by feeding it the exact JSON lines
  of a session (initialize, initialized notification, tools/list, tools/call)
  and reading the lines it writes back.  `serve` is exercised over real streams
  so the framing is tested too, not just the dispatch function."
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.fixtures :refer [test-db]]
            [brazilian-soccer.mcp :as mcp]))

(defn- call [db message]
  (some-> (mcp/handle-line db (json/write-str message)) json/read-str))

(deftest initialize-handshake
  (let [db (test-db)
        response (call db {"jsonrpc" "2.0" "id" 1 "method" "initialize"
                           "params" {"protocolVersion" "2024-11-05"
                                     "capabilities" {}
                                     "clientInfo" {"name" "test" "version" "1"}}})]
    (is (= "2.0" (get response "jsonrpc")))
    (is (= 1 (get response "id")))
    (is (= "2024-11-05" (get-in response ["result" "protocolVersion"])))
    (is (contains? (get-in response ["result" "capabilities"]) "tools"))
    (is (= "brazilian-soccer" (get-in response ["result" "serverInfo" "name"])))
    (is (string? (get-in response ["result" "instructions"]))))
  (testing "a newer protocol version the server understands is echoed back"
    (is (= "2025-06-18"
           (get-in (call (test-db) {"jsonrpc" "2.0" "id" 2 "method" "initialize"
                                    "params" {"protocolVersion" "2025-06-18"}})
                   ["result" "protocolVersion"])))))

(deftest notifications-are-not-answered
  (is (nil? (mcp/handle-line (test-db)
                             (json/write-str {"jsonrpc" "2.0" "method" "notifications/initialized"})))
      "a notification has no id and must produce no response line"))

(deftest ping
  (is (= {} (get (call (test-db) {"jsonrpc" "2.0" "id" 3 "method" "ping"}) "result"))))

(deftest tools-list
  (let [response (call (test-db) {"jsonrpc" "2.0" "id" 4 "method" "tools/list"})
        tools (get-in response ["result" "tools"])]
    (is (seq tools))
    (is (every? #(and (string? (get % "name"))
                      (string? (get % "description"))
                      (map? (get % "inputSchema")))
                tools))
    (is (some #(= "search_matches" (get % "name")) tools))))

(deftest tools-call
  (let [db (test-db)
        response (call db {"jsonrpc" "2.0" "id" 5 "method" "tools/call"
                           "params" {"name" "standings"
                                     "arguments" {"competition" "brasileirao" "season" 2019}}})
        content (get-in response ["result" "content"])]
    (is (false? (get-in response ["result" "isError"])))
    (is (= 1 (count content)))
    (is (= "text" (get-in content [0 "type"])))
    (is (str/includes? (get-in content [0 "text"]) "Flamengo"))))

(deftest tool-failures-are-results-not-protocol-errors
  (testing "MCP wants tool errors reported so the model can read and retry them"
    (let [response (call (test-db) {"jsonrpc" "2.0" "id" 6 "method" "tools/call"
                                    "params" {"name" "team_stats" "arguments" {"team" "Atletico"}}})]
      (is (nil? (get response "error")))
      (is (true? (get-in response ["result" "isError"])))
      (is (str/includes? (get-in response ["result" "content" 0 "text"]) "Atlético Mineiro"))))
  (testing "an unknown tool is also a tool error"
    (let [response (call (test-db) {"jsonrpc" "2.0" "id" 7 "method" "tools/call"
                                    "params" {"name" "nope" "arguments" {}}})]
      (is (true? (get-in response ["result" "isError"]))))))

(deftest protocol-errors
  (testing "unknown methods"
    (let [response (call (test-db) {"jsonrpc" "2.0" "id" 8 "method" "resources/list"})]
      (is (= -32601 (get-in response ["error" "code"])))))
  (testing "malformed JSON"
    (let [response (json/read-str (mcp/handle-line (test-db) "{not json"))]
      (is (= -32700 (get-in response ["error" "code"])))))
  (testing "a JSON value that is not an object"
    (let [response (json/read-str (mcp/handle-line (test-db) "[1,2,3]"))]
      (is (= -32600 (get-in response ["error" "code"]))))))

(deftest full-session-over-streams
  (testing "a realistic client session, framed as newline delimited JSON"
    (let [db (test-db)
          session (str/join "\n"
                            [(json/write-str {"jsonrpc" "2.0" "id" 1 "method" "initialize"
                                              "params" {"protocolVersion" "2024-11-05"}})
                             (json/write-str {"jsonrpc" "2.0" "method" "notifications/initialized"})
                             (json/write-str {"jsonrpc" "2.0" "id" 2 "method" "tools/list"})
                             (json/write-str {"jsonrpc" "2.0" "id" 3 "method" "tools/call"
                                              "params" {"name" "head_to_head"
                                                        "arguments" {"team_a" "Flamengo"
                                                                     "team_b" "Fluminense"}}})])
          out (java.io.ByteArrayOutputStream.)]
      (mcp/serve db (java.io.ByteArrayInputStream. (.getBytes session "UTF-8")) out)
      (let [lines (str/split-lines (str/trim (.toString out "UTF-8")))
            responses (map json/read-str lines)]
        (is (= 3 (count responses)) "the notification must not be answered")
        (is (= [1 2 3] (map #(get % "id") responses)))
        (is (str/includes? (get-in (last responses) ["result" "content" 0 "text"]) "Fla"))
        (testing "UTF-8 survives the round trip"
          (is (str/includes? (get-in (last responses) ["result" "content" 0 "text"])
                             "Brasileirão")))))))
