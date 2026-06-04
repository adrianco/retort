;; =============================================================================
;; soccer.tools — MCP tool definitions and dispatch
;; -----------------------------------------------------------------------------
;; Project: brazilian-soccer-mcp
;;
;; Context:
;;   Declares the catalogue of MCP tools the server exposes (name, description,
;;   JSON input schema) and the dispatch from a tool name + argument map to a
;;   formatted text answer.  Kept transport-agnostic so it can be unit tested
;;   without spinning up the stdio JSON-RPC loop in soccer.mcp.
;;
;;   Each handler receives the database map and an arguments map whose keys are
;;   STRINGS (as they arrive from JSON).  Handlers return a string.
;;
;; Tools:
;;   search_matches | team_record | head_to_head | standings |
;;   competition_stats | biggest_wins | search_players | players_by_club |
;;   list_competitions
;; =============================================================================
(ns soccer.tools
  (:require [clojure.string :as str]
            [soccer.query :as q]
            [soccer.format :as fmt]))

;; --- argument coercion helpers ---------------------------------------------

(defn- arg [args k] (or (get args k) (get args (keyword k))))

(defn- int-arg [args k]
  (let [v (arg args k)]
    (cond (nil? v) nil
          (integer? v) v
          (number? v) (int v)
          (string? v) (try (Integer/parseInt (str/trim v)) (catch Exception _ nil))
          :else nil)))

(defn- str-arg [args k]
  (let [v (arg args k)] (when (and v (not (str/blank? (str v)))) (str v))))

;; --- tool catalogue (advertised via tools/list) -----------------------------

(def tool-specs
  [{:name "search_matches"
    :description
    (str "Search Brazilian soccer matches across Brasileirão, Copa do Brasil "
         "and Copa Libertadores. Filter by team, opponent, competition, season "
         "and date range. Returns a dated list of results, newest first.")
    :inputSchema
    {:type "object"
     :properties
     {"team"        {:type "string" :description "Team plays home OR away"}
      "opponent"    {:type "string" :description "Restrict to matches vs this team"}
      "home"        {:type "string" :description "Team playing at home"}
      "away"        {:type "string" :description "Team playing away"}
      "competition" {:type "string" :description "e.g. 'Copa do Brasil', 'Copa Libertadores', 'Brasileirão Série A'"}
      "season"      {:type "integer" :description "Year, e.g. 2019"}
      "date_from"   {:type "string" :description "Inclusive lower bound (yyyy-MM-dd)"}
      "date_to"     {:type "string" :description "Inclusive upper bound (yyyy-MM-dd)"}
      "limit"       {:type "integer" :description "Max results (default 25)"}}
     :required []}}

   {:name "team_record"
    :description
    (str "Win/draw/loss and goal record for a team, optionally filtered by "
         "season, competition and venue (home/away/all).")
    :inputSchema
    {:type "object"
     :properties
     {"team"        {:type "string"}
      "season"      {:type "integer"}
      "competition" {:type "string"}
      "venue"       {:type "string" :enum ["home" "away" "all"]}}
     :required ["team"]}}

   {:name "head_to_head"
    :description "Aggregate head-to-head record and recent meetings between two teams."
    :inputSchema
    {:type "object"
     :properties
     {"team1"       {:type "string"}
      "team2"       {:type "string"}
      "competition" {:type "string"}
      "season"      {:type "integer"}}
     :required ["team1" "team2"]}}

   {:name "standings"
    :description
    (str "Compute a league table for a competition and season from match "
         "results (3pts win / 1pt draw). Best for round-robin leagues like "
         "the Brasileirão.")
    :inputSchema
    {:type "object"
     :properties
     {"competition" {:type "string" :description "Default 'Brasileirão Série A'"}
      "season"      {:type "integer"}}
     :required ["season"]}}

   {:name "competition_stats"
    :description
    (str "Aggregate statistics for a competition/season (or the whole dataset): "
         "average goals per match, home/away/draw win rates and totals.")
    :inputSchema
    {:type "object"
     :properties
     {"competition" {:type "string"}
      "season"      {:type "integer"}}
     :required []}}

   {:name "biggest_wins"
    :description "List the matches with the largest goal margin (optionally filtered)."
    :inputSchema
    {:type "object"
     :properties
     {"competition" {:type "string"}
      "season"      {:type "integer"}
      "limit"       {:type "integer" :description "Default 10"}}
     :required []}}

   {:name "search_players"
    :description
    (str "Search the FIFA player database by name, nationality, club, position "
         "and minimum overall rating. Sorted by rating (or potential/age).")
    :inputSchema
    {:type "object"
     :properties
     {"name"        {:type "string"}
      "nationality" {:type "string" :description "e.g. 'Brazil'"}
      "club"        {:type "string"}
      "position"    {:type "string" :description "e.g. 'GK', 'LW', 'ST'"}
      "min_overall" {:type "integer"}
      "sort_by"     {:type "string" :enum ["overall" "potential" "age"]}
      "limit"       {:type "integer" :description "Default 25"}}
     :required []}}

   {:name "players_by_club"
    :description
    (str "Summarise players grouped by club (count and average overall), "
         "optionally restricted to a nationality such as 'Brazil'.")
    :inputSchema
    {:type "object"
     :properties
     {"nationality" {:type "string"}
      "limit"       {:type "integer" :description "Default 20 clubs"}}
     :required []}}

   {:name "list_competitions"
    :description "List the competitions and seasons available in the dataset."
    :inputSchema {:type "object" :properties {} :required []}}])

