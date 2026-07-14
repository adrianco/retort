(ns brazilian-soccer.mcp
  "=============================================================================
   mcp.clj — Model Context Protocol server (JSON-RPC 2.0 over stdio)
   -----------------------------------------------------------------------------
   Context:
     Implements the MCP stdio transport: newline-delimited JSON-RPC 2.0
     messages on stdin/stdout. Supports the handshake (`initialize`,
     `notifications/initialized`), tool discovery (`tools/list`) and tool
     invocation (`tools/call`). Each tool wraps a function from
     brazilian-soccer.queries and renders the result with
     brazilian-soccer.format.

     This namespace is transport + dispatch only; all soccer logic lives in
     the queries / format namespaces so it is independently testable. The
     handler `handle-request` is pure (request map -> response map) which the
     test suite exercises directly without spawning a process.
   ============================================================================="
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [brazilian-soccer.queries :as q]
            [brazilian-soccer.format :as fmt])
  (:import [java.io BufferedReader]))

(def server-info {:name "brazilian-soccer-mcp" :version "1.0.0"})
(def protocol-version "2024-11-05")

;; ---------------------------------------------------------------------------
;; Tool definitions (exposed via tools/list)
;; ---------------------------------------------------------------------------

(def tools
  [{:name "search_matches"
    :description "Find soccer matches by team, opponent, competition, season or date range. Returns a formatted list, most recent first."
    :inputSchema
    {:type "object"
     :properties {:team        {:type "string" :description "Team name (matched on either side, e.g. \"Flamengo\")"}
                  :opponent    {:type "string" :description "Second team, for head-to-head listings"}
                  :competition {:type "string" :description "Competition name, e.g. \"Brasileirão\", \"Copa do Brasil\", \"Libertadores\""}
                  :season      {:type "integer" :description "Season / year, e.g. 2019"}
                  :side        {:type "string" :enum ["home" "away" "either"] :description "Which side the team played on"}
                  :date_from   {:type "string" :description "ISO date inclusive lower bound (YYYY-MM-DD)"}
                  :date_to     {:type "string" :description "ISO date inclusive upper bound (YYYY-MM-DD)"}
                  :limit       {:type "integer" :description "Max matches to return (default 25)"}}}}

   {:name "team_stats"
    :description "Win/draw/loss record, goals for/against and win rate for a team, optionally scoped to a season, competition and home/away venue."
    :inputSchema
    {:type "object"
     :required ["team"]
     :properties {:team        {:type "string"}
                  :season      {:type "integer"}
                  :competition {:type "string"}
                  :venue       {:type "string" :enum ["home" "away" "all"]}}}}

   {:name "head_to_head"
    :description "Head-to-head record between two teams (wins/draws and recent meetings)."
    :inputSchema
    {:type "object"
     :required ["team1" "team2"]
     :properties {:team1       {:type "string"}
                  :team2       {:type "string"}
                  :competition {:type "string"}
                  :season      {:type "integer"}}}}

   {:name "standings"
    :description "League table for a competition+season, calculated from match results (points, W/D/L, goal difference)."
    :inputSchema
    {:type "object"
     :required ["season"]
     :properties {:competition {:type "string" :description "Default \"Brasileirão\""}
                  :season      {:type "integer"}
                  :limit       {:type "integer"}}}}

   {:name "competition_stats"
    :description "Aggregate stats for a competition/season: match count, total & average goals, home/away/draw split, home win rate."
    :inputSchema
    {:type "object"
     :properties {:competition {:type "string"}
                  :season      {:type "integer"}}}}

   {:name "biggest_wins"
    :description "Matches with the largest goal margin, optionally filtered by competition/season."
    :inputSchema
    {:type "object"
     :properties {:competition {:type "string"}
                  :season      {:type "integer"}
                  :limit       {:type "integer"}}}}

   {:name "search_players"
    :description "Search the FIFA player database by name, nationality, club, position or minimum overall rating. Sorted by overall rating."
    :inputSchema
    {:type "object"
     :properties {:name        {:type "string"}
                  :nationality {:type "string" :description "e.g. \"Brazil\""}
                  :club        {:type "string"}
                  :position    {:type "string" :description "e.g. \"GK\", \"ST\", \"CB\""}
                  :min_overall {:type "integer"}
                  :limit       {:type "integer"}}}}

   {:name "players_by_club"
    :description "Summarize players grouped by club (count and average rating), optionally filtered by nationality (e.g. Brazilian players at Brazilian clubs)."
    :inputSchema
    {:type "object"
     :properties {:nationality {:type "string"}
                  :limit       {:type "integer"}}}}])

;; ---------------------------------------------------------------------------
;; Tool dispatch — returns a plain text string
;; ---------------------------------------------------------------------------

(defn- kw-venue [v] (some-> v keyword))

(defmulti run-tool (fn [name _args] name))

