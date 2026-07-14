(ns brazilian-soccer.mcp
  "Context
  =======
  Model Context Protocol server logic. Speaks JSON-RPC 2.0 (the transport loop
  itself lives in `brazilian-soccer.main`). This namespace defines:

    * the tool catalogue (`tools`) with JSON Schemas,
    * the per-tool handlers that bridge to `brazilian-soccer.queries` and
      render text via `brazilian-soccer.format`,
    * a pure `handle-request` function that maps a decoded JSON-RPC request map
      to a response map (or nil for notifications), which is exercised directly
      by the test suite.

  Implements MCP methods: initialize, notifications/initialized,
  tools/list, tools/call, ping."
  (:require [clojure.string :as str]
            [brazilian-soccer.queries :as q]
            [brazilian-soccer.format :as fmt]))

(def protocol-version "2024-11-05")

(def server-info
  {:name "brazilian-soccer-mcp" :version "1.0.0"})

;; ---------------------------------------------------------------------------
;; Tool catalogue
;; ---------------------------------------------------------------------------

(defn- str-prop [desc] {:type "string" :description desc})
(defn- int-prop [desc] {:type "integer" :description desc})

(def tools
  [{:name "find_matches"
    :description "Find soccer matches by team, opponent, competition, season or date range. Returns a formatted list of matches (most recent first)."
    :inputSchema
    {:type "object"
     :properties {:team (str-prop "Team name (matches home or away). Accepts variants like 'Flamengo' or 'Flamengo-RJ'.")
                  :opponent (str-prop "Second team; when given, only matches between team and opponent are returned.")
                  :competition (str-prop "Competition name substring, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'.")
                  :season (int-prop "Season year, e.g. 2019.")
                  :date_from (str-prop "Inclusive lower bound, ISO yyyy-MM-dd.")
                  :date_to (str-prop "Inclusive upper bound, ISO yyyy-MM-dd.")
                  :limit (int-prop "Max matches to return (default 50).")}}}

   {:name "team_record"
    :description "Win/draw/loss and goals record for a team, optionally scoped by season, competition and venue (home/away/all)."
    :inputSchema
    {:type "object"
     :required ["team"]
     :properties {:team (str-prop "Team name.")
                  :season (int-prop "Season year.")
                  :competition (str-prop "Competition substring.")
                  :venue (merge (str-prop "home, away or all (default all).")
                                {:enum ["home" "away" "all"]})}}}

   {:name "head_to_head"
    :description "Head-to-head record and match list between two teams."
    :inputSchema
    {:type "object"
     :required ["team1" "team2"]
     :properties {:team1 (str-prop "First team.")
                  :team2 (str-prop "Second team.")
                  :competition (str-prop "Optional competition substring.")
                  :season (int-prop "Optional season year.")}}}

   {:name "standings"
    :description "League table computed from match results (3 pts per win, 1 per draw) for a competition and season."
    :inputSchema
    {:type "object"
     :required ["competition" "season"]
     :properties {:competition (str-prop "Competition substring, e.g. 'Brasileirão'.")
                  :season (int-prop "Season year, e.g. 2019.")}}}

   {:name "league_stats"
    :description "Aggregate statistics (avg goals per match, home/away win rate, draws) for a competition and/or season."
    :inputSchema
    {:type "object"
     :properties {:competition (str-prop "Competition substring.")
                  :season (int-prop "Season year.")}}}

   {:name "biggest_wins"
    :description "Matches with the largest goal margins, optionally scoped by competition and season."
    :inputSchema
    {:type "object"
     :properties {:competition (str-prop "Competition substring.")
                  :season (int-prop "Season year.")
                  :limit (int-prop "Max matches (default 10).")}}}

   {:name "search_players"
    :description "Search FIFA player database by name, nationality, club, position or minimum overall rating. Sorted by overall rating."
    :inputSchema
    {:type "object"
     :properties {:name (str-prop "Player name substring.")
                  :nationality (str-prop "Nationality substring, e.g. 'Brazil'.")
                  :club (str-prop "Club name.")
                  :position (str-prop "Exact position code, e.g. 'GK', 'ST', 'CB'.")
                  :min_overall (int-prop "Minimum FIFA overall rating.")
                  :limit (int-prop "Max players (default 25).")}}}

   {:name "club_nationality_breakdown"
    :description "Group players of a nationality (default Brazil) by club, with player counts and average overall rating."
    :inputSchema
    {:type "object"
     :properties {:nationality (str-prop "Nationality (default 'Brazil').")
                  :limit (int-prop "Max clubs (default 20).")}}}

   {:name "list_competitions"
    :description "List all competitions present in the match data."
    :inputSchema {:type "object" :properties {}}}

   {:name "list_seasons"
    :description "List all seasons present in the match data, optionally filtered by competition."
    :inputSchema
    {:type "object"
     :properties {:competition (str-prop "Optional competition substring.")}}}])

