(ns brazilian-soccer.tools
  "MCP tool registry: tool descriptors (name, description, JSON Schema)
  plus handlers that turn query results into readable text responses."
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.query :as query]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; Argument coercion (MCP arguments arrive as JSON with string keys)

(defn- arg-str [args k]
  (let [v (get args k)]
    (when (and v (not (str/blank? (str v)))) (str/trim (str v)))))

(defn- arg-int [args k]
  (let [v (get args k)]
    (cond
      (number? v) (long v)
      (string? v) (data/parse-num v)
      :else nil)))

;; ---------------------------------------------------------------------------
;; Formatting

(defn- fmt-pct [num den]
  (if (pos? den) (format "%.1f%%" (* 100.0 (/ (double num) den))) "n/a"))

(defn format-match [{:keys [date home away home-goals away-goals competition round stage]}]
  (str "- " (or date "????-??-??") ": "
       home " " (or home-goals "?") "-" (or away-goals "?") " " away
       " (" competition
       (when round (str ", Round " round))
       (when stage (str ", " stage))
       ")"))

(defn format-matches [matches limit]
  (let [n (count matches)
        shown (take limit matches)]
    (if (zero? n)
      "No matches found."
      (str "Found " n " match" (when (not= 1 n) "es") ":\n"
           (str/join "\n" (map format-match shown))
           (when (> n limit)
             (str "\n... (" (- n limit) " more; raise the limit parameter to see them)"))))))

(defn- format-stats-block [{:keys [matches wins draws losses goals-for goals-against]}]
  (str "- Matches: " matches "\n"
       "- Wins: " wins ", Draws: " draws ", Losses: " losses "\n"
       "- Goals For: " goals-for ", Goals Against: " goals-against "\n"
       "- Win rate: " (fmt-pct wins matches)))

(defn- format-player-line [idx {:keys [name overall position club nationality]}]
  (str (inc idx) ". " name " - Overall: " overall
       ", Position: " (or position "?")
       ", Club: " (or club "Free agent")
       ", Nationality: " nationality))

;; ---------------------------------------------------------------------------
;; Tool handlers

(defn- search-matches-handler [args]
  (let [team     (or (arg-str args "team") (arg-str args "opponent"))
        opponent (when (arg-str args "team") (arg-str args "opponent"))
        limit    (or (arg-int args "limit") 20)
        matches  (query/find-matches {:team team
                                      :opponent opponent
                                      :competition (arg-str args "competition")
                                      :season (arg-int args "season")
                                      :date-from (arg-str args "date_from")
                                      :date-to (arg-str args "date_to")
                                      :stage (arg-str args "stage")})]
    (format-matches matches limit)))

(defn- head-to-head-handler [args]
  (let [team1 (arg-str args "team1")
        team2 (arg-str args "team2")]
    (if-not (and team1 team2)
      "Both team1 and team2 are required."
      (let [{:keys [matches team1-wins team2-wins draws]}
            (query/head-to-head team1 team2 {:competition (arg-str args "competition")
                                             :season (arg-int args "season")})
            c1 (data/canonical-team team1)
            c2 (data/canonical-team team2)]
        (if (empty? matches)
          (str "No matches found between " c1 " and " c2 ".")
          (str c1 " vs " c2 " head-to-head:\n"
               (str/join "\n" (map format-match (take 15 matches)))
               (when (> (count matches) 15)
                 (str "\n... (" (- (count matches) 15) " more matches in dataset)"))
               "\n\nHead-to-head record: " c1 " " team1-wins " wins, "
               c2 " " team2-wins " wins, " draws " draws"))))))

(defn- team-stats-handler [args]
  (if-let [team (arg-str args "team")]
    (let [season (arg-int args "season")
          competition (arg-str args "competition")
          venue (some-> (arg-str args "venue") str/lower-case)
          stats (query/team-stats team {:season season
                                        :competition competition
                                        :venue venue})
          c (data/canonical-team team)]
      (if (zero? (:matches stats))
        (str "No matches found for " c
             (when season (str " in season " season)) ".")
        (str c
             (case venue "home" " home" "away" " away" "")
             " record"
             (when season (str " (" season
                               (when competition (str " " (query/competition-key competition)))
                               ")"))
             ":\n" (format-stats-block stats))))
    "The team parameter is required."))