;; --- dispatch ---------------------------------------------------------------

(defn- venue-kw [s]
  (case (some-> s str/lower-case) "home" :home "away" :away :all))

(defn- sort-kw [s]
  (case (some-> s str/lower-case) "potential" :potential "age" :age :overall))

(defn call-tool
  "Execute tool `name` against `db` with string-keyed `args`, returning the
   formatted text answer. Throws ex-info with :type ::unknown-tool for an
   unrecognised name."
  [db name args]
  (case name
    "search_matches"
    (let [ms (q/search-matches db {:team        (str-arg args "team")
                                   :opponent    (str-arg args "opponent")
                                   :home        (str-arg args "home")
                                   :away        (str-arg args "away")
                                   :competition (str-arg args "competition")
                                   :season      (int-arg args "season")
                                   :date-from   (str-arg args "date_from")
                                   :date-to     (str-arg args "date_to")
                                   :limit       (or (int-arg args "limit") 200)})]
      (fmt/format-matches ms :show (or (int-arg args "limit") 25)))

    "team_record"
    (fmt/format-team-stats
     (q/team-stats db (str-arg args "team")
                   {:season      (int-arg args "season")
                    :competition (str-arg args "competition")
                    :venue       (venue-kw (str-arg args "venue"))}))

    "head_to_head"
    (fmt/format-head-to-head
     (q/head-to-head db (str-arg args "team1") (str-arg args "team2")
                     {:competition (str-arg args "competition")
                      :season      (int-arg args "season")}))

    "standings"
    (let [comp (or (str-arg args "competition") "Brasileirão Série A")
          season (int-arg args "season")]
      (fmt/format-standings (q/standings db comp season) comp season))

    "competition_stats"
    (fmt/format-competition-stats
     (q/competition-stats db {:competition (str-arg args "competition")
                              :season      (int-arg args "season")}))

    "biggest_wins"
    (fmt/format-biggest-wins
     (q/biggest-wins db {:competition (str-arg args "competition")
                         :season      (int-arg args "season")
                         :limit       (or (int-arg args "limit") 10)}))

    "search_players"
    (fmt/format-players
     (q/search-players db {:name        (str-arg args "name")
                           :nationality (str-arg args "nationality")
                           :club        (str-arg args "club")
                           :position    (str-arg args "position")
                           :min-overall (int-arg args "min_overall")
                           :sort-field  (sort-kw (str-arg args "sort_by"))
                           :limit       (or (int-arg args "limit") 25)})
     :show (or (int-arg args "limit") 25))

    "players_by_club"
    (let [nat (str-arg args "nationality")]
      (fmt/format-club-summary
       (q/players-by-club-summary db {:nationality nat
                                      :limit (or (int-arg args "limit") 20)})
       :nationality nat))

    "list_competitions"
    (str "Competitions in dataset:\n"
         (str/join "\n" (map #(str "- " %) (q/competitions db)))
         "\n\nSeasons available: "
         (str/join ", " (q/seasons db)))

    (throw (ex-info (str "Unknown tool: " name) {:type ::unknown-tool}))))
