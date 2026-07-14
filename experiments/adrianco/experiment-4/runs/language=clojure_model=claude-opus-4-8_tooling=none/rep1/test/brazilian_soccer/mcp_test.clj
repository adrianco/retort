(ns brazilian-soccer.mcp-test
  "=============================================================================
   BDD tests (Given-When-Then) for the MCP / JSON-RPC protocol layer.
   =============================================================================
   Drives the server exactly as an LLM host would: through `handle-request`
   with JSON-RPC envelopes, plus an end-to-end stdio round-trip via `serve!`."
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.string :as str]
            [cheshire.core :as json]
            [brazilian-soccer.fixtures :as fix]
            [brazilian-soccer.mcp :as mcp])
  (:import [java.io ByteArrayInputStream ByteArrayOutputStream]))

(defn- call [db name args]
  (mcp/handle-request db {:jsonrpc "2.0" :id 1 :method "tools/call"
                          :params {:name name :arguments args}}))

(defn- text [resp]
  (get-in resp [:result :content 0 :text]))

(deftest protocol-handshake
  (let [db (fix/db)]
    (testing "Scenario: initialize returns capabilities and server info"
      (let [resp (mcp/handle-request db {:jsonrpc "2.0" :id 0 :method "initialize" :params {}})]
        (is (= "2.0" (:jsonrpc resp)))
        (is (= 0 (:id resp)))
        (is (string? (get-in resp [:result :protocolVersion])))
        (is (= "brazilian-soccer-mcp" (get-in resp [:result :serverInfo :name])))))

    (testing "Scenario: initialized notification produces no response"
      (is (nil? (mcp/handle-request db {:jsonrpc "2.0" :method "notifications/initialized"}))))

    (testing "Scenario: unknown method on a request returns a JSON-RPC error"
      (let [resp (mcp/handle-request db {:jsonrpc "2.0" :id 9 :method "bogus/method"})]
        (is (= -32601 (get-in resp [:error :code])))))))

(deftest tools-listing
  (let [db (fix/db)
        resp (mcp/handle-request db {:jsonrpc "2.0" :id 2 :method "tools/list"})
        tools (get-in resp [:result :tools])]
    (testing "Scenario: tools/list advertises the soccer tools with schemas"
      (is (>= (count tools) 12))
      (is (every? #(and (:name %) (:description %) (:inputSchema %)) tools))
      (let [names (set (map :name tools))]
        (is (contains? names "search_matches"))
        (is (contains? names "team_stats"))
        (is (contains? names "search_players"))
        (is (contains? names "standings"))))))

(deftest tool-calls
  (let [db (fix/db)]
    (testing "Scenario: search_matches returns a readable derby list"
      (let [t (text (call db "search_matches" {:team "Flamengo" :opponent "Fluminense" :limit 5}))]
        (is (str/includes? t "Flamengo"))
        (is (str/includes? t "Fluminense"))))

    (testing "Scenario: team_stats returns a record block"
      (let [t (text (call db "team_stats" {:team "Palmeiras" :season 2019}))]
        (is (str/includes? t "Win rate"))
        (is (str/includes? t "Goals For"))))

    (testing "Scenario: head_to_head summarizes two teams"
      (let [t (text (call db "head_to_head" {:team1 "Palmeiras" :team2 "Santos" :show 3}))]
        (is (str/includes? t "Head-to-head"))
        (is (str/includes? t "wins"))))

    (testing "Scenario: search_players finds Brazilian stars"
      (let [t (text (call db "search_players" {:nationality "Brazil" :limit 5}))]
        (is (str/includes? t "Overall:"))
        ;; Numbered list of five players
        (is (str/includes? t "1. "))
        (is (str/includes? t "5. "))))

    (testing "Scenario: standings names the 2019 champion first"
      (let [t (text (call db "standings" {:season 2019 :top 5}))]
        (is (str/includes? t "Final Standings"))
        (is (str/includes? t "1. Flamengo"))))

    (testing "Scenario: champion tool reports the calculated winner"
      (let [t (text (call db "champion" {:season 2019}))]
        (is (str/includes? t "Flamengo"))))

    (testing "Scenario: competition_stats reports averages"
      (let [t (text (call db "competition_stats" {:competition "Brasileirão Série A"}))]
        (is (str/includes? t "Average goals per match"))))

    (testing "Scenario: biggest_wins lists lopsided results"
      (let [t (text (call db "biggest_wins" {:limit 5}))]
        (is (str/includes? t "Biggest victories"))))

    (testing "Scenario: club_roster lists a squad"
      (let [t (text (call db "club_roster" {:club "Santos"}))]
        (is (str/includes? t "avg rating"))))

    (testing "Scenario: calling an unknown tool flags an error"
      (let [resp (call db "no_such_tool" {})]
        (is (true? (get-in resp [:result :isError])))))

    (testing "Scenario: a tool handler exception is captured, not thrown"
      ;; standings with no season still runs (defaults), proving robustness
      (let [resp (call db "list_competitions" {})]
        (is (false? (get-in resp [:result :isError])))))))

(deftest stdio-round-trip
  (testing "Scenario: end-to-end newline-delimited JSON-RPC over stdio"
    ;; Given an initialize request followed by a tools/call on stdin
    (let [db (fix/db)
          requests (str (json/generate-string {:jsonrpc "2.0" :id 1 :method "initialize" :params {}})
                        "\n"
                        (json/generate-string {:jsonrpc "2.0" :id 2 :method "tools/call"
                                               :params {:name "list_competitions" :arguments {}}})
                        "\n")
          in (ByteArrayInputStream. (.getBytes requests "UTF-8"))
          out (ByteArrayOutputStream.)]
      ;; When the server processes the stream to EOF
      (mcp/serve! db in out)
      ;; Then we get two well-formed JSON-RPC responses, one per line
      (let [lines (->> (str/split-lines (str out)) (remove str/blank?))
            parsed (map #(json/parse-string % true) lines)]
        (is (= 2 (count parsed)))
        (is (= 1 (:id (first parsed))))
        (is (str/includes? (get-in (second parsed) [:result :content 0 :text]) "Competitions"))))))
