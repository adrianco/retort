(ns brazilian-soccer-mcp.server
  "MCP server that exposes Brazilian soccer tools via JSON-RPC over stdio."
  (:require [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.tools :as tools]
            [cheshire.core :as json]
            [clojure.string :as str])
  (:gen-class))

;; ---------------------------------------------------------------------------
;; Tool registry
;; ---------------------------------------------------------------------------

(def tool-definitions
  [{:name "find_matches_by_teams"
    :description "Find all matches between two specific teams, with head-to-head record."
    :inputSchema {:type "object"
                  :properties {:team-a {:type "string" :description "First team name"}
                               :team-b {:type "string" :description "Second team name"}
                               :limit  {:type "integer" :description "Max results (default 50)"}}
                  :required ["team-a" "team-b"]}}

   {:name "find_matches_by_team"
    :description "Find all matches for a single team, optionally filtered by competition or season."
    :inputSchema {:type "object"
                  :properties {:team        {:type "string"  :description "Team name"}
                               :competition {:type "string"  :description "Competition name filter"}
                               :season      {:type "integer" :description "Season year"}
                               :limit       {:type "integer" :description "Max results (default 50)"}}
                  :required ["team"]}}

   {:name "find_matches_by_date_range"
    :description "Find matches in a date range (ISO date format YYYY-MM-DD)."
    :inputSchema {:type "object"
                  :properties {:from-date   {:type "string" :description "Start date YYYY-MM-DD"}
                               :to-date     {:type "string" :description "End date YYYY-MM-DD"}
                               :competition {:type "string" :description "Competition filter"}
                               :limit       {:type "integer"}}
                  :required []}}

   {:name "find_matches_by_season"
    :description "Find all matches in a given season year."
    :inputSchema {:type "object"
                  :properties {:season      {:type "integer" :description "Season year e.g. 2023"}
                               :competition {:type "string"  :description "Competition filter"}
                               :limit       {:type "integer"}}
                  :required ["season"]}}

   {:name "get_team_stats"
    :description "Return win/draw/loss/goals stats for a team."
    :inputSchema {:type "object"
                  :properties {:team        {:type "string"  :description "Team name"}
                               :season      {:type "integer" :description "Season year"}
                               :competition {:type "string"  :description "Competition name"}}
                  :required ["team"]}}

   {:name "compare_teams_head_to_head"
    :description "Detailed head-to-head comparison between two teams."
    :inputSchema {:type "object"
                  :properties {:team-a {:type "string" :description "First team"}
                               :team-b {:type "string" :description "Second team"}
                               :season {:type "integer"}}
                  :required ["team-a" "team-b"]}}

   {:name "find_players"
    :description "Search FIFA player database by name, nationality, or club."
    :inputSchema {:type "object"
                  :properties {:name        {:type "string"  :description "Player name search"}
                               :nationality {:type "string"  :description "Nationality filter e.g. Brazil"}
                               :club        {:type "string"  :description "Club name filter"}
                               :limit       {:type "integer"}}
                  :required []}}

   {:name "find_brazilian_players"
    :description "Find Brazilian players, optionally filtered by club."
    :inputSchema {:type "object"
                  :properties {:club  {:type "string"  :description "Club name filter"}
                               :limit {:type "integer"}}
                  :required []}}

   {:name "top_players_at_club"
    :description "Return top-rated FIFA players at a specific club."
    :inputSchema {:type "object"
                  :properties {:club  {:type "string"  :description "Club name"}
                               :limit {:type "integer"}}
                  :required ["club"]}}

   {:name "calculate_standings"
    :description "Calculate league standings for a season/competition from match results."
    :inputSchema {:type "object"
                  :properties {:season      {:type "integer" :description "Season year"}
                               :competition {:type "string"  :description "Competition name (default: Brasileirao Serie A)"}}
                  :required []}}

   {:name "get_season_winner"
    :description "Return the champion team for a given season and competition."
    :inputSchema {:type "object"
                  :properties {:season      {:type "integer"}
                               :competition {:type "string"}}
                  :required ["season"]}}

   {:name "goals_per_match_avg"
    :description "Calculate average goals per match, optionally filtered."
    :inputSchema {:type "object"
                  :properties {:competition {:type "string"}
                               :season      {:type "integer"}}
                  :required []}}

   {:name "biggest_wins"
    :description "Return matches with the largest goal differences (biggest wins)."
    :inputSchema {:type "object"
                  :properties {:competition {:type "string"}
                               :season      {:type "integer"}
                               :limit       {:type "integer"}}
                  :required []}}

   {:name "home_vs_away_stats"
    :description "Overall home win/draw/away win percentages."
    :inputSchema {:type "object"
                  :properties {:competition {:type "string"}
                               :season      {:type "integer"}}
                  :required []}}

   {:name "best_home_records"
    :description "Teams with the best home win percentages."
    :inputSchema {:type "object"
                  :properties {:competition {:type "string"}
                               :season      {:type "integer"}
                               :limit       {:type "integer"}}
                  :required []}}

   {:name "top_scoring_teams"
    :description "Teams ranked by total goals scored."
    :inputSchema {:type "object"
                  :properties {:competition {:type "string"}
                               :season      {:type "integer"}
                               :limit       {:type "integer"}}
                  :required []}}])

