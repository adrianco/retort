(ns brazilian-soccer.server-test
  "Feature: MCP protocol server

  Scenario: A client performs the initialize handshake
  Scenario: A client lists the available tools
  Scenario: A client calls tools and receives text answers
  Scenario: At least 20 sample questions can be answered via the tools"
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.server :as server]
            [brazilian-soccer.tools :as tools]
            [clojure.data.json :as json]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]))

(def db (delay @data/db))

(defn- rpc [method params id]
  (server/handle-request @db {"jsonrpc" "2.0" "id" id "method" method "params" params}))

(defn- call-text
  "Calls a tool through the JSON-RPC layer and returns the text answer."
  [tool args]
  (let [resp (rpc "tools/call" {"name" tool "arguments" args} 99)
        result (:result resp)]
    (is (not (:isError result)) (str tool " should not error: " result))
    (-> result :content first :text)))

;; ---------------------------------------------------------------------------

(deftest initialize-handshake
  (testing "When the client sends initialize"
    (let [resp (rpc "initialize" {"protocolVersion" "2024-11-05"
                                  "capabilities" {}
                                  "clientInfo" {"name" "test" "version" "1"}} 1)]
      (testing "Then the server replies with its protocol version and capabilities"
        (is (= "2.0" (:jsonrpc resp)))
        (is (= 1 (:id resp)))
        (is (= "2024-11-05" (get-in resp [:result :protocolVersion])))
        (is (some? (get-in resp [:result :capabilities :tools])))
        (is (= "brazilian-soccer-mcp" (get-in resp [:result :serverInfo :name])))))))

(deftest notifications-get-no-response
  (testing "When the client sends a notification (no id)"
    (is (nil? (server/handle-request @db {"jsonrpc" "2.0"
                                          "method" "notifications/initialized"})))))

(deftest ping
  (is (= {} (:result (rpc "ping" nil 7)))))

(deftest unknown-method-returns-error
  (let [resp (rpc "bogus/method" {} 5)]
    (is (= -32601 (get-in resp [:error :code])))))

(deftest malformed-json-returns-parse-error
  (let [out (server/handle-line @db "{not json")]
    (is (= -32700 (get-in (json/read-str out :key-fn keyword) [:error :code])))))

(deftest tools-list
  (testing "When the client requests tools/list"
    (let [ts (get-in (rpc "tools/list" nil 2) [:result :tools])]
      (testing "Then all tools are advertised with schemas"
        (is (= 11 (count ts)))
        (doseq [t ts]
          (is (string? (:name t)))
          (is (seq (:description t)))
          (is (= "object" (get-in t [:inputSchema :type]))))
        (is (= #{"search_matches" "head_to_head" "get_team_stats" "get_standings"
                 "get_competition_stats" "get_biggest_wins" "get_best_records"
                 "search_players" "get_player" "get_extended_match_stats"
                 "list_competitions"}
               (set (map :name ts))))))))

