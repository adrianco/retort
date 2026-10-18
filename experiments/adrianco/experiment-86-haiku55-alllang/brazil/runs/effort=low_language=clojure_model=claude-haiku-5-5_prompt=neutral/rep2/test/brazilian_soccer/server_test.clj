(ns brazilian-soccer.server-test
  (:require [brazilian-soccer.fixtures :as fx]
            [clojure.string :as str]
            [brazilian-soccer.json :as json]
            [brazilian-soccer.server :as server]
            [clojure.test :refer [deftest is testing]]))

(def ctx {:matches fx/matches :players fx/players})

(defn- call [method params]
  (server/handle-message ctx {"jsonrpc" "2.0" "id" 1 "method" method "params" params}))

(defn- text-of [resp]
  (get-in resp [:result :content 0 :text]))

(deftest initialize-advertises-tools
  (let [r (call "initialize" {})]
    (is (= "2.0" (:jsonrpc r)))
    (is (contains? (get-in r [:result :capabilities]) :tools))
    (is (= "brazilian-soccer-mcp" (get-in r [:result :serverInfo :name])))))

(deftest tools-list-names-every-tool
  (let [names (set (map :name (:tools (:result (call "tools/list" {})))))]
    (is (= #{"search_matches" "team_record" "head_to_head" "standings"
             "league_stats" "search_players" "brazilian_club_summary"}
           names))))

(deftest tools-call-returns-text-content
  (let [r (call "tools/call" {"name" "search_matches" "arguments" {"team" "Flamengo" "season" 2023}})]
    (is (false? (get-in r [:result :isError])))
    (is (re-find #"^Found 3 matches" (text-of r)))
    (is (re-find #"2023-09-03: Flamengo 2-1 Fluminense" (text-of r)))))

(deftest tools-call-answers-team-record-question
  (let [text (text-of (call "tools/call" {"name" "team_record"
                                          "arguments" {"team" "Corinthians" "season" 2022}}))]
    (is (re-find #"Unknown team" text) "unknown team is reported as a tool error"))
  (let [r (call "tools/call" {"name" "team_record" "arguments" {"team" "Flamengo" "season" 2023}})]
    (is (re-find #"Wins: 1, Draws: 1, Losses: 1" (text-of r)))))

(deftest tool-errors-are-reported-not-thrown
  (let [r (call "tools/call" {"name" "team_record" "arguments" {"team" "Nobody"}})]
    (is (true? (get-in r [:result :isError])))))

(deftest unknown-tool-and-method-are-json-rpc-errors
  (is (= -32602 (get-in (call "tools/call" {"name" "nope"}) [:error :code])))
  (is (= -32601 (get-in (call "bogus" {}) [:error :code]))))

(deftest notifications-get-no-response
  (is (nil? (server/handle-message ctx {"jsonrpc" "2.0" "method" "notifications/initialized"}))))

(deftest handle-line-encodes-and-reports-parse-errors
  (let [out (server/handle-line ctx "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"ping\"}")]
    (is (= {"jsonrpc" "2.0" "id" 7 "result" {}} (json/decode out))))
  (is (= -32700 (get-in (json/decode (server/handle-line ctx "{bad")) ["error" "code"]))))

(deftest serve-processes-a-session
  (let [in (java.io.StringReader.
            (str "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}\n"
                 "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}\n"
                 "\n"
                 "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}\n"))
        out (java.io.StringWriter.)]
    (server/serve ctx (java.io.BufferedReader. in) out)
    (let [lines (str/split-lines (str out))]
      (is (= 2 (count lines)))
      (is (= [1 2] (map #(get (json/decode %) "id") lines))))))