;; ---------------------------------------------------------------------------
;; Tool handlers -> text
;; ---------------------------------------------------------------------------

(defn- kebab-args
  "Convert JSON arg keys (string or keyword, snake_case) to kebab keywords:
  \"date_from\" -> :date-from."
  [args]
  (reduce-kv (fn [m k v]
               (assoc m (keyword (str/replace (name k) "_" "-")) v))
             {} (or args {})))

(defmulti call-tool
  "Dispatch a tool call to its handler. Returns a text string."
  (fn [name _args] name))

(defmethod call-tool "find_matches" [_ args]
  (let [a (kebab-args args)
        ms (q/find-matches a)]
    (str (if (and (:team a) (:opponent a))
           (format "Matches between %s and %s:\n" (:team a) (:opponent a))
           (format "Matches found: %d\n" (count ms)))
         (fmt/matches-block ms))))

(defmethod call-tool "team_record" [_ args]
  (fmt/team-record-block (q/team-record (kebab-args args))))

(defmethod call-tool "head_to_head" [_ args]
  (fmt/head-to-head-block (q/head-to-head (kebab-args args))))

(defmethod call-tool "standings" [_ args]
  (let [a (kebab-args args)]
    (fmt/standings-block (q/standings a) a)))

(defmethod call-tool "league_stats" [_ args]
  (fmt/league-stats-block (q/league-stats (kebab-args args))))

(defmethod call-tool "biggest_wins" [_ args]
  (let [ms (q/biggest-wins (kebab-args args))]
    (str "Biggest victories (by goal margin):\n" (fmt/matches-block ms (count ms)))))

(defmethod call-tool "search_players" [_ args]
  (fmt/players-block (q/search-players (kebab-args args))))

(defmethod call-tool "club_nationality_breakdown" [_ args]
  (let [a (kebab-args args)]
    (fmt/club-breakdown-block (q/club-nationality-breakdown a) a)))

(defmethod call-tool "list_competitions" [_ _]
  (str "Competitions in dataset:\n"
       (str/join "\n" (map #(str "- " %) (q/list-competitions)))))

(defmethod call-tool "list_seasons" [_ args]
  (let [a (kebab-args args)]
    (str "Seasons in dataset:\n"
         (str/join ", " (q/list-seasons (:competition a))))))

(defmethod call-tool :default [name _]
  (throw (ex-info (str "Unknown tool: " name) {:code -32602})))

;; ---------------------------------------------------------------------------
;; JSON-RPC handling
;; ---------------------------------------------------------------------------

(defn- result [id body] {:jsonrpc "2.0" :id id :result body})
(defn- error  [id code msg] {:jsonrpc "2.0" :id id :error {:code code :message msg}})

(defn handle-request
  "Pure handler: takes a decoded JSON-RPC request map (keyword keys) and returns
  a response map, or nil for notifications (no id / notification methods)."
  [{:keys [id method params]}]
  (case method
    "initialize"
    (result id {:protocolVersion protocol-version
                :capabilities {:tools {}}
                :serverInfo server-info})

    "notifications/initialized" nil
    "initialized" nil

    "ping" (result id {})

    "tools/list"
    (result id {:tools tools})

    "tools/call"
    (let [tool-name (:name params)
          args (:arguments params)]
      (try
        (let [text (call-tool tool-name args)]
          (result id {:content [{:type "text" :text text}]
                      :isError false}))
        (catch Exception e
          ;; Surface tool errors as an MCP tool result with isError, per spec.
          (result id {:content [{:type "text"
                                 :text (str "Error: " (.getMessage e))}]
                      :isError true}))))

    ;; unknown method
    (if (nil? id)
      nil
      (error id -32601 (str "Method not found: " method)))))
