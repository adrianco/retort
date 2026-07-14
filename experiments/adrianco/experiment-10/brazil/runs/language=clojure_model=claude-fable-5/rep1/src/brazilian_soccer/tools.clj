(ns brazilian-soccer.tools
  "CONTEXT
  =======
  MCP tool registry for the Brazilian Soccer server.

  Defines the tools exposed over the Model Context Protocol.  Each tool is a
  map with :name, :description, :inputSchema (JSON Schema, keyword keys -
  serialized to JSON by the server) and :handler, a function from the parsed
  arguments map (keyword keys) to a human-readable answer string.

  Tools
  -----
    search_matches      find matches by team(s)/competition/season/date range
    head_to_head        compare two clubs across all meetings
    team_stats          W/D/L + goals record (overall, home or away)
    league_standings    season table calculated from results
    biggest_wins        largest margins of victory
    competition_stats   goals per match, home-win/draw rates, etc.
    list_competitions   competitions covered with seasons and match counts
    search_players      FIFA players by name/nationality/club/position
    top_players         highest-rated players for a filter
    club_player_summary players per club with average ratings
    data_summary        what was loaded from each CSV file

  The handlers format answers in the style shown in TASK.md (one line per
  match, summary tables for standings and records)."
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.query :as query]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; Formatting helpers

(defn- pct [x] (format "%.1f%%" (* 100.0 (double x))))

(defn- team-name [db canon]
  (get (:display-names db) canon canon))

(defn format-match [db m]
  (let [score (if (and (:home-goals m) (:away-goals m))
                (str (:home-goals m) "-" (:away-goals m))
                "?-?")
        ctx (->> [(:competition m)
                  (when (:round m) (str "Round " (:round m)))
                  (:stage m)
                  (when (:season m) (str "season " (:season m)))]
                 (remove nil?)
                 (str/join ", "))]
    (str "- " (or (:date m) "unknown date") ": "
         (team-name db (:home m)) " " score " " (team-name db (:away m))
         " (" ctx ")")))

