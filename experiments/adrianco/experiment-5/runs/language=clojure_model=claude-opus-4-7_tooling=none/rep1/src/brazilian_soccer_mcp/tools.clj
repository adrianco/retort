(ns brazilian-soccer-mcp.tools
  "MCP tool definitions for the Brazilian soccer dataset.

  Each tool is registered as a map: {:name :description :schema :handler}.
  The handler takes the dataset and a parameter map and returns a string
  ready to be wrapped in a `content` text block for MCP responses."
  (:require [brazilian-soccer-mcp.queries :as q]
            [clojure.string :as str]))

(defn- ->int [v]
  (cond
    (nil? v) nil
    (integer? v) v
    (number? v) (long v)
    (string? v) (try (Long/parseLong (str/trim v)) (catch Exception _ nil))
    :else nil))

(defn- limit-arg [params default]
  (or (->int (:limit params)) default))

;; ---------------------------------------------------------------------------
;; Tool handlers
;; ---------------------------------------------------------------------------

(defn- tool-search-matches [dataset params]
  (let [opts (-> {}
                 (cond-> (:team params)        (assoc :team (:team params)))
                 (cond-> (:home params)        (assoc :home (:home params)))
                 (cond-> (:away params)        (assoc :away (:away params)))
                 (cond-> (:competition params) (assoc :competition (:competition params)))
                 (cond-> (:season params)      (assoc :season (->int (:season params))))
                 (cond-> (:season_from params) (assoc :season-from (->int (:season_from params))))
                 (cond-> (:season_to params)   (assoc :season-to (->int (:season_to params))))
                 (cond-> (:date_from params)   (assoc :date-from (:date_from params)))
                 (cond-> (:date_to params)     (assoc :date-to (:date_to params)))
                 (cond-> (:stage params)       (assoc :stage (:stage params)))
                 (cond-> (:round params)       (assoc :round (:round params))))
        ms   (q/filter-matches dataset (assoc opts :limit (limit-arg params 50)))]
    (str "Matches found: " (count ms) "\n" (q/format-matches ms))))

(defn- tool-head-to-head [dataset params]
  (let [{:keys [team_a team_b]} params]
    (if-not (and team_a team_b)
      "Both team_a and team_b are required."
      (let [{:keys [matches aggregate total]} (q/head-to-head dataset team_a team_b)
            {:keys [a-wins b-wins draws]}     aggregate]
        (str/join "\n"
          [(format "Head-to-head: %s vs %s — %d matches in dataset"
                   team_a team_b total)
           (format "Aggregate: %s %d wins, %s %d wins, %d draws"
                   team_a a-wins team_b b-wins draws)
           ""
           (q/format-matches (take (limit-arg params 20) matches))])))))

(defn- tool-team-stats [dataset params]
  (let [team (:team params)]
    (if-not team
      "Parameter `team` is required."
      (let [opts (cond-> {}
                   (:season params)      (assoc :season (->int (:season params)))
                   (:competition params) (assoc :competition (:competition params))
                   (:season_from params) (assoc :season-from (->int (:season_from params)))
                   (:season_to params)   (assoc :season-to (->int (:season_to params))))
            s    (q/team-stats dataset team opts)]
        (q/format-team-stats s)))))

(defn- tool-standings [dataset params]
  (let [season (->int (:season params))]
    (if-not season
      "Parameter `season` is required (integer year)."
      (let [comp (or (:competition params) "Brasileirão")
            rows (q/standings dataset {:season season :competition comp})]
        (str (format "%s %d standings (calculated from matches):" comp season)
             "\n"
             (q/format-standings rows))))))

(defn- tool-search-players [dataset params]
  (let [ps (q/search-players dataset
             {:name        (:name params)
              :nationality (:nationality params)
              :club        (:club params)
              :position    (:position params)
              :min-overall (->int (:min_overall params))
              :sort        (case (:sort params)
                             "potential" :potential
                             "age"       :age
                             :overall)
              :limit       (limit-arg params 25)})]
    (str (format "Players found: %d" (count ps)) "\n" (q/format-players ps))))

(defn- tool-brazilians-by-club [dataset params]
  (let [rows (q/brazilians-by-club dataset)
        rows (take (limit-arg params 25) rows)]
    (str/join "\n"
      (cons "Brazilian players by club (FIFA dataset):"
            (map (fn [r]
                   (format "  %s — %d players (avg rating %.1f)"
                           (:club r) (:count r) (:avg-rating r)))
                 rows)))))

(defn- tool-average-goals [dataset params]
  (let [opts (cond-> {}
               (:competition params) (assoc :competition (:competition params))
               (:season params)      (assoc :season (->int (:season params))))
        {:keys [matches total-goals avg-goals]} (q/average-goals dataset opts)]
    (format "Matches: %d, total goals: %d, average goals/match: %.2f"
            matches total-goals avg-goals)))

(defn- tool-home-win-rate [dataset params]
  (let [opts (cond-> {}
               (:competition params) (assoc :competition (:competition params))
               (:season params)      (assoc :season (->int (:season params))))
        {:keys [matches home-wins away-wins draws
                home-win-rate away-win-rate draw-rate]} (q/home-win-rate dataset opts)]
    (format (str "Matches: %d\nHome wins: %d (%.1f%%)\n"
                 "Away wins: %d (%.1f%%)\nDraws: %d (%.1f%%)")
            matches
            home-wins (* 100.0 home-win-rate)
            away-wins (* 100.0 away-win-rate)
            draws     (* 100.0 draw-rate))))