(defmethod run-tool "search_matches" [_ {:keys [team opponent competition season
                                                side date_from date_to limit]}]
  (let [opts {:team team :opponent opponent :competition competition
              :season season :side (kw-venue side)
              :date-from date_from :date-to date_to :limit (or limit 25)}
        ms (q/search-matches (into {} (remove (comp nil? val) opts)))
        title (str "Matches"
                   (when team (str " for " team))
                   (when opponent (str " vs " opponent))
                   (when competition (str " — " competition))
                   (when season (str " (" season ")")))]
    (fmt/matches-report ms {:title title :shown (or limit 25)})))

(defmethod run-tool "team_stats" [_ {:keys [team season competition venue]}]
  (when (str/blank? team) (throw (ex-info "team is required" {})))
  (fmt/team-stats-report
   (q/team-stats {:team team :season season :competition competition
                  :venue (or (kw-venue venue) :all)})))

(defmethod run-tool "head_to_head" [_ {:keys [team1 team2 competition season]}]
  (when (or (str/blank? team1) (str/blank? team2))
    (throw (ex-info "team1 and team2 are required" {})))
  (fmt/head-to-head-report
   (q/head-to-head {:team1 team1 :team2 team2 :competition competition :season season})))

(defmethod run-tool "standings" [_ {:keys [competition season limit]}]
  (fmt/standings-report
   (q/standings {:competition (or competition "Brasileirão") :season season})
   {:title (str (or competition "Brasileirão") " " season " standings (calculated from matches)")
    :limit (or limit 20)}))

(defmethod run-tool "competition_stats" [_ {:keys [competition season]}]
  (fmt/competition-stats-report
   (q/competition-stats {:competition competition :season season})))

(defmethod run-tool "biggest_wins" [_ {:keys [competition season limit]}]
  (fmt/matches-report
   (q/biggest-wins {:competition competition :season season :limit (or limit 10)})
   {:title (str "Biggest wins"
                (when competition (str " — " competition))
                (when season (str " (" season ")")))
    :shown (or limit 10)}))

(defmethod run-tool "search_players" [_ {:keys [name nationality club position
                                                min_overall limit]}]
  (fmt/players-report
   (q/search-players {:name name :nationality nationality :club club
                      :position position :min-overall min_overall
                      :limit (or limit 25)})
   {:title (str/join " " (remove nil?
                                 ["Players"
                                  (when nationality (str "(" nationality ")"))
                                  (when club (str "at " club))]))
    :limit (or limit 25)}))

(defmethod run-tool "players_by_club" [_ {:keys [nationality limit]}]
  (fmt/club-summary-report
   (q/players-by-club-summary {:nationality nationality :limit (or limit 25)})
   {:title (str (or nationality "All") " players by club") :limit (or limit 25)}))

(defmethod run-tool :default [name _]
  (throw (ex-info (str "Unknown tool: " name) {:tool name})))

;; ---------------------------------------------------------------------------
;; JSON-RPC request handling (pure)
;; ---------------------------------------------------------------------------

(defn- result [id m] {:jsonrpc "2.0" :id id :result m})
(defn- error  [id code msg] {:jsonrpc "2.0" :id id :error {:code code :message msg}})

(defn handle-request
  "Handle a single decoded JSON-RPC request map. Returns a response map, or
   nil for notifications (no :id) which must not be answered."
  [{:keys [id method params]}]
  (case method
    "initialize"
    (result id {:protocolVersion protocol-version
                :capabilities {:tools {}}
                :serverInfo server-info})

    ("notifications/initialized" "notifications/cancelled")
    nil

    "ping"
    (result id {})

    "tools/list"
    (result id {:tools tools})

    "tools/call"
    (let [tool-name (:name params)
          args      (or (:arguments params) {})]
      (try
        (let [text (run-tool tool-name args)]
          (result id {:content [{:type "text" :text text}]
                      :isError false}))
        (catch Exception e
          (result id {:content [{:type "text"
                                 :text (str "Error: " (.getMessage e))}]
                      :isError true}))))

    ;; unknown method
    (when id (error id -32601 (str "Method not found: " method)))))

;; ---------------------------------------------------------------------------
;; stdio transport loop
;; ---------------------------------------------------------------------------

(defn- write-message! [^java.io.Writer out msg]
  (.write out (json/write-str msg))
  (.write out "\n")
  (.flush out))

(defn serve!
  "Run the MCP server reading newline-delimited JSON-RPC from `in` and writing
   responses to `out`. Blocks until EOF."
  [^BufferedReader in ^java.io.Writer out]
  (loop []
    (when-let [line (.readLine in)]
      (when-not (str/blank? line)
        (let [resp (try
                     (handle-request (json/read-str line :key-fn keyword))
                     (catch Exception e
                       (error nil -32700 (str "Parse error: " (.getMessage e)))))]
          (when resp (write-message! out resp))))
      (recur))))