(defn format-matches [db matches limit]
  (let [limit (or limit 20)
        shown (take limit matches)
        extra (- (count matches) (count shown))]
    (str (str/join "\n" (map #(format-match db %) shown))
         (when (pos? extra)
           (str "\n... (" extra " more matches in dataset)")))))

;; ---------------------------------------------------------------------------
;; Tool handlers

(defn- search-matches-handler
  [{:keys [team opponent competition season date_from date_to stage limit]}]
  (let [db (data/db)
        matches (query/search-matches db {:team team :opponent opponent
                                          :competition competition
                                          :season season
                                          :date-from date_from :date-to date_to
                                          :stage stage})]
    (if (empty? matches)
      "No matches found for those criteria."
      (str "Found " (count matches) " match(es):\n"
           (format-matches db matches (or limit 20))))))

(defn- head-to-head-handler [{:keys [team1 team2 competition season limit]}]
  (let [db (data/db)
        {:keys [matches played team1-wins team2-wins draws team1-goals team2-goals]}
        (query/head-to-head db team1 team2 {:competition competition :season season})
        n1 (team-name db (data/canonical-team team1))
        n2 (team-name db (data/canonical-team team2))]
    (if (empty? matches)
      (str "No matches found between " team1 " and " team2 ".")
      (str n1 " vs " n2 ":\n"
           (format-matches db (reverse matches) (or limit 15))
           "\n\nHead-to-head in dataset (" played " matches with final scores): "
           n1 " " team1-wins " wins, " n2 " " team2-wins " wins, " draws " draws\n"
           "Goals: " n1 " " team1-goals ", " n2 " " team2-goals))))

(defn- team-stats-handler [{:keys [team season competition venue]}]
  (let [db (data/db)
        {:keys [played wins draws losses goals-for goals-against win-rate]}
        (query/team-record db team {:season season :competition competition :venue venue})
        n (team-name db (data/canonical-team team))
        scope (->> [(when venue (str venue " record"))
                    (when competition competition)
                    (when season (str "season " season))]
                   (remove nil?)
                   (str/join ", "))]
    (if (zero? played)
      (str "No completed matches found for " team
           (when (seq scope) (str " (" scope ")")) ".")
      (str n (if (seq scope) (str " (" scope ")") "") ":\n"
           "- Matches: " played "\n"
           "- Wins: " wins ", Draws: " draws ", Losses: " losses "\n"
           "- Goals For: " goals-for ", Goals Against: " goals-against "\n"
           "- Win rate: " (pct win-rate)))))

(defn- standings-handler [{:keys [season competition limit]}]
  (let [db (data/db)
        season-n (data/parse-long* (str season))
        table (query/standings db season-n {:competition competition})]
    (if (empty? table)
      (str "No matches found for season " season
           (when competition (str " in " competition)) ".")
      (str season " " (or competition "Brasileirão Série A")
           " standings (calculated from " (reduce + (map :played table)) " team-matches):\n"
           (str/join "\n"
                     (for [row (take (or limit 30) table)]
                       (format "%2d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d)"
                               (:rank row) (team-name db (:team row)) (:points row)
                               (:wins row) (:draws row) (:losses row)
                               (:goals-for row) (:goals-against row))))
           "\n\nChampion: " (team-name db (:team (first table)))))))

(defn- biggest-wins-handler [{:keys [competition season team limit]}]
  (let [db (data/db)
        wins (query/biggest-wins db {:competition competition :season season
                                     :team team :limit (or limit 10)})]
    (if (empty? wins)
      "No matches found for those criteria."
      (str "Biggest victories"
           (when competition (str " in " competition))
           (when season (str ", season " season)) ":\n"
           (str/join "\n"
                     (map-indexed
                      (fn [i m]
                        (str (inc i) ". " (or (:date m) "unknown date") ": "
                             (team-name db (:home m)) " "
                             (:home-goals m) "-" (:away-goals m) " "
                             (team-name db (:away m))
                             " (" (:competition m) ")"))
                      wins))))))

(defn- competition-stats-handler [{:keys [competition season]}]
  (let [db (data/db)
        {:keys [matches total-goals avg-goals home-wins draws away-wins
                home-win-rate draw-rate away-win-rate]}
        (query/competition-stats db {:competition competition :season season})]
    (if (zero? matches)
      "No completed matches found for those criteria."
      (str "Statistics"
           (when competition (str " for " competition))
           (when season (str ", season " season)) ":\n"
           "- Matches (with final score): " matches "\n"
           "- Total goals: " total-goals "\n"
           "- Average goals per match: " (format "%.2f" avg-goals) "\n"
           "- Home wins: " home-wins " (" (pct home-win-rate) ")\n"
           "- Draws: " draws " (" (pct draw-rate) ")\n"
           "- Away wins: " away-wins " (" (pct away-win-rate) ")"))))

(defn- list-competitions-handler [_]
  (let [db (data/db)]
    (str "Competitions in the dataset:\n"
         (str/join "\n"
                   (for [{:keys [competition matches first-season last-season]}
                         (query/competitions db)]
                     (str "- " competition ": " matches " matches"
                          (when first-season
                            (str " (seasons " first-season "-" last-season ")"))))))))

(defn format-player [p]
  (str (:name p) " - Overall: " (:overall p)
       ", Position: " (or (:position p) "?")
       ", Age: " (:age p)
       ", Nationality: " (:nationality p)
       ", Club: " (if (str/blank? (str (:club p))) "none" (:club p))))

(defn- search-players-handler [{:keys [name nationality club position min_overall limit]}]
  (let [db (data/db)
        players (query/search-players db {:name name :nationality nationality
                                          :club club :position position
                                          :min-overall min_overall})
        limit (or limit 20)
        shown (take limit players)]
    (if (empty? players)
      "No players found for those criteria."
      (str "Found " (count players) " player(s):\n"
           (str/join "\n" (map #(str "- " (format-player %)) shown))
           (when (> (count players) limit)
             (str "\n... (" (- (count players) limit) " more players)"))))))

(defn- top-players-handler [{:keys [nationality club position limit]}]
  (let [db (data/db)
        players (query/top-players db {:nationality nationality :club club
                                       :position position}
                                   (or limit 10))]
    (if (empty? players)
      "No players found for those criteria."
      (str "Top-rated players"
           (when nationality (str " from " nationality))
           (when club (str " at " club)) ":\n"
           (str/join "\n"
                     (map-indexed (fn [i p] (str (inc i) ". " (format-player p)))
                                  players))))))

(defn- club-player-summary-handler [{:keys [nationality min_players limit]}]
  (let [db (data/db)
        clubs (query/club-player-summary db {:nationality nationality
                                             :min-players min_players})]
    (if (empty? clubs)
      "No clubs found for those criteria."
      (str "Players per club"
           (when nationality (str " (nationality: " nationality ")")) ":\n"
           (str/join "\n"
                     (for [{:keys [club players avg-overall]} (take (or limit 20) clubs)]
                       (str "- " club ": " players " players (avg rating: "
                            (format "%.1f" avg-overall) ")")))))))

(defn- data-summary-handler [_]
  (let [db (data/db)
        fc (:file-counts db)]
    (str "Loaded data:\n"
         "- Brasileirao_Matches.csv: " (:brasileirao fc) " matches\n"
         "- Brazilian_Cup_Matches.csv: " (:cup fc) " matches\n"
         "- Libertadores_Matches.csv: " (:libertadores fc) " matches\n"
         "- novo_campeonato_brasileiro.csv: " (:historical fc) " matches\n"
         "- BR-Football-Dataset.csv: " (:extended fc) " matches\n"
         "- fifa_data.csv: " (:players fc) " players\n"
         "After de-duplicating overlapping files: " (count (:matches db))
         " unique matches across " (count (query/competitions db)) " competitions.")))

;; ---------------------------------------------------------------------------
;; Tool registry

(def ^:private team-prop
  {:type "string" :description "Team name, e.g. \"Flamengo\", \"Sao Paulo\", \"Palmeiras-SP\" (accents and state suffixes optional)"})

(def ^:private competition-prop
  {:type "string" :description "Competition filter, e.g. \"Brasileirao\", \"Copa do Brasil\", \"Libertadores\", \"Serie B\""})

(def ^:private season-prop
  {:type "integer" :description "Season year, e.g. 2019"})

(def tools
  [{:name "search_matches"
    :description "Find soccer matches by team, opponent, competition, season, stage and/or date range. Returns one line per match with date, score and competition."
    :inputSchema {:type "object"
                  :properties {:team team-prop
                               :opponent (assoc team-prop :description "Optional second team; restricts to meetings between the two")
                               :competition competition-prop
                               :season season-prop
                               :date_from {:type "string" :description "Earliest date, ISO format YYYY-MM-DD"}
                               :date_to {:type "string" :description "Latest date, ISO format YYYY-MM-DD"}
                               :stage {:type "string" :description "Cup stage or round filter, e.g. \"final\", \"group stage\""}
                               :limit {:type "integer" :description "Max matches to list (default 20)"}}
                  :required []}
    :handler search-matches-handler}

   {:name "head_to_head"
    :description "Compare two teams: every meeting in the dataset plus a win/draw/loss and goals summary."
    :inputSchema {:type "object"
                  :properties {:team1 team-prop
                               :team2 team-prop
                               :competition competition-prop
                               :season season-prop
                               :limit {:type "integer" :description "Max matches to list (default 15)"}}
                  :required [:team1 :team2]}
    :handler head-to-head-handler}

   {:name "team_stats"
    :description "Win/draw/loss record, goals for/against and win rate for a team, optionally restricted to a season, competition and home/away."
    :inputSchema {:type "object"
                  :properties {:team team-prop
                               :season season-prop
                               :competition competition-prop
                               :venue {:type "string" :enum ["home" "away" "all"]
                                       :description "Restrict to home or away matches (default all)"}}
                  :required [:team]}
    :handler team-stats-handler}

   {:name "league_standings"
    :description "League table for a season calculated from match results (3 points per win). Defaults to Brasileirão Série A; the top team is the champion."
    :inputSchema {:type "object"
                  :properties {:season season-prop
                               :competition competition-prop
                               :limit {:type "integer" :description "Max table rows (default 30)"}}
                  :required [:season]}
    :handler standings-handler}

   {:name "biggest_wins"
    :description "Matches with the largest margins of victory, optionally filtered by competition, season or team."
    :inputSchema {:type "object"
                  :properties {:competition competition-prop
                               :season season-prop
                               :team team-prop
                               :limit {:type "integer" :description "How many to return (default 10)"}}
                  :required []}
    :handler biggest-wins-handler}

   {:name "competition_stats"
    :description "Aggregate statistics for a competition and/or season: matches, total goals, average goals per match, home-win/draw/away-win rates."
    :inputSchema {:type "object"
                  :properties {:competition competition-prop
                               :season season-prop}
                  :required []}
    :handler competition-stats-handler}

   {:name "list_competitions"
    :description "List the competitions covered by the dataset with match counts and season ranges."
    :inputSchema {:type "object" :properties {} :required []}
    :handler list-competitions-handler}

   {:name "search_players"
    :description "Search the FIFA player database by name, nationality, club, position and/or minimum overall rating. Sorted by rating."
    :inputSchema {:type "object"
                  :properties {:name {:type "string" :description "Player name substring, e.g. \"Neymar\""}
                               :nationality {:type "string" :description "e.g. \"Brazil\""}
                               :club {:type "string" :description "Club name substring, e.g. \"Fluminense\""}
                               :position {:type "string" :description "Exact position code, e.g. ST, GK, CAM, LW"}
                               :min_overall {:type "integer" :description "Minimum FIFA overall rating"}
                               :limit {:type "integer" :description "Max players to list (default 20)"}}
                  :required []}
    :handler search-players-handler}

   {:name "top_players"
    :description "Highest-rated FIFA players for an optional nationality, club and/or position filter."
    :inputSchema {:type "object"
                  :properties {:nationality {:type "string" :description "e.g. \"Brazil\""}
                               :club {:type "string" :description "Club name substring"}
                               :position {:type "string" :description "Exact position code, e.g. ST, GK"}
                               :limit {:type "integer" :description "How many to return (default 10)"}}
                  :required []}
    :handler top-players-handler}

   {:name "club_player_summary"
    :description "Player counts and average FIFA rating per club, optionally restricted to a nationality (e.g. Brazilian players per club)."
    :inputSchema {:type "object"
                  :properties {:nationality {:type "string" :description "e.g. \"Brazil\""}
                               :min_players {:type "integer" :description "Only clubs with at least this many matching players"}
                               :limit {:type "integer" :description "Max clubs to list (default 20)"}}
                  :required []}
    :handler club-player-summary-handler}

   {:name "data_summary"
    :description "Describe the loaded datasets: rows per CSV file and unique matches after de-duplication."
    :inputSchema {:type "object" :properties {} :required []}
    :handler data-summary-handler}])

(def tools-by-name (into {} (map (juxt :name identity)) tools))

(defn list-tools
  "Tool descriptors for the MCP tools/list response (no handlers)."
  []
  (mapv #(dissoc % :handler) tools))

(defn call-tool
  "Run a tool by name with an arguments map (keyword keys).  Returns an MCP
  tools/call result map.  Unknown tool -> nil (the server turns that into a
  JSON-RPC error); handler exceptions -> isError true."
  [name arguments]
  (when-let [tool (get tools-by-name name)]
    (try
      {:content [{:type "text" :text ((:handler tool) (or arguments {}))}]
       :isError false}
      (catch Exception e
        {:content [{:type "text"
                    :text (str "Error executing " name ": " (.getMessage e))}]
         :isError true}))))