(defn- standings-handler [args]
  (if-let [season (arg-int args "season")]
    (let [{:keys [competition rows]} (query/standings
                                      {:season season
                                       :competition (arg-str args "competition")})]
      (if (empty? rows)
        (str "No match data for " competition " season " season ".")
        (str season " " competition " standings (calculated from match results):\n"
             (str/join "\n"
                       (map (fn [{:keys [position team points wins draws losses gf ga goal-diff]}]
                              (format "%2d. %s - %d pts (%dW %dD %dL, GF %d, GA %d, GD %+d)%s"
                                      position team points wins draws losses gf ga goal-diff
                                      (if (= 1 position) " - Champion" "")))
                            rows))
             "\n\nNote: standings are computed from the matches in the dataset;"
             " historical point deductions are not reflected.")))
    "The season parameter is required (e.g. 2019)."))

(defn- search-players-handler [args]
  (let [limit (or (arg-int args "limit") 20)
        players (query/search-players {:name (arg-str args "name")
                                       :nationality (arg-str args "nationality")
                                       :club (arg-str args "club")
                                       :position (arg-str args "position")
                                       :min-overall (arg-int args "min_overall")
                                       :limit limit})]
    (if (empty? players)
      "No players found. Note: the FIFA dataset is from FIFA 19 and does not include every Brazilian club."
      (str "Found players (sorted by overall rating):\n"
           (str/join "\n" (map-indexed format-player-line players))))))

(defn- get-player-handler [args]
  (if-let [name (arg-str args "name")]
    (if-let [{:keys [name age nationality overall potential club position
                     jersey value wage height weight foot skills]}
             (query/get-player name)]
      (str name "\n"
           "- Age: " age ", Nationality: " nationality "\n"
           "- Overall: " overall ", Potential: " potential "\n"
           "- Club: " (or club "Free agent")
           (when position (str ", Position: " position))
           (when jersey (str ", Jersey: #" jersey)) "\n"
           "- Value: " value ", Wage: " wage "\n"
           "- Height: " height ", Weight: " weight ", Preferred foot: " foot "\n"
           "- Top skills: "
           (->> skills
                (sort-by (comp - val))
                (take 6)
                (map (fn [[k v]] (str k " " v)))
                (str/join ", ")))
      (str "No player named \"" name "\" found in the FIFA dataset."))
    "The name parameter is required."))

(defn- competition-stats-handler [args]
  (let [{:keys [competition season matches total-goals avg-goals
                home-wins draws away-wins]}
        (query/competition-stats {:competition (arg-str args "competition")
                                  :season (arg-int args "season")})]
    (if (zero? matches)
      "No matches found for those filters."
      (str "Statistics for " competition (when season (str ", season " season)) ":\n"
           "- Matches with scores: " matches "\n"
           "- Total goals: " total-goals "\n"
           "- Average goals per match: " (format "%.2f" avg-goals) "\n"
           "- Home wins: " home-wins " (" (fmt-pct home-wins matches) ")\n"
           "- Draws: " draws " (" (fmt-pct draws matches) ")\n"
           "- Away wins: " away-wins " (" (fmt-pct away-wins matches) ")"))))

(defn- biggest-wins-handler [args]
  (let [limit (or (arg-int args "limit") 10)
        matches (query/biggest-wins {:competition (arg-str args "competition")
                                     :season (arg-int args "season")
                                     :limit limit})]
    (if (empty? matches)
      "No matches found."
      (str "Biggest victories:\n"
           (str/join "\n"
                     (map-indexed
                      (fn [i {:keys [home-goals away-goals] :as m}]
                        (str (inc i) (subs (format-match m) 1)
                             "  [margin " (abs (- home-goals away-goals)) "]"))
                      matches))))))

