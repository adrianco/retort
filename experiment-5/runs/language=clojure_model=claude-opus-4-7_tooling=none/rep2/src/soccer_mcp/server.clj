(ns soccer-mcp.server
  "MCP server implementation for the Brazilian soccer knowledge graph.

   Speaks JSON-RPC 2.0 over stdio (one JSON object per line). The server is
   stateless aside from the in-memory dataset that is loaded once at startup.

   Tool surface (see tool-defs):
     find_matches        — search match data with team/comp/season/date filters
     team_stats          — W/D/L, goals, points for a team in a competition
     head_to_head        — record between two teams
     standings           — league table calculated from match results
     biggest_wins        — top-N matches by goal difference
     league_averages     — goals/match and home-win rate
     find_players        — FIFA player search
     players_by_club     — count + avg overall grouped by club

   The transport layer is deliberately small: every request is dispatched by
   method through a multi-method, and tool calls are dispatched by name in
   `handle-tools-call`. All stdout is reserved for protocol messages; logs go
   to stderr."
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [soccer-mcp.queries :as q])
  (:import (java.io BufferedReader BufferedWriter InputStreamReader
                    OutputStreamWriter PrintWriter)))

(def protocol-version "2024-11-05")

(def server-info
  {:name    "soccer-mcp"
   :version "0.1.0"})

;; ----------------------------------------------------------------------------
;; Logging (always to stderr)

(defn- log [& args]
  (binding [*out* *err*]
    (println (str/join " " (map str args)))))

;; ----------------------------------------------------------------------------
;; Pretty formatters — produce the `text` payloads users see

(defn- competition-name [k]
  (case k
    :brasileirao            "Brasileirão"
    :brasileirao-historical "Brasileirão (historical)"
    :copa-do-brasil         "Copa do Brasil"
    :libertadores           "Copa Libertadores"
    :other                  "Other"
    (str k)))

(defn- fmt-match [m]
  (let [c (competition-name (:competition m))
        d (or (:date m) "????-??-??")
        round (when (:round m) (str " R" (:round m)))
        stage (when (:stage m) (str " — " (:stage m)))]
    (format "%s: %s %d-%d %s (%s%s%s)"
            d (:home m) (:home-goal m) (:away-goal m) (:away m)
            c (or round "") (or stage ""))))

(defn- fmt-matches [ms]
  (if (empty? ms)
    "No matches found."
    (str/join "\n"
              (concat
               (map fmt-match ms)
               [(format "\n%d match%s total."
                        (count ms) (if (= 1 (count ms)) "" "es"))]))))

(defn- fmt-pct [r]
  (format "%.1f%%" (* 100.0 r)))

(defn- competition-label
  "Render whatever the user passed as a competition (string alias, keyword,
   or nil) as a human label."
  [c]
  (cond
    (nil? c)     nil
    (keyword? c) (competition-name c)
    :else (competition-name
           (keyword (str/replace (str/lower-case (str c)) "_" "-")))))

(defn- fmt-team-stats [s]
  (format
   (str "%s record%s%s%s\n"
        "Played: %d  Wins: %d  Draws: %d  Losses: %d\n"
        "Goals for: %d  Goals against: %d  Diff: %+d\n"
        "Points: %d  Win rate: %s")
   (:team s)
   (if-let [c (competition-label (:competition s))] (str " (" c ")") "")
   (if (:season s) (str " " (:season s)) "")
   (if-let [side (:side s)]
     (str " — " (str/lower-case (str (if (keyword? side) (name side) side))) " only")
     "")
   (:played s) (:wins s) (:draws s) (:losses s)
   (:goals-for s) (:goals-against s) (:goal-diff s)
   (:points s) (fmt-pct (:win-rate s))))

(defn- fmt-h2h [h]
  (format
   (str "%s vs %s — head-to-head\n"
        "Matches: %d\n"
        "%s wins: %d   %s wins: %d   Draws: %d\n"
        "Goals: %s %d - %d %s")
   (:team-a h) (:team-b h)
   (:matches h)
   (:team-a h) (:a-wins h)
   (:team-b h) (:b-wins h)
   (:draws h)
   (:team-a h) (:a-goals h) (:b-goals h) (:team-b h)))

