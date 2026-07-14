(ns brazilian-soccer.mcp
  "=============================================================================
   Brazilian Soccer MCP Server - MCP / JSON-RPC Protocol Layer
   =============================================================================

   CONTEXT
     Implements the Model Context Protocol over the stdio transport using
     newline-delimited JSON-RPC 2.0 messages. This is the boundary an LLM host
     (Claude Desktop, etc.) talks to. It exposes the soccer knowledge graph as
     a set of callable MCP 'tools', each backed by a pure function in
     brazilian-soccer.query and rendered by brazilian-soccer.format.

     Supported JSON-RPC methods:
       initialize                 - capability handshake
       notifications/initialized  - client ready (no response)
       tools/list                 - advertise available tools + JSON schemas
       tools/call                 - invoke a tool by name with arguments
       ping                       - liveness check

   DESIGN
     `handle-request` is a pure function (db + request-map -> response-map|nil)
     so the entire protocol surface is unit-testable without any IO. `serve!`
     wires it to real stdin/stdout. Tool handlers receive (db args) and return
     a human-readable string; `tools/call` wraps that into MCP content.

   PUBLIC API
     tools           - vector of tool definitions
     handle-request  - pure JSON-RPC request dispatch
     serve!          - run the stdio read/dispatch/write loop
   ============================================================================="
  (:require [cheshire.core :as json]
            [clojure.string :as str]
            [brazilian-soccer.query :as q]
            [brazilian-soccer.format :as fmt]))

(def protocol-version "2024-11-05")

(def server-info
  {:name "brazilian-soccer-mcp" :version "1.0.0"})

;; ----------------------------------------------------------------------------
;; Argument coercion helpers (JSON args arrive as strings/numbers)
;; ----------------------------------------------------------------------------

(defn- ->int [v]
  (cond (number? v) (long v)
        (string? v) (try (Long/parseLong (str/trim v)) (catch Exception _ nil))
        :else nil))

(defn- ->kw-side [v]
  (case (some-> v str str/lower-case)
    "home" :home "away" :away :either))

(defn- non-blank [v] (when (and v (not (str/blank? (str v)))) (str v)))

;; ----------------------------------------------------------------------------
;; Tool definitions
;;   Each: {:name :description :inputSchema :handler}
;;   :handler is (fn [db args] -> string)
;; ----------------------------------------------------------------------------

(defn- prop [type desc & {:as extra}]
  (merge {:type type :description desc} extra))

