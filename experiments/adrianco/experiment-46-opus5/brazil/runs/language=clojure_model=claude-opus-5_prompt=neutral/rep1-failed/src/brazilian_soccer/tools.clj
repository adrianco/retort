(ns brazilian-soccer.tools
  "The MCP tool catalogue: JSON schema + handler for every capability.

  CONTEXT
  -------
  This is the contract between the LLM and the knowledge graph.  Each entry has

      :name        the tool name the model calls
      :description what the tool answers, with example questions so the model
                   can pick the right one
      :schema      JSON Schema for the arguments (string keys - it is serialised
                   straight into the tools/list response)
      :handler     (fn [db args] -> text)

  Handlers take already-parsed arguments, run `brazilian-soccer.query` and
  render with `brazilian-soccer.format`.  A handler that cannot answer throws
  ex-info; `brazilian-soccer.mcp` turns that into an MCP tool error containing
  the message, which is usually a helpful \"did you mean\" list.

  The five capability groups required by the specification map onto the tools
  like this:
      match queries        search_matches, find_derbies, list_finals
      team queries         team_stats, team_profile, head_to_head
      player queries       search_players, player_profile, club_squad
      competition queries  standings, competition_stats
      statistical analysis competition_stats, biggest_wins, team_stats"
  (:require [clojure.string :as str]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.format :as fmt]
            [brazilian-soccer.query :as q]))

;; ---------------------------------------------------------------------------
;; Argument helpers
;; ---------------------------------------------------------------------------

(defn- arg [args k]
  (let [v (get args k (get args (name k)))]
    (when-not (or (nil? v) (and (string? v) (str/blank? v))) v)))

(defn- ->long [v]
  (cond (nil? v) nil
        (number? v) (long v)
        :else (try (Long/parseLong (str/trim (str v)))
                   (catch Exception _
                     (throw (ex-info (str "Expected a number, got \"" v "\"") {:value v}))))))

(defn- int-arg [args k] (->long (arg args k)))

(defn- competition-arg [args]
  (when-let [v (arg args :competition)]
    (or (data/competition-key v)
        (throw (ex-info (str "Unknown competition \"" v "\". Known competitions: "
                             (str/join ", " (map :name (vals data/competitions))))
                        {:type :unknown-competition})))))

