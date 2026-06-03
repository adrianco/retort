(ns soccer.mcp
  "=============================================================================
   soccer.mcp — Model Context Protocol server (JSON-RPC 2.0 over stdio)
   -----------------------------------------------------------------------------
   PURPOSE
     Exposes the Brazilian-soccer knowledge base as MCP tools so an LLM client
     can answer natural-language questions about players, teams, matches and
     competitions. Speaks newline-delimited JSON-RPC 2.0 on stdin/stdout, which
     is the transport used by MCP stdio servers.

   PROTOCOL SURFACE
     initialize                 -> server info + capabilities
     notifications/initialized  -> (no response)
     tools/list                 -> the catalogue of tools below
     tools/call                 -> dispatch to a handler, return text content

   TOOLS
     search_matches   find matches by team(s) / competition / season / dates
     head_to_head     head-to-head record between two teams
     team_stats       W/D/L, goals, points and win-rate for a team
     standings        league table for a competition+season
     league_stats     averages / win-rates for a competition (+season)
     biggest_wins     largest-margin victories
     search_players   FIFA player search by name / nationality / club / etc.
     season_summary   compare several seasons of a competition

   The handlers translate JSON argument maps into soccer.queries calls and use
   soccer.format to produce the textual answer, while also returning the raw
   structured data so programmatic clients can use it directly.
   ============================================================================="
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [soccer.data :as data]
            [soccer.queries :as q]
            [soccer.format :as fmt])
  (:import [java.io BufferedReader]))

;; ---------------------------------------------------------------------------
;; Tool catalogue (name -> JSON schema + handler)
;; ---------------------------------------------------------------------------

(defn- arg [args k] (get args (clojure.core/name k)))

(defn- int-arg [args k]
  (let [v (arg args k)]
    (cond (nil? v) nil
          (number? v) (long v)
          (string? v) (try (Long/parseLong (str/trim v)) (catch Exception _ nil))
          :else nil)))

(def tools
  [{:name "search_matches"
    :description "Find soccer matches by team (home/away/either), an optional second team for head-to-head, competition, season, and/or date range. Returns the matching matches most-recent first."
    :inputSchema {:type "object"
                  :properties {"team" {:type "string" :description "Team name, e.g. 'Flamengo' (state suffix optional)"}
                               "team2" {:type "string" :description "Second team to restrict to meetings between the two"}
                               "competition" {:type "string" :description "Brasileirão, Copa do Brasil, or Libertadores (substring)"}
                               "season" {:type "integer" :description "Season/year, e.g. 2019"}
                               "venue" {:type "string" :enum ["home" "away"] :description "Restrict 'team' to home or away"}
                               "date_from" {:type "string" :description "Inclusive start date (ISO or DD/MM/YYYY)"}
                               "date_to" {:type "string" :description "Inclusive end date"}
                               "limit" {:type "integer" :description "Max results (default 50)"}}}}
   {:name "head_to_head"
    :description "Head-to-head record between two teams across all competitions in the dataset: each side's wins, draws, and the list of meetings."
    :inputSchema {:type "object"
                  :required ["team1" "team2"]
                  :properties {"team1" {:type "string"}
                               "team2" {:type "string"}
                               "competition" {:type "string"}
                               "season" {:type "integer"}}}}
   {:name "team_stats"
    :description "Aggregate a team's wins/draws/losses, goals for/against, points and win-rate, optionally restricted by season, competition and venue (home/away)."
    :inputSchema {:type "object"
                  :required ["team"]
                  :properties {"team" {:type "string"}
                               "season" {:type "integer"}
                               "competition" {:type "string"}
                               "venue" {:type "string" :enum ["home" "away"]}}}}
   {:name "standings"
    :description "Compute the final league table (standings) for a competition and season from match results: position, points, W/D/L, goals, goal difference."
    :inputSchema {:type "object"
                  :required ["competition" "season"]
                  :properties {"competition" {:type "string"}
                               "season" {:type "integer"}}}}
   {:name "league_stats"
    :description "Aggregate statistics for a competition (optionally a season): match count, total/average goals per match, home/away win rate and draw rate."
    :inputSchema {:type "object"
                  :properties {"competition" {:type "string"}
                               "season" {:type "integer"}}}}
   {:name "biggest_wins"
    :description "List the matches with the largest goal margin, optionally filtered by competition and season."
    :inputSchema {:type "object"
                  :properties {"competition" {:type "string"}
                               "season" {:type "integer"}
                               "limit" {:type "integer" :description "Default 10"}}}}
   {:name "search_players"
    :description "Search the FIFA player database by name, nationality (e.g. 'Brazil'), club (e.g. 'Flamengo'), position (e.g. 'GK'), and/or minimum overall rating. Sorted by overall rating."
    :inputSchema {:type "object"
                  :properties {"name" {:type "string"}
                               "nationality" {:type "string"}
                               "club" {:type "string"}
                               "position" {:type "string"}
                               "min_overall" {:type "integer"}
                               "limit" {:type "integer" :description "Default 25"}}}}
   {:name "season_summary"
    :description "Compare multiple seasons of a competition: matches, goals and average goals per season."
    :inputSchema {:type "object"
                  :required ["competition" "seasons"]
                  :properties {"competition" {:type "string"}
                               "seasons" {:type "array" :items {:type "integer"}}}}}])