(def tools
  [{:name "search_matches"
    :description "Find soccer matches by team, opponent, competition, season, or date range. Returns a readable list of matches with scores and competition context."
    :inputSchema {:type "object"
                  :properties {:team        (prop "string" "Team name (e.g. \"Flamengo\"). Matches home, away, or either side.")
                               :side        (prop "string" "Which side the team must be on: \"home\", \"away\", or \"either\" (default).")
                               :opponent    (prop "string" "Second team; both teams must appear in the match.")
                               :competition (prop "string" "Competition filter, e.g. \"Brasileirão\", \"Copa do Brasil\", \"Libertadores\".")
                               :season      (prop "integer" "Season year, e.g. 2019.")
                               :date_from   (prop "string" "Inclusive ISO start date YYYY-MM-DD.")
                               :date_to     (prop "string" "Inclusive ISO end date YYYY-MM-DD.")
                               :limit       (prop "integer" "Max matches to return (default 20).")}}
    :handler (fn [db a]
               (let [limit (or (->int (:limit a)) 20)
                     opts {:team (non-blank (:team a))
                           :side (->kw-side (:side a))
                           :opponent (non-blank (:opponent a))
                           :competition (non-blank (:competition a))
                           :season (->int (:season a))
                           :date-from (non-blank (:date_from a))
                           :date-to (non-blank (:date_to a))
                           :limit limit}
                     ;; Get the true total then the capped page for the "N more" note.
                     total (count (q/search-matches db (assoc opts :limit Long/MAX_VALUE)))
                     page (q/search-matches db opts)]
                 (str (if (:opponent a)
                        (format "Matches between %s and %s:\n" (:team a) (:opponent a))
                        "")
                      (fmt/matches page total))))}

   {:name "team_stats"
    :description "Win/loss/draw record, goals for/against, and win rate for a team, optionally filtered by season, competition, and venue (home/away)."
    :inputSchema {:type "object"
                  :properties {:team        (prop "string" "Team name (required).")
                               :season      (prop "integer" "Season year filter.")
                               :competition (prop "string" "Competition filter.")
                               :venue       (prop "string" "\"home\", \"away\", or \"all\" (default).")}
                  :required ["team"]}
    :handler (fn [db a]
               (fmt/team-stats
                (q/team-stats db (:team a)
                              {:season (->int (:season a))
                               :competition (non-blank (:competition a))
                               :venue (case (some-> (:venue a) str str/lower-case)
                                        "home" :home "away" :away :all)})))}

   {:name "head_to_head"
    :description "Head-to-head record between two teams across all competitions, with recent matches."
    :inputSchema {:type "object"
                  :properties {:team1 (prop "string" "First team (required).")
                               :team2 (prop "string" "Second team (required).")
                               :show  (prop "integer" "How many recent matches to list (default 5).")}
                  :required ["team1" "team2"]}
    :handler (fn [db a]
               (fmt/head-to-head (q/head-to-head db (:team1 a) (:team2 a))
                                 (or (->int (:show a)) 5)))}

   {:name "search_players"
    :description "Search FIFA player data by name, nationality, club, position, or minimum overall rating. Sorted by rating."
    :inputSchema {:type "object"
                  :properties {:name        (prop "string" "Player name substring, e.g. \"Neymar\".")
                               :nationality (prop "string" "Nationality, e.g. \"Brazil\".")
                               :club        (prop "string" "Club name substring.")
                               :position    (prop "string" "Position code, e.g. \"ST\", \"GK\", \"LW\".")
                               :min_overall (prop "integer" "Minimum FIFA overall rating.")
                               :limit       (prop "integer" "Max players to return (default 10).")}}
    :handler (fn [db a]
               (fmt/players
                (q/search-players db {:name (non-blank (:name a))
                                      :nationality (non-blank (:nationality a))
                                      :club (non-blank (:club a))
                                      :position (non-blank (:position a))
                                      :min-overall (->int (:min_overall a))
                                      :limit (or (->int (:limit a)) 10)})))}

   {:name "club_roster"
    :description "List players belonging to a club with the squad size and average overall rating."
    :inputSchema {:type "object"
                  :properties {:club (prop "string" "Club name (required), e.g. \"Santos\".")}
                  :required ["club"]}
    :handler (fn [db a] (fmt/club-roster (q/club-roster db (:club a))))}

   {:name "standings"
    :description "Computed league standings (3pts win, 1pt draw) for a competition and season, derived from match results."
    :inputSchema {:type "object"
                  :properties {:competition (prop "string" "Competition, e.g. \"Brasileirão Série A\".")
                               :season      (prop "integer" "Season year (required).")
                               :top         (prop "integer" "Show only the top N rows (default all).")}
                  :required ["season"]}
    :handler (fn [db a]
               (let [season (->int (:season a))
                     comp (or (non-blank (:competition a)) "Brasileirão Série A")
                     rows (q/standings db {:competition comp :season season})]
                 (str (format "%s %d Final Standings (calculated from matches):\n" comp season)
                      (fmt/standings rows (or (->int (:top a)) 0)))))}

   {:name "champion"
    :description "The calculated champion (top of the standings) for a competition and season."
    :inputSchema {:type "object"
                  :properties {:competition (prop "string" "Competition (default \"Brasileirão Série A\").")
                               :season      (prop "integer" "Season year (required).")}
                  :required ["season"]}
    :handler (fn [db a]
               (let [season (->int (:season a))
                     comp (or (non-blank (:competition a)) "Brasileirão Série A")
                     champ (q/champion db {:competition comp :season season})]
                 (if champ
                   (format "%s %d champion (calculated): %s with %d points (%dW, %dD, %dL)."
                           comp season (:team champ) (:points champ)
                           (:win champ) (:draw champ) (:loss champ))
                   (format "No data for %s %d." comp season))))}

   {:name "competition_stats"
    :description "Aggregate statistics for a competition/season: match count, total & average goals, home/away win rates."
    :inputSchema {:type "object"
                  :properties {:competition (prop "string" "Competition filter.")
                               :season      (prop "integer" "Season year filter.")}}
    :handler (fn [db a]
               (fmt/competition-stats
                (q/competition-stats db {:competition (non-blank (:competition a))
                                         :season (->int (:season a))})))}

   {:name "biggest_wins"
    :description "Matches with the largest goal margin, optionally filtered by competition/season."
    :inputSchema {:type "object"
                  :properties {:competition (prop "string" "Competition filter.")
                               :season      (prop "integer" "Season year filter.")
                               :limit       (prop "integer" "How many matches (default 10).")}}
    :handler (fn [db a]
               (let [ms (q/biggest-wins db {:competition (non-blank (:competition a))
                                            :season (->int (:season a))
                                            :limit (or (->int (:limit a)) 10)})]
                 (str "Biggest victories:\n" (fmt/matches ms))))}

   {:name "best_record"
    :description "Teams ranked by win rate within a competition/season (home/away/all), with a minimum games threshold."
    :inputSchema {:type "object"
                  :properties {:competition (prop "string" "Competition filter.")
                               :season      (prop "integer" "Season year filter.")
                               :venue       (prop "string" "\"home\", \"away\", or \"all\" (default).")
                               :limit       (prop "integer" "How many teams (default 10).")}}
    :handler (fn [db a]
               (let [rows (q/best-record db {:competition (non-blank (:competition a))
                                             :season (->int (:season a))
                                             :venue (case (some-> (:venue a) str str/lower-case)
                                                      "home" :home "away" :away :all)
                                             :limit (or (->int (:limit a)) 10)})]
                 (if (empty? rows)
                   "No teams matched the criteria."
                   (str/join "\n"
                             (map-indexed
                              (fn [i s]
                                (format "%d. %s - %.1f%% win rate (%dW, %dD, %dL)"
                                        (inc i) (:team s) (:win-rate s)
                                        (:win s) (:draw s) (:loss s)))
                              rows)))))}

   {:name "list_competitions"
    :description "List all competitions available in the dataset."
    :inputSchema {:type "object" :properties {}}
    :handler (fn [db _] (str "Competitions:\n- " (str/join "\n- " (q/list-competitions db))))}

   {:name "list_seasons"
    :description "List the seasons available, optionally for one competition."
    :inputSchema {:type "object"
                  :properties {:competition (prop "string" "Competition filter (optional).")}}
    :handler (fn [db a]
               (str "Seasons: " (str/join ", " (q/list-seasons db (non-blank (:competition a))))))}])