(deftest tools-call-roundtrip
  (testing "When the client calls search_matches over JSON-RPC"
    (let [text (call-text "search_matches" {"team" "Flamengo" "opponent" "Fluminense" "limit" 5})]
      (is (str/includes? text "Flamengo"))
      (is (str/includes? text "Fluminense"))
      (is (re-find #"\d+-\d+" text) "includes scores"))))

(deftest tools-call-unknown-tool
  (let [result (:result (rpc "tools/call" {"name" "nope" "arguments" {}} 3))]
    (is (:isError result))
    (is (str/includes? (-> result :content first :text) "Unknown tool"))))

(deftest tools-call-handles-bad-arguments-gracefully
  (testing "Missing/odd arguments produce a text answer, not a crash"
    (is (string? (call-text "search_matches" {})))
    (is (string? (call-text "search_matches" {"season" "2019"})) "string season coerced")
    (is (str/includes? (call-text "get_team_stats" {"team" "Nonexistent United FC"})
                       "No completed matches"))))

(deftest stdio-line-protocol
  (testing "When a raw JSON line arrives, a single JSON line is returned"
    (let [out (server/handle-line
               @db
               (json/write-str {:jsonrpc "2.0" :id 42 :method "tools/call"
                                :params {:name "list_competitions" :arguments {}}}))
          resp (json/read-str out :key-fn keyword)]
      (is (= 42 (:id resp)))
      (is (str/includes? (-> resp :result :content first :text) "Brasileirão Série A"))
      (testing "And accented characters survive the JSON round trip"
        (is (str/includes? (-> resp :result :content first :text) "Série"))))))

;; ---------------------------------------------------------------------------
;; Feature: the 20+ sample questions from the specification

(def sample-questions
  "question -> [tool args expected-regex]"
  [["Show me all Flamengo vs Fluminense matches"
    "search_matches" {"team" "Flamengo" "opponent" "Fluminense"} #"Flamengo"]
   ["What matches did Palmeiras play in 2023?"
    "search_matches" {"team" "Palmeiras" "season" 2023} #"Palmeiras"]
   ["Find Copa do Brasil matches for Grêmio"
    "search_matches" {"team" "Grêmio" "competition" "Copa do Brasil"} #"(?i)gremio|grêmio"]
   ["When did Flamengo last play Corinthians? What was the score?"
    "search_matches" {"team" "Flamengo" "opponent" "Corinthians" "limit" 1} #"\d+-\d+"]
   ["Find all Libertadores finals"
    "search_matches" {"competition" "Libertadores" "date_from" "2019-01-01"} #"final|Libertadores"]
   ["What is Corinthians' home record in 2022?"
    "get_team_stats" {"team" "Corinthians" "season" 2022 "venue" "home"} #"Wins: \d+"]
   ["How did São Paulo do in the 2019 Brasileirão?"
    "get_team_stats" {"team" "São Paulo" "season" 2019 "competition" "Serie A"} #"Win rate"]
   ["Compare Palmeiras and Santos head-to-head"
    "head_to_head" {"team1" "Palmeiras" "team2" "Santos"} #"wins"]
   ["Show me Fla-Flu derby history"
    "head_to_head" {"team1" "Flamengo" "team2" "Fluminense"} #"Matches: \d+"]
   ["Who won the 2019 Brasileirão?"
    "get_standings" {"season" 2019} #"1\. Flamengo.*Champion"]
   ["Which teams were relegated in 2019?"
    "get_standings" {"season" 2019} #"Relegation zone"]
   ["Show the 2008 Brasileirão table"
    "get_standings" {"season" 2008} #"1\. .*Champion"]
   ["What's the average goals per match in the Brasileirão?"
    "get_competition_stats" {"competition" "brasileirao"} #"Average goals per match: \d"]
   ["Compare the 2018 and 2019 seasons (2018 half)"
    "get_competition_stats" {"competition" "brasileirao" "season" 2018} #"Matches: 380"]
   ["Compare the 2018 and 2019 seasons (2019 half)"
    "get_competition_stats" {"competition" "brasileirao" "season" 2019} #"Matches: 380"]
   ["Show me the biggest wins in the dataset"
    "get_biggest_wins" {"limit" 5} #"\d+-\d+"]
   ["Which team has the best home record?"
    "get_best_records" {"venue" "home" "min_matches" 100} #"1\. .*win rate"]
   ["Which team has the best away record?"
    "get_best_records" {"venue" "away" "min_matches" 100} #"1\. .*win rate"]
   ["Find all Brazilian players in the dataset"
    "search_players" {"nationality" "Brazil"} #"827 player"]
   ["Who are the highest-rated players at Grêmio?"
    "search_players" {"club" "Gremio"} #"Grêmio"]
   ["Show me forwards from FC Barcelona"
    "search_players" {"club" "Barcelona" "position" "ST"} #"Barcelona"]
   ["Who is Neymar?"
    "get_player" {"name" "Neymar"} #"Overall: 92"]
   ["Top young Brazilian talents"
    "search_players" {"nationality" "Brazil" "max_age" 21 "min_overall" 75} #"player"]
   ["How many corners does Flamengo average?"
    "get_extended_match_stats" {"team" "Flamengo"} #"Avg corners"]
   ["What competitions are covered?"
    "list_competitions" {} #"Copa do Brasil"]])

(deftest twenty-plus-sample-questions
  (testing "At least 20 sample questions can be answered"
    (is (>= (count sample-questions) 20))
    (doseq [[question tool args expected] sample-questions]
      (testing question
        (let [text (call-text tool args)]
          (is (re-find expected text)
              (str "Answer for \"" question "\" was:\n" text)))))))

;; ---------------------------------------------------------------------------
;; Feature: response time over the protocol layer

(deftest protocol-performance
  (let [_ @db]
    (testing "Simple tool calls complete in under 2 seconds"
      (let [t0 (System/nanoTime)
            _ (call-text "search_matches" {"team" "Santos" "limit" 5})
            ms (/ (- (System/nanoTime) t0) 1e6)]
        (is (< ms 2000))))
    (testing "Aggregate tool calls complete in under 5 seconds"
      (let [t0 (System/nanoTime)
            _ (call-text "get_best_records" {"venue" "away"})
            ms (/ (- (System/nanoTime) t0) 1e6)]
        (is (< ms 5000))))))

(comment
  ;; Exercise every tool against the live data:
  (doseq [t (tools/list-tools)] (println (:name t))))