;; ---------------------------------------------------------------------------
;; Tool handlers — return {:text String :data <structured>}
;; ---------------------------------------------------------------------------

(defn- venue-kw [args]
  (when-let [v (arg args :venue)] (keyword v)))

(defn handle-call [db tool-name args]
  (case tool-name
    "search_matches"
    (let [opts {:team (arg args :team) :team2 (arg args :team2)
                :competition (arg args :competition) :season (int-arg args :season)
                :date-from (arg args :date_from) :date-to (arg args :date_to)
                :home (= :home (venue-kw args)) :away (= :away (venue-kw args))
                :limit (or (int-arg args :limit) 50)}
          ms (q/search-matches db opts)]
      {:text (str (count ms) " match(es) found:\n" (fmt/matches ms)) :data ms})

    "head_to_head"
    (let [h (q/head-to-head db {:team1 (arg args :team1) :team2 (arg args :team2)
                                :competition (arg args :competition)
                                :season (int-arg args :season)})]
      {:text (fmt/head-to-head h) :data (dissoc h :matches)})

    "team_stats"
    (let [t (q/team-stats db {:team (arg args :team) :season (int-arg args :season)
                              :competition (arg args :competition) :venue (venue-kw args)})]
      {:text (fmt/team-stats t) :data t})

    "standings"
    (let [opts {:competition (arg args :competition) :season (int-arg args :season)}
          rows (q/standings db opts)]
      {:text (fmt/standings rows opts) :data rows})

    "league_stats"
    (let [s (q/league-stats db {:competition (arg args :competition)
                                :season (int-arg args :season)})]
      {:text (fmt/league-stats s) :data s})

    "biggest_wins"
    (let [ms (q/biggest-wins db {:competition (arg args :competition)
                                 :season (int-arg args :season)
                                 :limit (or (int-arg args :limit) 10)})]
      {:text (fmt/biggest-wins ms) :data ms})

    "search_players"
    (let [ps (q/search-players db {:name (arg args :name)
                                   :nationality (arg args :nationality)
                                   :club (arg args :club)
                                   :position (arg args :position)
                                   :min-overall (int-arg args :min_overall)
                                   :limit (or (int-arg args :limit) 25)})]
      {:text (str (count ps) " player(s) found:\n" (fmt/players ps)) :data ps})

    "season_summary"
    (let [seasons (mapv long (arg args :seasons))
          rows (q/season-summary db {:competition (arg args :competition) :seasons seasons})]
      {:text (fmt/season-summary rows) :data (vec rows)})

    (throw (ex-info (str "Unknown tool: " tool-name) {:tool tool-name}))))

;; ---------------------------------------------------------------------------
;; JSON-RPC request handling
;; ---------------------------------------------------------------------------

(def ^:private server-info
  {:name "brazilian-soccer-mcp" :version "1.0.0"})

(defn handle-request
  "Handle a single decoded JSON-RPC request map. Returns a response map, or nil
   for notifications (which must not be answered)."
  [db {:keys [id method params]}]
  (try
    (case method
      "initialize"
      {:jsonrpc "2.0" :id id
       :result {:protocolVersion "2024-11-05"
                :capabilities {:tools {}}
                :serverInfo server-info}}

      "notifications/initialized" nil
      "notifications/cancelled" nil
      "ping" {:jsonrpc "2.0" :id id :result {}}

      "tools/list"
      {:jsonrpc "2.0" :id id :result {:tools tools}}

      "tools/call"
      (let [tool-name (get params "name")
            args (or (get params "arguments") {})
            {:keys [text]} (handle-call db tool-name args)]
        {:jsonrpc "2.0" :id id
         :result {:content [{:type "text" :text text}]}})

      ;; default: method not found
      {:jsonrpc "2.0" :id id
       :error {:code -32601 :message (str "Method not found: " method)}})
    (catch Exception e
      (when id
        {:jsonrpc "2.0" :id id
         :error {:code -32603 :message (.getMessage e)}}))))

(defn- write-line! [^java.io.Writer out obj]
  (locking out
    (.write out (json/write-str obj))
    (.write out "\n")
    (.flush out)))

(defn- io-reader [in]
  (if (instance? BufferedReader in)
    in
    (BufferedReader. (clojure.java.io/reader in))))

(defn serve!
  "Run the blocking stdio JSON-RPC loop until EOF. `db` is the loaded dataset."
  ([db] (serve! db *in* *out*))
  ([db in out]
   (binding [*out* (java.io.PrintWriter. System/err)] ; keep stdout clean for JSON
     (let [^BufferedReader r (io-reader in)]
       (loop []
         (when-let [line (.readLine r)]
           (when-not (str/blank? line)
             (let [req (try (json/read-str line) (catch Exception _ nil))
                   resp (when (map? req)
                          (handle-request db {:id (get req "id")
                                              :method (get req "method")
                                              :params (get req "params")}))]
               (when resp (write-line! out resp))))
           (recur)))))))