(def ^:private tool-index
  (into {} (map (juxt :name identity) tools)))

;; ----------------------------------------------------------------------------
;; JSON-RPC plumbing
;; ----------------------------------------------------------------------------

(defn- result [id v] {:jsonrpc "2.0" :id id :result v})
(defn- error  [id code msg] {:jsonrpc "2.0" :id id :error {:code code :message msg}})

(defn- tool-listing
  "Public schema view of the tools (drops the internal :handler)."
  []
  (mapv #(select-keys % [:name :description :inputSchema]) tools))

(defn- call-tool
  "Invoke a named tool. Returns an MCP tools/call result map (with :isError on
   failure) - never throws."
  [db name args]
  (if-let [tool (get tool-index name)]
    (try
      (let [text ((:handler tool) db (or args {}))]
        {:content [{:type "text" :text text}] :isError false})
      (catch Exception e
        {:content [{:type "text" :text (str "Error running tool '" name "': " (.getMessage e))}]
         :isError true}))
    {:content [{:type "text" :text (str "Unknown tool: " name)}] :isError true}))

(defn handle-request
  "Pure dispatch for a single parsed JSON-RPC request map. Returns the response
   map to send back, or nil for notifications (which take no response).
   `db` is the loaded knowledge graph."
  [db {:keys [id method params]}]
  (case method
    "initialize"
    (result id {:protocolVersion protocol-version
                :capabilities {:tools {}}
                :serverInfo server-info})

    "notifications/initialized" nil
    "initialized" nil

    "ping" (result id {})

    "tools/list" (result id {:tools (tool-listing)})

    "tools/call"
    (let [{:keys [name arguments]} params]
      (result id (call-tool db name arguments)))

    ;; Unknown method: only error on requests (those with an id), ignore notifications.
    (if (nil? id)
      nil
      (error id -32601 (str "Method not found: " method)))))

;; ----------------------------------------------------------------------------
;; stdio transport
;; ----------------------------------------------------------------------------

(defn- parse-request [line]
  (try (json/parse-string line true)
       (catch Exception _ ::parse-error)))

(defn serve!
  "Run the blocking stdio JSON-RPC loop: read newline-delimited JSON requests
   from `in` (default *in*), dispatch against `db`, and write newline-delimited
   JSON responses to `out` (default *out*). Returns when EOF is reached."
  ([db] (serve! db *in* *out*))
  ([db in out]
   (let [reader (clojure.java.io/reader in)
         writer (clojure.java.io/writer out)
         emit (fn [resp]
                (when resp
                  (.write writer (json/generate-string resp))
                  (.write writer "\n")
                  (.flush writer)))]
     (loop []
       (when-let [line (.readLine reader)]
         (when-not (str/blank? line)
           (let [req (parse-request line)]
             (if (= req ::parse-error)
               (emit (error nil -32700 "Parse error"))
               (emit (handle-request db req)))))
         (recur))))))