(defn- fmt-standings [rows]
  (if (empty? rows)
    "No standings — no matches in the filter."
    (str/join "\n"
              (cons
               (format "%-3s %-30s %4s %4s %4s %4s %5s %5s %4s %4s"
                       "#" "Team" "P" "W" "D" "L" "GF" "GA" "GD" "Pts")
               (map-indexed
                (fn [i r]
                  (format "%-3d %-30s %4d %4d %4d %4d %5d %5d %+4d %4d"
                          (inc i)
                          (subs (str (:team r)) 0
                                (min 30 (count (str (:team r)))))
                          (:played r) (:wins r) (:draws r) (:losses r)
                          (:goals-for r) (:goals-against r)
                          (:goal-diff r) (:points r)))
                rows)))))

(defn- fmt-biggest [ms]
  (if (empty? ms)
    "No matches found."
    (str/join "\n"
              (map-indexed
               (fn [i m]
                 (format "%d. %s" (inc i) (fmt-match m)))
               ms))))

(defn- fmt-averages [m]
  (format "Matches: %d  Total goals: %d  Average: %.2f goals/match"
          (:matches m) (:goals m) (:avg m)))

(defn- fmt-home-rate [m]
  (format "Matches: %d  Home wins: %d  Home-win rate: %s"
          (:matches m) (:home-wins m) (fmt-pct (:rate m))))

(defn- fmt-player [p]
  (format "%s — %s, Overall %s, %s, %s"
          (or (:name p) "?")
          (or (:nationality p) "?")
          (or (:overall p) "?")
          (or (:position p) "?")
          (or (:club p) "Unattached")))

(defn- fmt-players [ps]
  (if (empty? ps)
    "No players found."
    (str/join "\n"
              (map-indexed
               (fn [i p] (format "%d. %s" (inc i) (fmt-player p)))
               ps))))

(defn- fmt-clubs [rows]
  (if (empty? rows)
    "No clubs found."
    (str/join "\n"
              (map (fn [r]
                     (format "%s — %d players (avg overall %.1f)"
                             (or (:club r) "?")
                             (:players r) (:avg-overall r)))
                   rows))))

;; ----------------------------------------------------------------------------
;; Tool definitions and dispatcher

(def tool-defs
  [{:name "find_matches"
    :description "Search Brazilian soccer matches across all loaded competitions. Supports team, competition, season, and date-range filters."
    :inputSchema
    {:type "object"
     :properties
     {:team        {:type "string" :description "Either-side team name match (substring, case- and accent-insensitive)."}
      :team_a      {:type "string" :description "First team for a head-to-head listing."}
      :team_b      {:type "string" :description "Second team for a head-to-head listing."}
      :side        {:type "string" :enum ["home" "away"]}
      :competition {:type "string" :description "One of: brasileirao, brasileirao-historical, copa-do-brasil, libertadores, extended."}
      :season      {:type "integer"}
      :from        {:type "string" :description "Inclusive start date (YYYY-MM-DD)."}
      :to          {:type "string" :description "Inclusive end date (YYYY-MM-DD)."}
      :limit       {:type "integer" :description "Maximum number of matches to return (0 = unlimited)."}}}}

   {:name "team_stats"
    :description "Aggregate wins/draws/losses, goals for/against, and points for one team. Filters: season, competition, side."
    :inputSchema
    {:type "object"
     :required ["team"]
     :properties
     {:team        {:type "string"}
      :season      {:type "integer"}
      :competition {:type "string"}
      :side        {:type "string" :enum ["home" "away"]}}}}

   {:name "head_to_head"
    :description "Head-to-head record between two teams across the dataset (filters: competition, season, date range)."
    :inputSchema
    {:type "object"
     :required ["team_a" "team_b"]
     :properties
     {:team_a      {:type "string"}
      :team_b      {:type "string"}
      :competition {:type "string"}
      :season      {:type "integer"}}}}

   {:name "standings"
    :description "Calculate a league table from match results for a season/competition."
    :inputSchema
    {:type "object"
     :properties
     {:competition {:type "string"}
      :season      {:type "integer"}
      :from        {:type "string"}
      :to          {:type "string"}
      :limit       {:type "integer" :description "Number of rows returned (default 20)."}}}}

   {:name "biggest_wins"
    :description "Return the N matches with the largest goal difference, optionally filtered."
    :inputSchema
    {:type "object"
     :properties
     {:n           {:type "integer" :description "How many matches (default 10)."}
      :team        {:type "string"}
      :competition {:type "string"}
      :season      {:type "integer"}}}}

   {:name "league_averages"
    :description "Aggregate league-wide statistics: average goals per match and home-win rate."
    :inputSchema
    {:type "object"
     :properties
     {:competition {:type "string"}
      :season      {:type "integer"}
      :team        {:type "string"}}}}

   {:name "find_players"
    :description "Search FIFA player data by name, nationality, club, position, or minimum overall rating."
    :inputSchema
    {:type "object"
     :properties
     {:name        {:type "string"}
      :nationality {:type "string"}
      :club        {:type "string"}
      :position    {:type "string"}
      :min_overall {:type "integer"}
      :limit       {:type "integer" :description "Default 25, 0 = unlimited."}
      :sort        {:type "string" :enum ["overall" "name"]}}}}

   {:name "players_by_club"
    :description "Count players (default: Brazilian players) grouped by club and ranked by player count then average overall."
    :inputSchema
    {:type "object"
     :properties
     {:nationality {:type "string" :description "Default: Brazil"}
      :club_filter {:type "string"}
      :limit       {:type "integer"}}}}])

