(ns brazil-soccer.tools
  "MCP tool definitions. Each tool has a JSON schema for the model and a handler that
  takes the JSON arguments and returns plain text for the model to read."
  (:require [clojure.string :as str]
            [brazil-soccer.queries :as q]
            [brazil-soccer.teams :as teams]))

;; --- argument helpers -------------------------------------------------------

(defn- kebab
  "Turns JSON argument keys such as :final_only into :final-only."
  [args]
  (update-keys args #(-> % name (str/replace "_" "-") keyword)))

(defn- prop [type description]
  {:type type :description description})

(defn- schema [properties required]
  {:type "object" :properties properties :required (vec required)})

(def ^:private competition-hint
  "Brasileirão Série A/B/C, Copa do Brasil or Libertadores (free-form names are accepted).")

(defn- present
  "Drops nil arguments so that the query functions can apply their defaults."
  [m]
  (into {} (remove (comp nil? val)) m))

;; --- formatting -------------------------------------------------------------

(defn- team-name [key] (teams/display-name key))

(defn- competition-label [m]
  (str (get teams/competition-names (:competition m))
       (cond
         (:round m) (str " Round " (:round m))
         (:stage m) (str ", " (:stage m)))))

(defn- match-line [m]
  (format "%s: %s %d-%d %s (%s)"
          (:date m)
          (team-name (:home m)) (:home-goals m) (:away-goals m)
          (team-name (:away m))
          (competition-label m)))

(defn- record-lines [r]
  [(str "- Matches: " (:played r))
   (str "- Wins: " (:wins r) ", Draws: " (:draws r) ", Losses: " (:losses r))
   (str "- Goals For: " (:goals-for r) ", Goals Against: " (:goals-against r))
   (str "- Win rate: " (:win-rate r) "%")])

(defn- scope-label
  "Describes the filters applied, e.g. \"2022, Copa do Brasil, home games\"."
  [{:keys [season competition venue]}]
  (str/join ", "
            (remove nil?
                    [(some-> season str)
                     (some-> competition teams/competition-of teams/competition-names)
                     (when (and venue (not= venue "any")) (str venue " games"))])))

(defn- text [& lines]
  (str/join "\n" (remove nil? lines)))

(defn- format-player [p]
  (format "%s - Overall: %s, Potential: %s, Position: %s, Club: %s, Nationality: %s, Age: %s"
          (:name p) (:overall p) (:potential p) (:position p)
          (or (:club p) "none") (:nationality p) (:age p)))

;; --- handlers ---------------------------------------------------------------

(defn- find-matches [db args]
  (let [{:keys [team opponent competition season from to venue final-only limit]
         :or {limit 20}} (kebab args)
        ms (q/filter-matches db {:team team :opponent opponent :competition competition
                                 :season season :from from :to to :venue venue
                                 :final-only final-only})
        shown (take limit ms)
        head-to-head (when (and team opponent (seq ms))
                       (let [r (q/record-in team ms)]
                         (format "Head-to-head in these matches: %s %d wins, %s %d wins, %d draws"
                                 (team-name (teams/team-key team)) (:wins r)
                                 (team-name (teams/team-key opponent)) (:losses r)
                                 (:draws r))))]
    (if (empty? ms)
      "No matches found."
      (text (format "%d matches found." (count ms))
            head-to-head
            (str/join "\n" (map match-line shown))
            (when (> (count ms) (count shown))
              (format "... %d more matches in dataset" (- (count ms) (count shown))))))))

(defn- team-record [db args]
  (let [{:keys [team season competition venue]} (kebab args)
        r (q/team-record db {:team team :season season :competition competition :venue venue})
        scope (scope-label {:season season :competition competition :venue venue})]
    (if (zero? (:played r))
      (format "No matches found for %s%s." team
              (if (str/blank? scope) "" (str " (" scope ")")))
      (text (format "%s%s:" (team-name (:team r)) (if (str/blank? scope) "" (str " (" scope ")")))
            (str/join "\n" (record-lines r))
            (format "- Points: %d" (:points r))))))

(defn- head-to-head [db args]
  (let [{:keys [team-a team-b competition]} (kebab args)
        {:keys [record matches]} (q/head-to-head db {:team-a team-a :team-b team-b
                                                     :competition competition})]
    (if (zero? (:played record))
      (format "No matches found between %s and %s." (team-name (teams/team-key team-a))
              (team-name (teams/team-key team-b)))
      (text (format "Head-to-head in dataset: %s %d wins, %s %d wins, %d draws"
                    (team-name (teams/team-key team-a)) (:wins record)
                    (team-name (teams/team-key team-b)) (:losses record) (:draws record))
            (format "Goals: %d-%d over %d matches" (:goals-for record) (:goals-against record)
                    (:played record))
            (str/join "\n" (map match-line (take 10 matches)))
            (when (> (count matches) 10)
              (format "... %d more matches in dataset" (- (count matches) 10)))))))

(defn- standings [db args]
  (let [{:keys [competition season]} (kebab args)
        rows (q/standings db {:competition competition :season season})]
    (if (empty? rows)
      "No matches found for that season."
      (text (format "%s %s standings (calculated from match results):"
                    season (get teams/competition-names (teams/competition-of competition)))
            (str/join "\n"
                      (map (fn [{:keys [position team points wins draws losses goal-difference]}]
                             (format "%d. %s - %d pts (%dW, %dD, %dL, GD %+d)%s"
                                     position (team-name team) points wins draws losses
                                     goal-difference (if (= position 1) " - Champion" "")))
                           rows))))))

(defn- team-rankings [db args]
  (let [{:keys [competition season venue sort-by min-matches limit]} (kebab args)
        rows (q/team-rankings db (present {:competition competition :season season :venue venue
                                                 :sort-by sort-by :min-matches min-matches
                                                 :limit limit}))]
    (if (empty? rows)
      "No teams matched those filters."
      (str/join "\n"
                (map-indexed
                 (fn [i r]
                   (format "%d. %s - %d played, %dW %dD %dL, GF %d, GA %d, win rate %s%%, %d pts"
                           (inc i) (team-name (:team r)) (:played r) (:wins r) (:draws r)
                           (:losses r) (:goals-for r) (:goals-against r) (:win-rate r)
                           (:points r)))
                 rows)))))

(defn- league-summary [db args]
  (let [{:keys [competition season top]} (kebab args)
        s (q/league-summary db (present {:competition competition :season season :top top}))]
    (if (zero? (:matches s))
      "No matches found for that competition and season."
      (text (format "%d matches, %d goals" (:matches s) (:goals s))
            (format "Average goals per match: %.2f" (double (:goals-per-match s)))
            (format "Home win rate: %s%%, draw rate: %s%%, away win rate: %s%%"
                    (:home-win-rate s) (:draw-rate s) (:away-win-rate s))
            "Biggest wins:"
            (str/join "\n" (map (fn [m] (str "- " (match-line m))) (:biggest-wins s)))
            "Highest scoring:"
            (str/join "\n" (map (fn [m] (str "- " (match-line m))) (:highest-scoring s)))))))

(defn- search-players [db args]
  (let [{:keys [name nationality club position-group min-overall sort-by limit]} (kebab args)
        {:keys [total players]} (q/search-players db (present {:name name :nationality nationality
                                                     :club club :position-group position-group
                                                     :min-overall min-overall :sort-by sort-by
                                                     :limit limit}))]
    (if (zero? total)
      "No players matched."
      (text (format "%d players matched (showing %d)." total (count players))
            (str/join "\n" (map format-player players))))))

(defn- brazilian-players-by-club [db args]
  (let [{:keys [limit]} (kebab args)
        rows (q/brazilian-players-by-club db (present {:limit limit}))]
    (str/join "\n"
              (map (fn [{:keys [club players average-overall]}]
                     (format "%s: %d players (avg overall %.1f)"
                             (team-name club) players (double average-overall)))
                   rows))))

(defn- team-profile [db args]
  (let [{:keys [team]} (kebab args)
        p (q/team-profile db {:team team})]
    (text (format "%s - dataset profile:" (team-name (:team p)))
          "Match record (all competitions):"
          (str/join "\n" (record-lines (:record p)))
          "By competition:"
          (str/join "\n" (map (fn [r]
                                (format "- %s: %d played, %dW %dD %dL"
                                        (get teams/competition-names (:competition r))
                                        (:played r) (:wins r) (:draws r) (:losses r)))
                              (:by-competition p)))
          (format "FIFA squad: %d players%s" (:squad-size p)
                  (if (:squad-average-overall p)
                    (format " (avg overall %.1f)" (double (:squad-average-overall p)))
                    ""))
          (when (seq (:top-players p))
            (str/join "\n" (map format-player (:top-players p)))))))

;; --- tool registry ----------------------------------------------------------

(defn tools
  "All MCP tools backed by the given database map."
  [db]
  [{:name "find_matches"
    :description (str "Find matches by team (home, away or either), opponent, competition, season, "
                      "date range or final-only. Lists the most recent matches with scores. "
                      "Use for 'show me all Flamengo vs Fluminense matches' or 'Copa do Brasil finals'.")
    :inputSchema (schema {:team (prop "string" "Team name, e.g. Flamengo or Palmeiras-SP")
                          :opponent (prop "string" "Second team; when given with team, only their meetings are returned")
                          :competition (prop "string" competition-hint)
                          :season (prop "integer" "Season year, e.g. 2023")
                          :from (prop "string" "Earliest date, YYYY-MM-DD or DD/MM/YYYY")
                          :to (prop "string" "Latest date, YYYY-MM-DD or DD/MM/YYYY")
                          :venue (prop "string" "home, away or any (relative to team); default any")
                          :final_only (prop "boolean" "Only finals (Libertadores final stage, or highest Copa do Brasil round of a season)")
                          :limit (prop "integer" "Maximum matches to list; default 20")}
                         [])
    :handler (partial find-matches db)}

   {:name "team_record"
    :description "Win/draw/loss record, goals and win rate for one team, optionally by season, competition and venue."
    :inputSchema (schema {:team (prop "string" "Team name")
                          :season (prop "integer" "Season year")
                          :competition (prop "string" competition-hint)
                          :venue (prop "string" "home, away or any; default any")}
                         [:team])
    :handler (partial team-record db)}

   {:name "head_to_head"
    :description "Head-to-head record between two teams across all matches in the dataset, with the most recent meetings."
    :inputSchema (schema {:team_a (prop "string" "First team")
                          :team_b (prop "string" "Second team")
                          :competition (prop "string" competition-hint)}
                         [:team_a :team_b])
    :handler (partial head-to-head db)}

   {:name "competition_standings"
    :description "League table for a Brasileirão season (Serie A, B or C), calculated from match results with 3 points for a win and 1 for a draw."
    :inputSchema (schema {:competition (prop "string" "Serie A, Serie B or Serie C")
                          :season (prop "integer" "Season year, e.g. 2019")}
                         [:competition :season])
    :handler (partial standings db)}

   {:name "team_rankings"
    :description "Rank teams in a competition or season by points, wins, win rate, goals for or goal difference. Use for 'which team has the best home record' or 'who scored the most goals'."
    :inputSchema (schema {:competition (prop "string" competition-hint)
                          :season (prop "integer" "Season year")
                          :venue (prop "string" "home, away or any; default any")
                          :sort_by (prop "string" "points, wins, win_rate, goals_for or goal_difference; default points")
                          :min_matches (prop "integer" "Ignore teams with fewer matches; default 1")
                          :limit (prop "integer" "How many teams to return; default 10")}
                         [])
    :handler (partial team-rankings db)}

   {:name "league_summary"
    :description "Aggregate statistics for a competition and season: average goals per match, home/draw/away rates, biggest wins and highest-scoring games."
    :inputSchema (schema {:competition (prop "string" competition-hint)
                          :season (prop "integer" "Season year")
                          :top (prop "integer" "How many biggest wins and highest-scoring games to list; default 5")}
                         [:competition])
    :handler (partial league-summary db)}

   {:name "search_players"
    :description "Search the FIFA player database by name, nationality, club, position group and minimum overall rating."
    :inputSchema (schema {:name (prop "string" "Part of the player's name, e.g. Gabriel Barbosa")
                          :nationality (prop "string" "Nationality, e.g. Brazil")
                          :club (prop "string" "Club name, e.g. Flamengo")
                          :position_group (prop "string" "goalkeeper, defender, midfielder or forward")
                          :min_overall (prop "integer" "Minimum overall rating")
                          :sort_by (prop "string" "overall or potential; default overall")
                          :limit (prop "integer" "Maximum players to return; default 10")}
                         [])
    :handler (partial search-players db)}

   {:name "brazilian_players_by_club"
    :description "Count and average overall rating of Brazilian-national players at each Brazilian club in the FIFA data."
    :inputSchema (schema {:limit (prop "integer" "How many clubs to return; default 20")} [])
    :handler (partial brazilian-players-by-club db)}

   {:name "team_profile"
    :description "Cross-dataset profile of one team: match record per competition plus its FIFA squad size, average rating and top players."
    :inputSchema (schema {:team (prop "string" "Team or club name")} [:team])
    :handler (partial team-profile db)}])
