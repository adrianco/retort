;; =============================================================================
;; brazilian-soccer.mcp-test
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   BDD (Given/When/Then) tests for the MCP/JSON-RPC layer of the Brazilian
;;   Soccer MCP server: the initialize handshake, tools/list advertisement, and
;;   tools/call dispatch for representative tools, plus an end-to-end round-trip
;;   through the newline-delimited stdio serve! loop.
;; =============================================================================
(ns brazilian-soccer.mcp-test
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.data.json :as json]
            [clojure.string :as str]
            [brazilian-soccer.mcp :as mcp]))

(defn- tool-text
  "Run tools/call for `name`/`args` through dispatch and return the first
   (prose) text content block."
  [name args]
  (let [r (mcp/handle-request {:method "tools/call" :id 1
                               :params {:name name :arguments args}})]
    (-> r :content first :text)))

(deftest initialize-handshake
  (testing "Given an initialize request, When handled, Then protocol/server info return"
    (let [r (mcp/handle-request {:method "initialize" :id 1 :params {}})]
      (is (= mcp/protocol-version (:protocolVersion r)))
      (is (contains? (:capabilities r) :tools))
      (is (= "brazilian-soccer-mcp" (get-in r [:serverInfo :name]))))))

(deftest notifications-have-no-response
  (testing "Given an initialized notification, When handled, Then nil (no reply)"
    (is (nil? (mcp/handle-request {:method "notifications/initialized"})))))

(deftest tools-are-listed
  (testing "Given tools/list, When handled, Then all tools advertise name+schema"
    (let [tools (:tools (mcp/handle-request {:method "tools/list" :id 1}))
          names (set (map :name tools))]
      (is (>= (count tools) 9))
      (is (every? #(and (:name %) (:description %) (:inputSchema %)) tools))
      (is (every? names ["search_matches" "head_to_head" "team_stats"
                         "standings" "competition_stats" "biggest_wins"
                         "search_players" "top_players" "list_competitions"]))
      ;; handlers must not leak into the advertised schema
      (is (not-any? :handler tools)))))

(deftest tools-call-dispatch
  (testing "Given search_matches, When called, Then prose mentions matches"
    (is (str/includes? (tool-text "search_matches" {:team "Flamengo" :opponent "Fluminense"})
                        "match(es) found")))

  (testing "Given head_to_head, When called, Then prose shows a H2H summary"
    (is (str/includes? (tool-text "head_to_head" {:team_a "Flamengo" :team_b "Fluminense"})
                        "Head-to-head")))

  (testing "Given search_players for Brazilians, When called, Then players return"
    (is (str/includes? (tool-text "search_players" {:nationality "Brazil" :limit 3})
                        "player(s) found")))

  (testing "Given standings, When called, Then a table is rendered"
    (is (str/includes? (tool-text "standings" {:competition "Brasileirão Série A" :season 2019})
                        "standings")))

  (testing "Given list_competitions, When called, Then competitions are listed"
    (is (str/includes? (tool-text "list_competitions" {}) "Competitions")))

  (testing "Given an unknown tool, When called, Then an error result returns"
    (let [r (mcp/handle-request {:method "tools/call" :id 1
                                 :params {:name "nope" :arguments {}}})]
      (is (:isError r)))))

(deftest tools-call-returns-structured-json
  (testing "Given any tool call, When handled, Then a JSON data block accompanies prose"
    (let [r (mcp/handle-request {:method "tools/call" :id 1
                                 :params {:name "list_competitions" :arguments {}}})
          json-block (-> r :content second :text)]
      (is (str/includes? json-block "```json"))
      (is (str/includes? json-block "total-matches")))))

(deftest stdio-round-trip
  (testing "Given JSON-RPC lines on a reader, When served, Then valid replies stream out"
    (let [input (str (json/write-str {:jsonrpc "2.0" :id 1 :method "initialize" :params {}}) "\n"
                     (json/write-str {:jsonrpc "2.0" :method "notifications/initialized"}) "\n"
                     (json/write-str {:jsonrpc "2.0" :id 2 :method "tools/list"}) "\n")
          reader (java.io.BufferedReader. (java.io.StringReader. input))
          sw (java.io.StringWriter.)]
      (mcp/serve! reader sw)
      (let [lines (->> (str/split-lines (str sw)) (remove str/blank?))
            replies (map #(json/read-str % :key-fn keyword) lines)]
        ;; initialize (id 1) + tools/list (id 2) reply; notification gets none.
        (is (= 2 (count replies)))
        (is (= [1 2] (map :id replies)))
        (is (= mcp/protocol-version (get-in (first replies) [:result :protocolVersion])))
        (is (seq (get-in (second replies) [:result :tools])))))))