(defn- kw-args
  "Convert a JSON-RPC argument map (string keys) to kw-keyed Clojure map for
   query functions. Recognized aliases are mapped from snake_case → kebab."
  [m]
  (reduce-kv (fn [acc k v]
               (let [k' (-> (name k)
                            (str/replace "_" "-")
                            keyword)]
                 (assoc acc k' v)))
             {} (or m {})))

(defn- call-tool
  "Dispatch a tool name to the corresponding query and format its result as
   text. Returns the {:content [...]} payload directly."
  [dataset name args]
  (let [a (kw-args args)
        text
        (case name
          "find_matches"
          (let [opts (-> a (assoc :limit (or (:limit a) 25)))
                ms   (q/find-matches dataset opts)]
            (fmt-matches ms))

          "team_stats"
          (fmt-team-stats (q/team-stats dataset a))

          "head_to_head"
          (fmt-h2h (q/head-to-head dataset a))

          "standings"
          (let [limit (or (:limit a) 20)
                rows  (q/standings dataset (dissoc a :limit))]
            (fmt-standings (take limit rows)))

          "biggest_wins"
          (fmt-biggest (q/biggest-wins dataset
                                       (update a :n #(or % 10))))

          "league_averages"
          (let [avg (q/average-goals dataset a)
                hwr (q/home-win-rate dataset a)]
            (str (fmt-averages avg) "\n" (fmt-home-rate hwr)))

          "find_players"
          (let [opts (-> a (assoc :limit (or (:limit a) 25)))
                ps   (q/find-players dataset opts)]
            (fmt-players ps))

          "players_by_club"
          (fmt-clubs (q/players-by-club dataset a))

          (throw (ex-info (str "Unknown tool: " name) {:code -32601})))]
    {:content [{:type "text" :text text}]}))

;; ----------------------------------------------------------------------------
;; JSON-RPC handler

(defn- error-response [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn- result-response [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn handle-message
  "Pure handler — takes (dataset, parsed JSON-RPC message) and returns a
   response map or nil (for notifications). Public so tests can drive it
   without stdio."
  [dataset msg]
  (let [{:strs [id method params]} msg]
    (try
      (case method
        "initialize"
        (result-response id
                         {:protocolVersion protocol-version
                          :capabilities    {:tools {}}
                          :serverInfo      server-info})

        "initialized"   nil
        "notifications/initialized" nil

        "ping"
        (result-response id {})

        "tools/list"
        (result-response id {:tools tool-defs})

        "tools/call"
        (let [tool-name (get params "name")
              tool-args (get params "arguments")]
          (result-response id (call-tool dataset tool-name tool-args)))

        (if (nil? id)
          nil ;; unknown notification — ignore
          (error-response id -32601 (str "Method not found: " method))))
      (catch Exception e
        (log "Error handling" method ":" (.getMessage e))
        (error-response id -32603 (.getMessage e))))))

;; ----------------------------------------------------------------------------
;; Stdio main loop

(defn- write-line! [^BufferedWriter w obj]
  (.write w ^String (json/write-str obj))
  (.newLine w)
  (.flush w))

(defn run-stdio!
  "Run the MCP server on stdin/stdout. Blocks until stdin closes."
  [dataset]
  (let [in  (BufferedReader. (InputStreamReader. System/in "UTF-8"))
        out (BufferedWriter. (OutputStreamWriter. System/out "UTF-8"))]
    (log "soccer-mcp ready:"
         (count (:matches dataset)) "matches,"
         (count (:players dataset)) "players")
    (loop []
      (when-let [line (.readLine in)]
        (when-not (str/blank? line)
          (try
            (let [msg  (json/read-str line)
                  resp (handle-message dataset msg)]
              (when resp
                (write-line! out resp)))
            (catch Exception e
              (log "Parse error:" (.getMessage e))
              (write-line! out (error-response nil -32700 "Parse error")))))
        (recur)))))
