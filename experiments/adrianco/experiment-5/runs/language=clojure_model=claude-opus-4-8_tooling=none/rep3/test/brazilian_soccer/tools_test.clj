;; =============================================================================
;; brazilian-soccer.tools-test
;; -----------------------------------------------------------------------------
;; BDD scenarios for the MCP tool dispatch layer. Fixtures are injected via the
;; *matches* / *players* dynamic bindings so no disk access is required. Asserts
;; both the content shape and the rendered text.
;; =============================================================================
(ns brazilian-soccer.tools-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [clojure.string :as str]
            [clojure.set :as set]
            [brazilian-soccer.tools :as tools]
            [brazilian-soccer.fixtures :as fx]))

(use-fixtures :each
  (fn [t]
    (binding [tools/*matches* fx/matches
              tools/*players* fx/players*]
      (t))))

(defn text [resp] (-> resp :content first :text))

(deftest tools-list-scenario
  (testing "Scenario: tools/list exposes every capability and hides handlers"
    (let [ts (tools/list-tools)
          names (set (map :name ts))]
      (is (= 10 (count ts)))
      (is (every? #(contains? % :inputSchema) ts))
      (is (not-any? #(contains? % :handler) ts))
      (is (set/subset?
           #{"find_matches" "matches_between" "head_to_head" "team_record"
             "find_players" "top_players" "standings" "champion"
             "statistics" "list_teams"}
           names)))))

(deftest call-find-matches-scenario
  (testing "Scenario: find_matches returns formatted match lines"
    (let [resp (tools/call-tool "find_matches" {"team" "Flamengo" "season" 2019})]
      (is (false? (boolean (:isError resp))))
      (is (str/includes? (text resp) "Matches (5 found)"))
      (is (str/includes? (text resp) "Flamengo")))))

(deftest call-matches-between-scenario
  (testing "Scenario: matches_between includes a head-to-head block"
    (let [resp (tools/call-tool "matches_between" {"team_a" "Flamengo" "team_b" "Fluminense"})]
      (is (str/includes? (text resp) "Flamengo vs Fluminense"))
      (is (str/includes? (text resp) "Head-to-head")))))

(deftest call-team-record-scenario
  (testing "Scenario: team_record with home venue filter"
    (let [resp (tools/call-tool "team_record"
                                {"team" "Flamengo" "season" 2019 "venue" "home"})]
      (is (str/includes? (text resp) "Flamengo home record"))
      (is (str/includes? (text resp) "Matches: 2")))))

(deftest call-find-players-scenario
  (testing "Scenario: find_players by nationality"
    (let [resp (tools/call-tool "find_players" {"nationality" "Brazil"})]
      (is (str/includes? (text resp) "Players (6 found)"))
      (is (str/includes? (text resp) "Neymar")))))

(deftest call-top-players-scenario
  (testing "Scenario: top_players limited and nationality-filtered"
    (let [resp (tools/call-tool "top_players" {"nationality" "Brazil" "limit" 3})]
      (is (str/includes? (text resp) "Top 3 players"))
      (is (str/includes? (text resp) "Neymar Jr")))))

(deftest call-standings-scenario
  (testing "Scenario: standings ranks Flamengo first"
    (let [resp (tools/call-tool "standings" {"season" 2019 "competition" "Brasileirão"})]
      (is (str/includes? (text resp) "standings"))
      (is (str/includes? (text resp) " 1. Flamengo")))))

(deftest call-champion-scenario
  (testing "Scenario: champion identifies Flamengo for 2019"
    (let [resp (tools/call-tool "champion" {"season" 2019})]
      (is (str/includes? (text resp) "Flamengo")))))

(deftest call-statistics-scenario
  (testing "Scenario: statistics reports averages and biggest wins"
    (let [resp (tools/call-tool "statistics" {})]
      (is (str/includes? (text resp) "Average goals per match"))
      (is (str/includes? (text resp) "Biggest victories")))))

(deftest call-missing-required-arg
  (testing "Scenario: missing required arg yields an error result, not a crash"
    (let [resp (tools/call-tool "head_to_head" {"team_a" "Flamengo"})]
      (is (true? (:isError resp))))))

(deftest call-unknown-tool
  (testing "Scenario: unknown tool name yields an error result"
    (is (true? (:isError (tools/call-tool "does_not_exist" {}))))))