(defn- tool-biggest-wins [dataset params]
  (let [opts (cond-> {:limit (limit-arg params 10)}
               (:competition params) (assoc :competition (:competition params))
               (:season params)      (assoc :season (->int (:season params)))
               (:team params)        (assoc :team (:team params)))
        ms   (q/biggest-wins dataset opts)]
    (str "Biggest wins:\n" (q/format-matches ms))))

(defn- tool-dataset-summary [dataset _]
  (let [{:keys [matches players competitions sources]}
        (brazilian-soccer-mcp.data/dataset-summary dataset)]
    (str/join "\n"
      [(str "Matches loaded:      " matches)
       (str "Players loaded:      " players)
       (str "Competitions:        " (str/join ", " competitions))
       (str "Source files:        " (str/join ", " sources))])))

;; ---------------------------------------------------------------------------
;; Registry
;; ---------------------------------------------------------------------------

(def tools
  [{:name        "search_matches"
    :description "Search match data with optional filters: team, home, away, competition, season, season_from, season_to, date_from (YYYY-MM-DD), date_to, stage, round, limit."
    :schema      {:type "object"
                  :properties
                  {:team        {:type "string" :description "team name, matches home or away"}
                   :home        {:type "string"}
                   :away        {:type "string"}
                   :competition {:type "string"}
                   :season      {:type "integer"}
                   :season_from {:type "integer"}
                   :season_to   {:type "integer"}
                   :date_from   {:type "string"}
                   :date_to     {:type "string"}
                   :stage       {:type "string"}
                   :round       {:type "string"}
                   :limit       {:type "integer" :default 50}}}
    :handler     tool-search-matches}

   {:name        "head_to_head"
    :description "Head-to-head match history and aggregate W/D/L between two teams."
    :schema      {:type "object"
                  :required ["team_a" "team_b"]
                  :properties
                  {:team_a {:type "string"}
                   :team_b {:type "string"}
                   :limit  {:type "integer" :default 20}}}
    :handler     tool-head-to-head}

   {:name        "team_stats"
    :description "Aggregate W/D/L, goals-for/against and home/away splits for a team, optionally filtered by season and competition."
    :schema      {:type "object"
                  :required ["team"]
                  :properties
                  {:team        {:type "string"}
                   :season      {:type "integer"}
                   :season_from {:type "integer"}
                   :season_to   {:type "integer"}
                   :competition {:type "string"}}}
    :handler     tool-team-stats}

   {:name        "standings"
    :description "League table for a given season computed from match results. Defaults to Brasileirão."
    :schema      {:type "object"
                  :required ["season"]
                  :properties
                  {:season      {:type "integer"}
                   :competition {:type "string" :default "Brasileirão"}}}
    :handler     tool-standings}

   {:name        "search_players"
    :description "Filter FIFA players by name, nationality, club, position or min_overall. Sort by overall|potential|age."
    :schema      {:type "object"
                  :properties
                  {:name        {:type "string"}
                   :nationality {:type "string"}
                   :club        {:type "string"}
                   :position    {:type "string"}
                   :min_overall {:type "integer"}
                   :sort        {:type "string" :enum ["overall" "potential" "age"]}
                   :limit       {:type "integer" :default 25}}}
    :handler     tool-search-players}

   {:name        "brazilians_by_club"
    :description "Count of Brazilian players per club plus average overall rating."
    :schema      {:type "object" :properties {:limit {:type "integer" :default 25}}}
    :handler     tool-brazilians-by-club}

   {:name        "average_goals"
    :description "Average goals per match across the dataset, with optional season/competition filters."
    :schema      {:type "object"
                  :properties
                  {:competition {:type "string"}
                   :season      {:type "integer"}}}
    :handler     tool-average-goals}

   {:name        "home_win_rate"
    :description "Home vs away win/draw rate across the dataset, with optional filters."
    :schema      {:type "object"
                  :properties
                  {:competition {:type "string"}
                   :season      {:type "integer"}}}
    :handler     tool-home-win-rate}

   {:name        "biggest_wins"
    :description "Top-N matches sorted by goal margin. Optional team/season/competition filters."
    :schema      {:type "object"
                  :properties
                  {:competition {:type "string"}
                   :season      {:type "integer"}
                   :team        {:type "string"}
                   :limit       {:type "integer" :default 10}}}
    :handler     tool-biggest-wins}

   {:name        "dataset_summary"
    :description "High-level diagnostics: how many matches, players, competitions and source files are loaded."
    :schema      {:type "object" :properties {}}
    :handler     tool-dataset-summary}])

(def by-name (into {} (map (juxt :name identity) tools)))

(defn call
  "Invoke a tool by name. Returns the textual result or an error string."
  [dataset tool-name params]
  (if-let [t (get by-name tool-name)]
    (try
      ((:handler t) dataset (or params {}))
      (catch Exception e
        (str "Error executing " tool-name ": " (.getMessage e))))
    (str "Unknown tool: " tool-name)))

(defn descriptors
  "Tool descriptors as returned by MCP `tools/list`."
  []
  (mapv (fn [{:keys [name description schema]}]
          {:name        name
           :description description
           :inputSchema schema})
        tools))
