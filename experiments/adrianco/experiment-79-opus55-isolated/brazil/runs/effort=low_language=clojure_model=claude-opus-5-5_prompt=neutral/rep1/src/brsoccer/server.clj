(ns brsoccer.server
  "Model Context Protocol server (JSON-RPC 2.0 over stdio, one message per
  line) exposing the Brazilian soccer data as tools.

  Start with `clojure -M:run`. stdout carries protocol messages only;
  diagnostics go to stderr."
  (:require [brsoccer.data :as data]
            [brsoccer.format :as fmt]
            [brsoccer.query :as q]
            [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clojure.string :as str])
  (:gen-class))

(def server-info {:name "brazilian-soccer-mcp" :version "1.0.0"})
(def supported-protocols #{"2024-11-05" "2025-03-26" "2025-06-18"})
(def default-protocol "2025-06-18")

;; ---------------------------------------------------------------------------
;; Argument handling

(defn- invalid [msg & args]
  (throw (ex-info (apply format msg args) {:type :invalid-argument})))

(defn- text-arg [args k]
  (let [v (get args k)]
    (cond (nil? v) nil
          (string? v) (when-not (str/blank? v) (str/trim v))
          :else (str v))))

(defn- int-arg [args k]
  (let [v (get args k)]
    (cond (nil? v) nil
          (integer? v) (long v)
          (and (number? v) (== v (long v))) (long v)
          (and (string? v) (re-matches #"\s*-?\d+\s*" v)) (parse-long (str/trim v))
          (and (string? v) (str/blank? v)) nil
          :else (invalid "%s must be an integer (got %s)" (name k) (pr-str v)))))

(defn- date-arg [args k]
  (when-let [v (text-arg args k)]
    (or (data/iso-date v)
        (invalid "%s must be a date formatted YYYY-MM-DD (got \"%s\")" (name k) v))))

(defn- required [args k]
  (or (text-arg args k) (invalid "Missing required argument: %s" (name k))))

(defn- limit-arg [args]
  (when-let [n (int-arg args :limit)]
    (when (< n 1) (invalid "limit must be at least 1"))
    (min n 200)))

(defn- match-filters [args]
  {:team (text-arg args :team)
   :opponent (text-arg args :opponent)
   :venue (text-arg args :venue)
   :competition (text-arg args :competition)
   :season (int-arg args :season)
   :date-from (date-arg args :date_from)
   :date-to (date-arg args :date_to)
   :stage (text-arg args :stage)
   :round (int-arg args :round)
   :limit (limit-arg args)})

;; ---------------------------------------------------------------------------
;; Tools

(def ^:private competition-prop
  {:type "string"
   :description "Competition: Brasileirão (Série A), Série B, Série C, Copa do Brasil or Libertadores"})
(def ^:private season-prop {:type "integer" :description "Season year, e.g. 2019"})
(def ^:private limit-prop {:type "integer" :description "Maximum rows to list"})
(def ^:private venue-prop
  {:type "string" :enum ["home" "away" "either"]
   :description "Count only the team's home or away games (default either)"})
(defn- team-prop [what]
  {:type "string" :description (str what " Any common spelling works (\"Sao Paulo\", \"São Paulo-SP\", \"Atletico Mineiro\").")})

(def tools
  [{:name "search_matches"
    :description "Find matches by team, opponent, venue, competition, season, date range, round or stage (e.g. stage=final for Copa do Brasil / Libertadores finals). Most recent first, so limit=1 answers 'when did X last play Y'."
    :inputSchema {:type "object"
                  :properties {:team (team-prop "Team that played.")
                               :opponent (team-prop "The other team.")
                               :venue venue-prop
                               :competition competition-prop
                               :season season-prop
                               :date_from {:type "string" :description "Earliest date, YYYY-MM-DD"}
                               :date_to {:type "string" :description "Latest date, YYYY-MM-DD"}
                               :stage {:type "string" :description "Knockout stage: group stage, round of 16, quarterfinals, semifinals, final"}
                               :round {:type "integer" :description "Round number (league and cup files)"}
                               :limit limit-prop}}
    :handler (fn [db args]
               (let [f (match-filters args)]
                 (fmt/matches (q/find-matches db f) f)))}

   {:name "head_to_head"
    :description "Compare two teams: every meeting in the dataset plus wins, draws and goals for each side."
    :inputSchema {:type "object"
                  :properties {:team_a (team-prop "First team.")
                               :team_b (team-prop "Second team.")
                               :competition competition-prop
                               :season season-prop
                               :limit limit-prop}
                  :required ["team_a" "team_b"]}
    :handler (fn [db args]
               (let [f (assoc (match-filters args)
                              :team-a (required args :team_a)
                              :team-b (required args :team_b))]
                 (fmt/head-to-head (q/head-to-head db f) f)))}

   {:name "team_stats"
    :description "A team's record: matches, wins, draws, losses, goals for/against and win rate, optionally for one season, competition or venue (home/away)."
    :inputSchema {:type "object"
                  :properties {:team (team-prop "Team.")
                               :season season-prop
                               :competition competition-prop
                               :venue venue-prop}
                  :required ["team"]}
    :handler (fn [db args]
               (fmt/team-stats (q/team-stats db (assoc (match-filters args) :team (required args :team)))))}

   {:name "standings"
    :description "League table for a season calculated from match results: champion, points, relegation zone. Defaults to Brasileirão Série A (2003-2023)."
    :inputSchema {:type "object"
                  :properties {:season season-prop :competition competition-prop}
                  :required ["season"]}
    :handler (fn [db args]
               (fmt/standings (q/standings db {:season (or (int-arg args :season)
                                                           (invalid "Missing required argument: season"))
                                               :competition (text-arg args :competition)})))}

   {:name "rank_teams"
    :description "Rank teams by a metric over a competition/season and venue, e.g. best away record (venue=away, metric=win_rate) or most goals scored (metric=goals_for)."
    :inputSchema {:type "object"
                  :properties {:metric {:type "string" :enum (vec (sort (keys q/metrics)))
                                        :description "Default points_per_match"}
                               :venue venue-prop
                               :competition competition-prop
                               :season season-prop
                               :min_matches {:type "integer" :description "Ignore teams with fewer games (default 20, or 1 when a season is given)"}
                               :limit limit-prop}}
    :handler (fn [db args]
               (fmt/ranking (q/rank-teams db (assoc (match-filters args)
                                                    :metric (text-arg args :metric)
                                                    :min-matches (int-arg args :min_matches)))))}

   {:name "competition_stats"
    :description "Aggregate statistics: average goals per match, home win / draw / away win rates. Optionally for one competition, season or team."
    :inputSchema {:type "object"
                  :properties {:competition competition-prop :season season-prop
                               :team (team-prop "Only this team's matches.")}}
    :handler (fn [db args]
               (fmt/competition-stats (q/competition-stats db (match-filters args))))}

   {:name "biggest_wins"
    :description "Matches with the largest winning margins, optionally for one competition, season or team."
    :inputSchema {:type "object"
                  :properties {:competition competition-prop :season season-prop
                               :team (team-prop "Only this team's matches.")
                               :limit limit-prop}}
    :handler (fn [db args]
               (fmt/biggest-wins (q/biggest-wins db (match-filters args))))}

   {:name "team_competitions"
    :description "Which competitions and seasons a team appears in across all match files, with its record in each."
    :inputSchema {:type "object"
                  :properties {:team (team-prop "Team.")}
                  :required ["team"]}
    :handler (fn [db args]
               (fmt/team-competitions (q/team-competitions db {:team (required args :team)})))}

   {:name "derbies"
    :description "Matches between traditional rivals (Fla-Flu, Derby Paulista, Grenal, Clássico Mineiro ...), optionally for one season, competition or team."
    :inputSchema {:type "object"
                  :properties {:season season-prop :competition competition-prop
                               :team (team-prop "Only derbies of this team.")
                               :limit limit-prop}}
    :handler (fn [db args]
               (let [f (match-filters args)]
                 (fmt/derbies (q/derbies db f) f)))}

   {:name "search_players"
    :description "Search the FIFA player database by name, nationality, club, position (code such as ST, or goalkeeper/defender/midfielder/forward), minimum overall rating or maximum age. Best rated first."
    :inputSchema {:type "object"
                  :properties {:name {:type "string" :description "Part of the player's name"}
                               :nationality {:type "string" :description "Country, e.g. Brazil"}
                               :club {:type "string" :description "Club name or part of it"}
                               :position {:type "string" :description "Position code or group"}
                               :min_overall {:type "integer" :description "Minimum FIFA overall rating"}
                               :max_age {:type "integer" :description "Maximum age"}
                               :limit limit-prop}}
    :handler (fn [db args]
               (fmt/players (q/search-players db {:name (text-arg args :name)
                                                  :nationality (text-arg args :nationality)
                                                  :club (text-arg args :club)
                                                  :position (text-arg args :position)
                                                  :min-overall (int-arg args :min_overall)
                                                  :max-age (int-arg args :max_age)
                                                  :limit (limit-arg args)})))}

   {:name "player_details"
    :description "Full FIFA profile of the player(s) matching a name: club, position, ratings, physical attributes and best skills."
    :inputSchema {:type "object"
                  :properties {:name {:type "string" :description "Player name or part of it"}
                               :limit limit-prop}
                  :required ["name"]}
    :handler (fn [db args]
               (fmt/player-details (q/search-players db {:name (required args :name)
                                                         :limit (or (limit-arg args) 3)})))}

   {:name "brazilian_club_squads"
    :description "FIFA players grouped by Brazilian club (clubs found in both the player file and the league match files), with squad size and average rating. Optionally only players of one nationality."
    :inputSchema {:type "object"
                  :properties {:nationality {:type "string" :description "e.g. Brazil"}}}
    :handler (fn [db args]
               (let [f {:nationality (text-arg args :nationality)}]
                 (fmt/club-squads (q/brazilian-club-squads db f) f)))}

   {:name "team_profile"
    :description "Cross-file profile of a club: record per competition, most recent results and its top-rated FIFA players."
    :inputSchema {:type "object"
                  :properties {:team (team-prop "Team.") :limit limit-prop}
                  :required ["team"]}
    :handler (fn [db args]
               (fmt/team-profile (q/team-profile db {:team (required args :team)
                                                     :limit (limit-arg args)})))}

   {:name "list_competitions"
    :description "Overview of the dataset: competitions, season ranges, match and player counts, source files."
    :inputSchema {:type "object" :properties {}}
    :handler (fn [db _] (fmt/competitions (q/list-competitions db)))}])

(def ^:private tool-index (into {} (map (juxt :name identity)) tools))

(defn call-tool
  "Runs a tool and returns an MCP tool result. Bad arguments and lookups
  that fail are reported in-band (isError) so the model can correct itself."
  [db tool-name args]
  (let [{:keys [handler]} (tool-index tool-name)]
    (try
      {:content [{:type "text" :text (handler db (or args {}))}]
       :isError false}
      (catch clojure.lang.ExceptionInfo e
        (if (= :invalid-argument (:type (ex-data e)))
          {:content [{:type "text" :text (str "Error: " (ex-message e))}]
           :isError true}
          (throw e))))))

;; ---------------------------------------------------------------------------
;; JSON-RPC

(defn- rpc-error [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn- rpc-result [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn handle-request
  "Response map for one decoded JSON-RPC message, or nil for notifications.
  `db` is a delay so the CSV files are only read when a tool is first called."
  [db {:keys [id method params] :as msg}]
  (let [notification? (and (map? msg) (not (contains? msg :id)))]
    (cond
      (not (and (map? msg) (string? method)))
      (rpc-error (:id msg) -32600 "Invalid Request")

      notification? nil

      :else
      (case method
        "initialize"
        (rpc-result id {:protocolVersion (or (supported-protocols (:protocolVersion params))
                                             default-protocol)
                        :capabilities {:tools {:listChanged false}}
                        :serverInfo server-info
                        :instructions "Brazilian soccer knowledge base: Brasileirão Série A/B/C, Copa do Brasil and Copa Libertadores matches (2003-2023) plus the FIFA player database. All answers are computed from the bundled Kaggle CSV files."})

        "ping" (rpc-result id {})

        "tools/list"
        (rpc-result id {:tools (mapv #(dissoc % :handler) tools)})

        "tools/call"
        (let [tool-name (:name params)
              args (:arguments params)]
          (cond
            (not (contains? tool-index tool-name))
            (rpc-error id -32602 (str "Unknown tool: " tool-name))

            (not (or (nil? args) (map? args)))
            (rpc-error id -32602 "Tool arguments must be an object")

            :else
            (try
              (rpc-result id (call-tool @db tool-name args))
              (catch Exception e
                (binding [*out* *err*] (println "tool failure:" tool-name (ex-message e)))
                (rpc-error id -32603 (str "Internal error: " (ex-message e)))))))

        (rpc-error id -32601 (str "Method not found: " method))))))

(defn handle-line
  "JSON text in, JSON text out (nil when no response is due)."
  [db line]
  (let [msg (try (json/read-str line :key-fn keyword)
                 (catch Exception _ ::unparseable))]
    (some-> (if (= msg ::unparseable)
              (rpc-error nil -32700 "Parse error")
              (handle-request db msg))
            (json/write-str :escape-unicode false :escape-slash false))))

(defn serve
  "Reads newline-delimited JSON-RPC from `in` and answers on `out` until EOF."
  [db in out]
  (let [reader (io/reader in :encoding "UTF-8")
        writer (io/writer out :encoding "UTF-8")]
    (doseq [line (line-seq reader)
            :when (not (str/blank? line))]
      (when-let [response (handle-line db line)]
        (.write writer ^String response)
        (.write writer "\n")
        (.flush writer)))))

(defn -main [& _]
  (serve data/db System/in System/out)
  (shutdown-agents))