;; ---------------------------------------------------------------------------
;; Tool dispatch
;; ---------------------------------------------------------------------------

(defn call-tool [name args]
  (case name
    "find_matches_by_teams"      (tools/find-matches-by-teams args)
    "find_matches_by_team"       (tools/find-matches-by-team args)
    "find_matches_by_date_range" (tools/find-matches-by-date-range args)
    "find_matches_by_season"     (tools/find-matches-by-season args)
    "get_team_stats"             (tools/get-team-stats args)
    "compare_teams_head_to_head" (tools/compare-teams-head-to-head args)
    "find_players"               (tools/find-players args)
    "find_brazilian_players"     (tools/find-brazilian-players args)
    "top_players_at_club"        (tools/top-players-at-club args)
    "calculate_standings"        (tools/calculate-standings args)
    "get_season_winner"          (tools/get-season-winner args)
    "goals_per_match_avg"        (tools/goals-per-match-avg args)
    "biggest_wins"               (tools/biggest-wins args)
    "home_vs_away_stats"         (tools/home-vs-away-stats args)
    "best_home_records"          (tools/best-home-records args)
    "top_scoring_teams"          (tools/top-scoring-teams args)
    (throw (ex-info (str "Unknown tool: " name) {:tool name}))))

;; ---------------------------------------------------------------------------
;; JSON-RPC helpers
;; ---------------------------------------------------------------------------

(defn success-response [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn error-response [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn write-response! [resp]
  (println (json/generate-string resp))
  (flush))

;; ---------------------------------------------------------------------------
;; MCP request handlers
;; ---------------------------------------------------------------------------

(defn handle-initialize [id _params]
  (success-response id
    {:protocolVersion "2024-11-05"
     :capabilities    {:tools {}}
     :serverInfo      {:name    "brazilian-soccer-mcp"
                       :version "1.0.0"}}))

(defn handle-tools-list [id _params]
  (success-response id {:tools tool-definitions}))

(defn handle-tools-call [id params]
  (let [tool-name (get params "name")
        raw-args  (get params "arguments" {})
        ;; Convert string keys to keywords
        args      (into {} (map (fn [[k v]] [(keyword k) v]) raw-args))]
    (try
      (let [result (call-tool tool-name args)
            text   (json/generate-string result {:pretty true})]
        (success-response id
          {:content [{:type "text" :text text}]}))
      (catch Exception e
        (error-response id -32603 (.getMessage e))))))

(defn handle-request [req]
  (let [id     (get req "id")
        method (get req "method")
        params (get req "params" {})]
    (case method
      "initialize"        (handle-initialize id params)
      "tools/list"        (handle-tools-list id params)
      "tools/call"        (handle-tools-call id params)
      "notifications/initialized" nil  ;; notification, no response
      (when id
        (error-response id -32601 (str "Method not found: " method))))))

;; ---------------------------------------------------------------------------
;; Main loop
;; ---------------------------------------------------------------------------

(defn -main [& _args]
  (binding [*out* *out*]
    (data/load-all!)
    (loop []
      (when-let [line (try (read-line) (catch Exception _ nil))]
        (when (not= "" (str/trim line))
          (try
            (let [req  (json/parse-string line)
                  resp (handle-request req)]
              (when resp (write-response! resp)))
            (catch Exception e
              (write-response! (error-response nil -32700
                                               (str "Parse error: " (.getMessage e)))))))
        (recur)))))