(defn- list-teams-handler [args]
  (let [teams (query/list-teams {:competition (arg-str args "competition")
                                 :season (arg-int args "season")})]
    (str (count teams) " teams:\n" (str/join "\n" (map #(str "- " %) teams)))))

;; ---------------------------------------------------------------------------
;; Registry

(def ^:private competition-prop
  {:type "string"
   :description "Competition filter: 'brasileirao'/'serie a', 'serie b', 'serie c', 'copa do brasil', or 'libertadores'."})

(def tools
  [{:name "search_matches"
    :description "Search matches across all competitions (Brasileirão Série A/B/C 2003-2023, Copa do Brasil, Copa Libertadores). Filter by team, opponent, competition, season, date range or stage. Team names are normalized, so 'Flamengo', 'Flamengo-RJ' and 'São Paulo'/'Sao Paulo' all work."
    :inputSchema {:type "object"
                  :properties {:team {:type "string" :description "Team name (matches home or away)."}
                               :opponent {:type "string" :description "Second team, to find matches between two specific teams."}
                               :competition competition-prop
                               :season {:type "integer" :description "Season year, e.g. 2023."}
                               :date_from {:type "string" :description "Earliest date, ISO format yyyy-MM-dd."}
                               :date_to {:type "string" :description "Latest date, ISO format yyyy-MM-dd."}
                               :stage {:type "string" :description "Knockout stage filter, e.g. 'final', 'semifinals', 'group stage' (Libertadores and Copa do Brasil)."}
                               :limit {:type "integer" :description "Max matches to list (default 20). Results are sorted newest first."}}
                  :required []}
    :handler search-matches-handler}

   {:name "head_to_head"
    :description "Head-to-head record between two teams: full match list plus win/draw tally (e.g. Flamengo vs Fluminense)."
    :inputSchema {:type "object"
                  :properties {:team1 {:type "string"}
                               :team2 {:type "string"}
                               :competition competition-prop
                               :season {:type "integer"}}
                  :required ["team1" "team2"]}
    :handler head-to-head-handler}

   {:name "get_team_stats"
    :description "Win/draw/loss record and goals for/against for a team, optionally filtered by season, competition and venue (home/away)."
    :inputSchema {:type "object"
                  :properties {:team {:type "string"}
                               :season {:type "integer"}
                               :competition competition-prop
                               :venue {:type "string" :enum ["home" "away"]
                                       :description "Only home or only away matches."}}
                  :required ["team"]}
    :handler team-stats-handler}

   {:name "get_standings"
    :description "League table for a season calculated from match results (3 points per win). Defaults to Brasileirão Série A; data covers 2003-2023. Position 1 is the champion; in Série A the bottom 4 were relegated."
    :inputSchema {:type "object"
                  :properties {:season {:type "integer" :description "Season year, e.g. 2019."}
                               :competition competition-prop}
                  :required ["season"]}
    :handler standings-handler}

   {:name "search_players"
    :description "Search the FIFA 19 player database (18,207 players, 827 Brazilians). Filter by name, nationality, club, position or minimum overall rating; results sorted by rating."
    :inputSchema {:type "object"
                  :properties {:name {:type "string" :description "Partial or full player name."}
                               :nationality {:type "string" :description "e.g. 'Brazil'."}
                               :club {:type "string" :description "Club name, e.g. 'Cruzeiro'."}
                               :position {:type "string" :description "FIFA position code, e.g. ST, GK, CAM, LW."}
                               :min_overall {:type "integer" :description "Minimum overall rating (0-99)."}
                               :limit {:type "integer" :description "Max players to return (default 20)."}}
                  :required []}
    :handler search-players-handler}

   {:name "get_player"
    :description "Detailed profile for one player from the FIFA 19 dataset: ratings, club, value, physical attributes and top skills."
    :inputSchema {:type "object"
                  :properties {:name {:type "string" :description "Player name, e.g. 'Neymar' or 'Gabriel Barbosa'."}}
                  :required ["name"]}
    :handler get-player-handler}

   {:name "get_competition_stats"
    :description "Aggregate statistics: matches played, average goals per match, home-win/draw/away-win rates. Filter by competition and/or season; no filters means the whole dataset."
    :inputSchema {:type "object"
                  :properties {:competition competition-prop
                               :season {:type "integer"}}
                  :required []}
    :handler competition-stats-handler}

   {:name "get_biggest_wins"
    :description "Matches with the largest goal margins, optionally filtered by competition and season."
    :inputSchema {:type "object"
                  :properties {:competition competition-prop
                               :season {:type "integer"}
                               :limit {:type "integer" :description "How many matches (default 10)."}}
                  :required []}
    :handler biggest-wins-handler}

   {:name "list_teams"
    :description "List the canonical names of all teams in the dataset, optionally for one competition and/or season. Useful to resolve team-name spelling."
    :inputSchema {:type "object"
                  :properties {:competition competition-prop
                               :season {:type "integer"}}
                  :required []}
    :handler list-teams-handler}])

(def tool-index (into {} (map (juxt :name identity)) tools))

(defn list-tools
  "Tool descriptors as sent in the MCP tools/list response."
  []
  (mapv #(select-keys % [:name :description :inputSchema]) tools))

(defn call-tool
  "Runs a tool by name. Returns the MCP tools/call result map."
  [name arguments]
  (if-let [{:keys [handler]} (tool-index name)]
    (try
      {:content [{:type "text" :text (handler (or arguments {}))}]
       :isError false}
      (catch Exception e
        {:content [{:type "text" :text (str "Tool error: " (.getMessage e))}]
         :isError true}))
    {:content [{:type "text" :text (str "Unknown tool: " name)}]
     :isError true}))
