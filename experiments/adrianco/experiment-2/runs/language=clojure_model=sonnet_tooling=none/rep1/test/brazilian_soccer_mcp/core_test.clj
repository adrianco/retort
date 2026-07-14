(ns brazilian-soccer-mcp.core-test
  (:require [clojure.test :refer [deftest is testing use-fixtures]]
            [cheshire.core :as json]
            [brazilian-soccer-mcp.core :as core]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.tools :as tools]))

;;; ─── Fixtures ────────────────────────────────────────────────────────────────

(defn load-data-fixture [f]
  (data/load-all-data!)
  (f))

(use-fixtures :once load-data-fixture)

;;; ─── MCP protocol tests ──────────────────────────────────────────────────────

(deftest test-initialize
  (testing "initialize returns protocol version and server info"
    (let [req  {"jsonrpc" "2.0" "id" 1 "method" "initialize"
                "params"  {"protocolVersion" "2024-11-05"
                           "clientInfo"      {"name" "test" "version" "1.0"}}}
          resp (core/handle-request req)]
      (is (= "2.0" (get resp :jsonrpc)))
      (is (= 1 (get resp :id)))
      (is (some? (get-in resp [:result :serverInfo])))
      (is (some? (get-in resp [:result :protocolVersion]))))))

(deftest test-tools-list
  (testing "tools/list returns expected tools"
    (let [req  {"jsonrpc" "2.0" "id" 2 "method" "tools/list" "params" {}}
          resp (core/handle-request req)]
      (is (= 2 (get resp :id)))
      (let [tool-names (map :name (get-in resp [:result :tools]))]
        (is (some #{"search_matches"} tool-names))
        (is (some #{"get_head_to_head"} tool-names))
        (is (some #{"get_team_stats"} tool-names))
        (is (some #{"get_standings"} tool-names))
        (is (some #{"search_players"} tool-names))
        (is (some #{"get_biggest_wins"} tool-names))
        (is (some #{"get_global_stats"} tool-names))))))

(deftest test-unknown-method
  (testing "unknown method returns error"
    (let [req  {"jsonrpc" "2.0" "id" 3 "method" "nonexistent/method" "params" {}}
          resp (core/handle-request req)]
      (is (some? (get resp :error)))
      (is (= -32601 (get-in resp [:error :code]))))))

(deftest test-notification-no-response
  (testing "notifications/initialized returns nil"
    (let [req  {"jsonrpc" "2.0" "method" "notifications/initialized" "params" {}}
          resp (core/handle-request req)]
      (is (nil? resp)))))

;;; ─── Data loading tests ──────────────────────────────────────────────────────

(deftest test-data-loaded
  (testing "all CSV files are loaded"
    (let [d (data/get-data)]
      (is (seq (:brasileirao d)) "Brasileirao data should be non-empty")
      (is (seq (:copa-brasil d)) "Copa Brasil data should be non-empty")
      (is (seq (:libertadores d)) "Libertadores data should be non-empty")
      (is (seq (:br-football d)) "BR-Football data should be non-empty")
      (is (seq (:historico d)) "Historico data should be non-empty")
      (is (seq (:fifa d)) "FIFA data should be non-empty"))))

(deftest test-data-counts
  (testing "data files have reasonable record counts"
    (let [d (data/get-data)]
      (is (> (count (:brasileirao d)) 1000))
      (is (> (count (:copa-brasil d)) 100))
      (is (> (count (:libertadores d)) 100))
      (is (> (count (:br-football d)) 1000))
      (is (> (count (:historico d)) 1000))
      (is (> (count (:fifa d)) 1000)))))

;;; ─── Match query tests ───────────────────────────────────────────────────────

(deftest test-search-matches-by-team
  (testing "search matches by team name"
    (let [matches (data/search-matches {:team "Flamengo" :limit 100})]
      (is (seq matches) "Should find Flamengo matches")
      (is (every? (fn [m]
                    (or (clojure.string/includes?
                         (clojure.string/lower-case (str (:home-team m))) "flamengo")
                        (clojure.string/includes?
                         (clojure.string/lower-case (str (:away-team m))) "flamengo")))
                  matches)
          "All matches should involve Flamengo"))))

(deftest test-search-matches-by-season
  (testing "search matches by season"
    (let [matches (data/search-matches {:season 2019 :limit 100})]
      (is (seq matches) "Should find 2019 matches")
      (is (every? #(= 2019 (:season %)) matches)
          "All matches should be in 2019 season"))))

(deftest test-search-matches-by-competition
  (testing "search matches by competition using accent-insensitive search"
    (let [matches (data/search-matches {:competition "Brasileirao" :limit 100})]
      (is (seq matches) "Should find Brasileirao matches (accent-insensitive)"))))

(deftest test-head-to-head
  (testing "head-to-head between Flamengo and Fluminense"
    (let [matches (data/head-to-head "Flamengo" "Fluminense")]
      (is (seq matches) "Should find derby matches")
      (is (every? (fn [m]
                    (let [ht (clojure.string/lower-case (str (:home-team m)))
                          at (clojure.string/lower-case (str (:away-team m)))]
                      (or (and (clojure.string/includes? ht "flamengo")
                               (clojure.string/includes? at "fluminense"))
                          (and (clojure.string/includes? ht "fluminense")
                               (clojure.string/includes? at "flamengo")))))
                  matches)
          "All matches should be between Flamengo and Fluminense"))))

(deftest test-head-to-head-stats
  (testing "head-to-head stats sum correctly"
    (let [stats (data/head-to-head-stats "Palmeiras" "Corinthians")]
      (is (= (:total-matches stats)
             (+ (:team-a-wins stats) (:team-b-wins stats) (:draws stats)))
          "Wins + draws should equal total matches"))))

(deftest test-team-stats
  (testing "team stats include required fields"
    (let [stats (data/team-stats {:team "Palmeiras" :season 2023})]
      (is (some? (:matches stats)))
      (is (some? (:win stats)))
      (is (some? (:draw stats)))
      (is (some? (:loss stats)))
      (is (some? (:goals-for stats)))
      (is (some? (:goals-against stats)))
      (is (= (:matches stats) (+ (:win stats) (:draw stats) (:loss stats)))
          "Matches should equal wins + draws + losses"))))

;;; ─── Player query tests ──────────────────────────────────────────────────────

(deftest test-search-players-by-nationality
  (testing "search Brazilian players"
    (let [players (data/search-players {:nationality "Brazil" :limit 20})]
      (is (seq players) "Should find Brazilian players")
      (is (every? #(clojure.string/includes?
                    (clojure.string/lower-case (str (:nationality %))) "brazil")
                  players)
          "All players should be Brazilian"))))

(deftest test-search-players-by-name
  (testing "search players by name substring"
    (let [players (data/search-players {:name "Neymar" :limit 10})]
      (is (seq players) "Should find Neymar"))))

(deftest test-search-players-by-min-overall
  (testing "filter players by minimum overall rating"
    (let [players (data/search-players {:min-overall 85 :limit 50})]
      (is (seq players) "Should find high-rated players")
      (is (every? #(>= (or (:overall %) 0) 85) players)
          "All players should have rating >= 85"))))

;;; ─── Tool call tests ─────────────────────────────────────────────────────────

(deftest test-tool-search-matches
  (testing "search_matches tool returns formatted text"
    (let [req  {"jsonrpc" "2.0" "id" 10 "method" "tools/call"
                "params"  {"name" "search_matches"
                           "arguments" {"team" "Flamengo" "limit" 5}}}
          resp (core/handle-request req)]
      (is (nil? (get resp :error)) "Should not return error")
      (let [text (get-in resp [:result :content 0 :text])]
        (is (string? text))
        (is (clojure.string/includes? (clojure.string/lower-case text) "match")
            "Response should mention matches")))))

(deftest test-tool-get-head-to-head
  (testing "get_head_to_head tool returns formatted text"
    (let [req  {"jsonrpc" "2.0" "id" 11 "method" "tools/call"
                "params"  {"name" "get_head_to_head"
                           "arguments" {"team_a" "Flamengo" "team_b" "Fluminense"}}}
          resp (core/handle-request req)]
      (is (nil? (get resp :error)))
      (let [text (get-in resp [:result :content 0 :text])]
        (is (string? text))))))

(deftest test-tool-get-team-stats
  (testing "get_team_stats tool returns stats"
    (let [req  {"jsonrpc" "2.0" "id" 12 "method" "tools/call"
                "params"  {"name" "get_team_stats"
                           "arguments" {"team" "Palmeiras" "season" 2023}}}
          resp (core/handle-request req)]
      (is (nil? (get resp :error)))
      (let [text (get-in resp [:result :content 0 :text])]
        (is (string? text))
        (is (clojure.string/includes? text "Wins") "Response should include win stats")))))

(deftest test-tool-search-players
  (testing "search_players tool returns player info"
    (let [req  {"jsonrpc" "2.0" "id" 13 "method" "tools/call"
                "params"  {"name" "search_players"
                           "arguments" {"nationality" "Brazil" "min_overall" 85 "limit" 5}}}
          resp (core/handle-request req)]
      (is (nil? (get resp :error)))
      (let [text (get-in resp [:result :content 0 :text])]
        (is (string? text))
        (is (clojure.string/includes? text "Overall"))))))

(deftest test-tool-get-standings
  (testing "get_standings tool computes standings"
    (let [req  {"jsonrpc" "2.0" "id" 14 "method" "tools/call"
                "params"  {"name" "get_standings"
                           "arguments" {"season" 2019 "competition" "Brasileirao"}}}
          resp (core/handle-request req)]
      (is (nil? (get resp :error)))
      (let [text (get-in resp [:result :content 0 :text])]
        (is (string? text))
        (is (or (clojure.string/includes? text "pts")
                (clojure.string/includes? text "No standings")))))))

(deftest test-tool-get-team-stats-palmeiras
  (testing "get_team_stats for Palmeiras 2019 Brasileirao season"
    (let [req  {"jsonrpc" "2.0" "id" 20 "method" "tools/call"
                "params"  {"name" "get_team_stats"
                           "arguments" {"team" "Palmeiras" "season" 2019
                                        "competition" "Brasileirao"}}}
          resp (core/handle-request req)]
      (is (nil? (get resp :error)))
      (let [text (get-in resp [:result :content 0 :text])]
        (is (string? text))))))

(deftest test-tool-get-biggest-wins
  (testing "get_biggest_wins returns top results"
    (let [req  {"jsonrpc" "2.0" "id" 15 "method" "tools/call"
                "params"  {"name" "get_biggest_wins"
                           "arguments" {"limit" 5}}}
          resp (core/handle-request req)]
      (is (nil? (get resp :error)))
      (let [text (get-in resp [:result :content 0 :text])]
        (is (string? text))))))

(deftest test-tool-get-global-stats
  (testing "get_global_stats returns aggregate info"
    (let [req  {"jsonrpc" "2.0" "id" 16 "method" "tools/call"
                "params"  {"name" "get_global_stats"
                           "arguments" {"season" 2019}}}
          resp (core/handle-request req)]
      (is (nil? (get resp :error)))
      (let [text (get-in resp [:result :content 0 :text])]
        (is (string? text))
        (is (clojure.string/includes? text "Goals"))))))

;;; ─── JSON round-trip test ────────────────────────────────────────────────────

(deftest test-json-round-trip
  (testing "responses can be serialised to JSON"
    (let [req  {"jsonrpc" "2.0" "id" 99 "method" "tools/list" "params" {}}
          resp (core/handle-request req)
          json (json/generate-string resp)]
      (is (string? json))
      (is (map? (json/parse-string json))))))