(defn- venue-arg [args]
  (when-let [v (arg args :venue)]
    (let [k (keyword (str/lower-case (str v)))]
      (if (#{:home :away :any} k)
        k
        (throw (ex-info (str "venue must be home, away or any (got \"" v "\")") {}))))))

(defn- date-arg [args k]
  (when-let [v (arg args k)]
    (let [s (str/trim (str v))]
      (if (re-matches #"\d{4}-\d{2}-\d{2}" s)
        s
        (throw (ex-info (str k " must be an ISO date such as 2019-10-27 (got \"" v "\")") {}))))))

(defn- match-filters [db args]
  (cond-> {:competition (competition-arg args)
           :season      (int-arg args :season)
           :season-from (int-arg args :season_from)
           :season-to   (int-arg args :season_to)
           :date-from   (date-arg args :date_from)
           :date-to     (date-arg args :date_to)
           :venue       (venue-arg args)
           :round       (int-arg args :round)
           :stage       (arg args :stage)}
    (arg args :team)     (assoc :team-id (q/team-id! db (arg args :team)))
    (arg args :opponent) (assoc :opponent-id (q/team-id! db (arg args :opponent)))))

;; ---------------------------------------------------------------------------
;; Schema fragments
;; ---------------------------------------------------------------------------

(def ^:private team-prop
  {"type" "string"
   "description" "Club name in any spelling used by the data, e.g. \"Flamengo\", \"Sao Paulo\", \"Atletico-MG\", \"Athletico Paranaense\"."})

(def ^:private competition-prop
  {"type" "string"
   "description" "One of: Brasileirão Série A, Série B, Série C, Copa do Brasil, Copa Libertadores. Aliases such as \"brasileirao\" or \"libertadores\" are accepted."})

(def ^:private season-prop {"type" "integer" "description" "Season year, e.g. 2019."})
(def ^:private limit-prop  {"type" "integer" "description" "Maximum rows to return (default 20)."})

(defn- object [props & [required]]
  (cond-> {"type" "object" "properties" props}
    (seq required) (assoc "required" (vec required))))

;; ---------------------------------------------------------------------------
;; Tools
;; ---------------------------------------------------------------------------

(def tools
  [{:name "search_matches"
    :description (str "Find matches by team, opponent, competition, season, round, stage or date "
                      "range. Answers questions such as \"Show me all Flamengo vs Fluminense "
                      "matches\", \"What matches did Palmeiras play in 2023?\" or \"When did "
                      "Flamengo last play Corinthians?\" (use limit 1 for the latest).")
    :schema (object {"team" team-prop
                     "opponent" team-prop
                     "competition" competition-prop
                     "season" season-prop
                     "season_from" {"type" "integer" "description" "Earliest season (inclusive)."}
                     "season_to" {"type" "integer" "description" "Latest season (inclusive)."}
                     "date_from" {"type" "string" "description" "Earliest match date, ISO format YYYY-MM-DD."}
                     "date_to" {"type" "string" "description" "Latest match date, ISO format YYYY-MM-DD."}
                     "venue" {"type" "string" "enum" ["home" "away" "any"]
                              "description" "Restrict to home or away matches of `team`."}
                     "round" {"type" "integer" "description" "League round or cup round number."}
                     "stage" {"type" "string" "description" "Libertadores stage: group stage, round of 16, quarterfinals, semifinals, final."}
                     "order" {"type" "string" "enum" ["newest" "oldest"] "description" "Sort order, default newest first."}
                     "limit" limit-prop})
    :handler
    (fn [db args]
      (let [filters (match-filters db args)
            order   (if (= "oldest" (arg args :order)) :date-asc :date-desc)
            all     (q/find-matches db (assoc filters :sort order))
            limit   (or (int-arg args :limit) 20)
            shown   (vec (take limit all))
            team    (when (:team-id filters) (q/team db (:team-id filters)))
            opp     (when (:opponent-id filters) (q/team db (:opponent-id filters)))]
        (fmt/matches-answer
         {:title (str "Matches"
                      (when team (str " for " (:display team)))
                      (when opp (str " against " (:display opp))))
          :filters (fmt/filters-line filters)
          :matches shown
          :total (count all)})))}

   {:name "head_to_head"
    :description (str "Complete head-to-head record between two clubs: wins for each side, draws, "
                      "goals, first and last meeting, breakdown by competition and the match list. "
                      "Answers \"Compare Palmeiras and Santos head-to-head\".")
    :schema (object {"team_a" team-prop "team_b" team-prop
                     "competition" competition-prop
                     "season" season-prop
                     "limit" limit-prop}
                    ["team_a" "team_b"])
    :handler
    (fn [db args]
      (let [a (q/team-id! db (or (arg args :team_a) (throw (ex-info "team_a is required" {}))))
            b (q/team-id! db (or (arg args :team_b) (throw (ex-info "team_b is required" {}))))
            filters {:competition (competition-arg args) :season (int-arg args :season)}]
        (fmt/head-to-head-answer (q/head-to-head db a b filters)
                                 {:limit (or (int-arg args :limit) 20)
                                  :filters (fmt/filters-line filters)})))}

   {:name "team_stats"
    :description (str "Win/draw/loss record, goals for and against, home and away splits and "
                      "per-season breakdown for one club, optionally filtered by competition, "
                      "season or date range. Answers \"What is Corinthians' home record in 2022?\".")
    :schema (object {"team" team-prop
                     "competition" competition-prop
                     "season" season-prop
                     "season_from" {"type" "integer"} "season_to" {"type" "integer"}
                     "date_from" {"type" "string"} "date_to" {"type" "string"}
                     "venue" {"type" "string" "enum" ["home" "away" "any"]}}
                    ["team"])
    :handler
    (fn [db args]
      (let [filters (match-filters db args)
            id (or (:team-id filters) (throw (ex-info "team is required" {})))]
        (fmt/team-stats-answer
         (assoc (q/team-summary db id filters)
                :filters (fmt/filters-line filters)))))}

   {:name "team_profile"
    :description (str "Overview of a club: which competitions and seasons it appears in, its "
                      "overall record, every spelling of its name in the data and its most recent "
                      "matches. Answers \"What competitions has Palmeiras played in?\".")
    :schema (object {"team" team-prop} ["team"])
    :handler
    (fn [db args]
      (let [id (q/team-id! db (or (arg args :team) (throw (ex-info "team is required" {}))))
            t  (q/team db id)
            summary (q/team-summary db id {})
            seasons (map first (:by-season summary))]
        (str (:display t) (when (:state t) (str " (" (:state t) ")")) "\n"
             "Canonical id: " (:id t) "\n"
             "Spellings in the data: " (str/join " / " (:variants t)) "\n"
             "Seasons: " (when (seq seasons) (str (apply min seasons) "-" (apply max seasons)))
             " (" (count seasons) " seasons)\n"
             "Overall record: " (fmt/record-line (:overall summary)) "\n\n"
             "Competitions:\n"
             (str/join "\n" (for [[c r] (:by-competition summary)]
                              (str "  - " (data/competition-name c) ": " (:matches r) " matches, "
                                   (:wins r) "W " (:draws r) "D " (:losses r) "L, seasons "
                                   (let [ss (map :season (q/find-matches db {:team-id id :competition c}))]
                                     (str (apply min ss) "-" (apply max ss))))))
             "\n\nMost recent matches:\n"
             (fmt/match-list (:recent summary) nil))))}

   {:name "standings"
    :description (str "League table for a season, calculated from the match results in the data "
                      "(3 points per win). Answers \"Who won the 2019 Brasileirão?\" and "
                      "\"Which teams were relegated in 2020?\".")
    :schema (object {"competition" competition-prop "season" season-prop} ["season"])
    :handler
    (fn [db args]
      (let [competition (or (competition-arg args) :serie-a)
            season (or (int-arg args :season) (throw (ex-info "season is required" {})))]
        (when-not (q/league? competition)
          (throw (ex-info (str (data/competition-name competition)
                               " is a knockout competition - use list_finals or search_matches with a stage.")
                          {})))
        (let [s (q/standings db competition season)]
          (when (zero? (:match-count s))
            (throw (ex-info (str "No " (data/competition-name competition) " matches for season "
                                 season " in the dataset. Available seasons: "
                                 (str/join ", " (q/seasons db competition)))
                            {})))
          (fmt/standings-answer s))))}

   {:name "competition_stats"
    :description (str "Aggregate statistics for a competition and optionally one season: matches, "
                      "goals per match, home/away/draw rates, biggest margin, highest scoring game "
                      "and top scoring teams. Answers \"What's the average goals per match in the "
                      "Brasileirão?\" and \"Compare the 2018 and 2019 seasons\" (call twice).")
    :schema (object {"competition" competition-prop "season" season-prop})
    :handler
    (fn [db args]
      (fmt/competition-summary-answer
       (q/competition-summary db (competition-arg args) (int-arg args :season))))}

   {:name "biggest_wins"
    :description (str "Matches with the largest goal margin, optionally restricted to a team, "
                      "competition or season. Answers \"Show me the biggest wins in the dataset\".")
    :schema (object {"team" team-prop "competition" competition-prop "season" season-prop
                     "limit" limit-prop})
    :handler
    (fn [db args]
      (let [filters (match-filters db args)
            limit (or (int-arg args :limit) 10)
            ms (q/biggest-wins db (assoc filters :limit limit))]
        (fmt/matches-answer {:title (if-let [t (:team-id filters)]
                                      (str "Biggest wins for " (:display (q/team db t)))
                                      "Biggest margins of victory")
                             :filters (fmt/filters-line filters)
                             :matches ms})))}

   {:name "team_rankings"
    :description (str "Rank clubs by a metric over any slice of the data: points per match, win "
                      "rate, goals scored, goal difference. Combine with venue=home or away for "
                      "\"Which team has the best home record?\" / \"best away record?\", or with "
                      "metric=goals_for and a season for \"Which team scored the most goals in "
                      "Serie A 2023?\".")
    :schema (object {"metric" {"type" "string"
                               "enum" ["points_per_match" "win_rate" "points" "wins"
                                       "goals_for" "goals_per_match" "goal_difference" "matches"]
                               "description" "Ranking metric, default points_per_match."}
                     "venue" {"type" "string" "enum" ["home" "away" "any"]}
                     "competition" competition-prop
                     "season" season-prop
                     "season_from" {"type" "integer"} "season_to" {"type" "integer"}
                     "min_matches" {"type" "integer" "description" "Ignore clubs with fewer matches (default 20)."}
                     "limit" limit-prop})
    :handler
    (fn [db args]
      (let [filters (match-filters db args)
            metric (keyword (str/replace (or (arg args :metric) "points_per_match") "_" "-"))
            opts (-> filters
                     (dissoc :team-id :opponent-id :round :stage)
                     (assoc :metric metric
                            :venue (or (venue-arg args) :any)
                            :min-matches (int-arg args :min_matches)
                            :limit (or (int-arg args :limit) 10)))]
        (when-not (q/ranking-metrics metric)
          (throw (ex-info (str "Unknown metric \"" (arg args :metric) "\". Use one of: "
                               (str/join ", " (map #(str/replace (name %) "-" "_")
                                                   (keys q/ranking-metrics))))
                          {})))
        (fmt/rankings-answer (q/team-rankings db opts)
                             (fmt/filters-line (dissoc filters :venue)))))}

   {:name "list_finals"
    :description (str "Finals of a knockout competition: Copa do Brasil (the last round of each "
                      "season) or Copa Libertadores (matches tagged \"final\"). Answers "
                      "\"Find all Copa do Brasil finals\".")
    :schema (object {"competition" competition-prop "season" season-prop})
    :handler
    (fn [db args]
      (let [competition (or (competition-arg args) :copa-do-brasil)
            season (int-arg args :season)
            _ (when (q/league? competition)
                (throw (ex-info (str (data/competition-name competition)
                                     " is a league - use standings to see who finished first.")
                                {})))
            {:keys [finals incomplete-seasons]} (q/finals db competition season)]
        (str (fmt/matches-answer {:title (str (data/competition-name competition) " finals")
                                  :filters (fmt/filters-line {:competition competition :season season})
                                  :matches finals})
             (when (seq incomplete-seasons)
               (str "\nThe final cannot be identified for these seasons because the data stops"
                    " before the last round or carries no round numbers: "
                    (str/join ", " incomplete-seasons) ".")))))}

   {:name "find_derbies"
    :description (str "Matches between traditional rivals (Fla-Flu, Derby Paulista, Gre-Nal, "
                      "Clássico Mineiro, Atletiba, Ba-Vi, Clássico-Rei, Re-Pa and more), "
                      "optionally by season or competition. Answers \"Show me all derbies in 2023\".")
    :schema (object {"season" season-prop "competition" competition-prop
                     "team" team-prop "limit" limit-prop})
    :handler
    (fn [db args]
      (let [filters (match-filters db args)
            limit (or (int-arg args :limit) 50)
            ms (q/derbies db (assoc filters :limit limit))]
        (str "Derby matches (" (fmt/filters-line filters) ")\n"
             (fmt/match-list ms nil)
             "\n\n" (count ms) " derbies shown. Rivalries tracked: "
             (str/join ", " (map :name q/rivalries)))))}

   {:name "search_players"
    :description (str "Search the FIFA 19 player database by name, nationality, club, position or "
                      "rating. Answers \"Find all Brazilian players in the dataset\", \"Who are "
                      "the highest-rated players at Fluminense?\" and \"Show me all forwards from "
                      "Santos\".")
    :schema (object {"name" {"type" "string" "description" "Full or partial player name (accent insensitive)."}
                     "nationality" {"type" "string" "description" "Exact nationality, e.g. \"Brazil\"."}
                     "club" {"type" "string" "description" "Club name as it appears in the FIFA data, e.g. \"Fluminense\"."}
                     "position" {"type" "string" "description" "Exact FIFA position code, e.g. ST, CAM, GK."}
                     "position_group" {"type" "string" "enum" ["goalkeeper" "defender" "midfielder" "forward"]}
                     "min_overall" {"type" "integer" "description" "Minimum FIFA overall rating."}
                     "max_age" {"type" "integer"}
                     "min_age" {"type" "integer"}
                     "sort" {"type" "string" "enum" ["overall" "potential" "age" "name"]}
                     "limit" limit-prop})
    :handler
    (fn [db args]
      (let [opts {:name (arg args :name)
                  :nationality (arg args :nationality)
                  :club (arg args :club)
                  :position (arg args :position)
                  :position-group (arg args :position_group)
                  :min-overall (int-arg args :min_overall)
                  :min-age (int-arg args :min_age)
                  :max-age (int-arg args :max_age)
                  :sort (keyword (or (arg args :sort) "overall"))
                  :limit (or (int-arg args :limit) 20)}
            {:keys [total players]} (q/search-players db opts)]
        (fmt/players-answer
         {:title (str "FIFA 19 players"
                      (when (:name opts) (str " matching \"" (:name opts) "\""))
                      (when (:nationality opts) (str " from " (:nationality opts)))
                      (when (:club opts) (str " at " (:club opts)))
                      (when (:position opts) (str " playing " (:position opts)))
                      (when (:position-group opts) (str " (" (:position-group opts) "s)")))
          :players players
          :total total
          :note (when (and (:club opts) (zero? total))
                  (str "No club in the FIFA 19 snapshot matches \"" (:club opts)
                       "\". That snapshot only licenses these Brazilian clubs: "
                       (str/join ", " (sort (keys (:club->team-id db))))
                       "."))})))}

   {:name "player_profile"
    :description (str "Full FIFA 19 profile for one player: ratings, physical data, contract and "
                      "top attributes, plus the link to the club's matches when that club is in "
                      "the match data. Answers \"Who is Gabriel Barbosa?\".")
    :schema (object {"name" {"type" "string" "description" "Player name or part of it."}} ["name"])
    :handler
    (fn [db args]
      (let [n (or (arg args :name) (throw (ex-info "name is required" {})))
            profile (q/player-profile db n)]
        (when-not profile
          (throw (ex-info (str "No player matching \"" n "\" in the FIFA 19 dataset.") {})))
        (str (fmt/player-profile-answer profile (q/team db (:team-id profile)))
             (when-let [tid (:team-id profile)]
               (let [s (q/team-summary db tid {})]
                 (str "\n\nClub in the match data - " (:display (q/team db tid)) ": "
                      (fmt/record-line (:overall s))))))))}

   {:name "club_squad"
    :description (str "FIFA 19 squad for a club, with size, average rating, nationalities and the "
                      "players sorted by rating. Called without a club it lists every Brazilian "
                      "club squad in the snapshot with player counts and average ratings.")
    :schema (object {"club" {"type" "string" "description" "Club name, e.g. \"Cruzeiro\" or \"Sport Club do Recife\"."}})
    :handler
    (fn [db args]
      (if-let [club (arg args :club)]
        (if-let [squad (q/club-squad db club)]
          (str (fmt/squad-answer squad (q/team db (:team-id squad)))
               (when (:team-id squad)
                 (str "\n\nNote: FIFA 19 does not license the Brazilian league, so this squad "
                      "carries EA's generated placeholder names; the ratings describe the squad, "
                      "the names are not the real players.")))
          (throw (ex-info (str "No club matching \"" club "\" in the FIFA 19 snapshot. "
                               "Brazilian clubs it does contain: "
                               (str/join ", " (sort (keys (:club->team-id db)))) ".")
                          {})))
        (let [squads (q/brazilian-club-squads db)]
          (str "Brazilian club squads in the FIFA 19 snapshot ("
               (count squads) " clubs linked to the match data)\n"
               (str/join "\n"
                         (for [s squads]
                           (str "  - " (:club s) " -> " (:team s) ": " (:players s) " players"
                                " (" (:brazilians s) " Brazilian), avg rating "
                                (fmt/dec2 (:avg-overall s))
                                "; best: " (str/join ", " (map #(str (:name %) " " (:overall %))
                                                               (:top s))))))
               "\n\nNote: the FIFA 19 snapshot only licenses the clubs listed above, so "
               "Flamengo, Palmeiras, Corinthians and São Paulo have no players in it, and the "
               "squads it does contain use EA's generated placeholder names - the ratings are "
               "usable, the individual identities are not. Brazilian internationals appear under "
               "their real names at the European clubs they played for (search_players with "
               "nationality=Brazil)."))))}

   {:name "list_teams"
    :description (str "List or search the clubs in the match data, showing the canonical id, "
                      "every spelling used by the CSV files, the number of matches and the "
                      "competitions each club appears in.")
    :schema (object {"query" {"type" "string" "description" "Optional name fragment, e.g. \"atletico\"."}
                     "limit" limit-prop})
    :handler
    (fn [db args]
      (let [ts (q/search-teams db (arg args :query))
            limit (or (int-arg args :limit) 25)]
        (str (fmt/teams-answer (take limit ts))
             "\n\n" (min limit (count ts)) " of " (count ts) " matching clubs.")))}

   {:name "dataset_info"
    :description (str "What data is loaded: files, licenses, row counts, competitions, season "
                      "coverage and how overlapping files were merged. Use it to check what can "
                      "be answered before answering.")
    :schema (object {})
    :handler (fn [db _] (fmt/dataset-answer (q/dataset-info db)))}])

(def tools-by-name (into {} (map (juxt :name identity) tools)))

(defn tool-list-json
  "The payload of an MCP tools/list response."
  []
  (mapv (fn [t] {"name" (:name t)
                 "description" (:description t)
                 "inputSchema" (:schema t)})
        tools))

(defn call-tool
  "Run a tool by name.  Returns text; throws ex-info for unknown tools."
  [db tool-name args]
  (if-let [t (tools-by-name tool-name)]
    ((:handler t) db (or args {}))
    (throw (ex-info (str "Unknown tool \"" tool-name "\". Available: "
                         (str/join ", " (map :name tools)))
                    {:type :unknown-tool}))))
