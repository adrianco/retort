(ns brazilian-soccer.tools
  "MCP tool definitions and the plain-text formatting of query results."
  (:require [brazilian-soccer.queries :as q]
            [clojure.string :as str]))

(defn- ->long [x]
  (cond
    (nil? x) nil
    (number? x) (long x)
    (string? x) (parse-long (str/trim x))
    :else nil))

(defn- ->keyword-venue [x]
  (when x (keyword (str/lower-case (str x)))))

(defn- pct [x] (format "%.1f%%" (* 100.0 x)))

(defn- match-line [m]
  (format "%s: %s %d-%d %s (%s%s)"
          (:date m) (:home m) (:home-goals m) (:away-goals m) (:away m)
          (:competition m)
          (if (:round m) (str ", round " (:round m)) "")))

(defn- format-record [{:keys [played wins draws losses goals-for goals-against win-rate]}]
  (str "- Matches: " played "\n"
       "- Wins: " wins ", Draws: " draws ", Losses: " losses "\n"
       "- Goals For: " goals-for ", Goals Against: " goals-against "\n"
       "- Win rate: " (pct win-rate)))

(defn- scope-label [{:keys [competition season venue]}]
  (str/join ", " (remove nil? [(or competition "all competitions")
                               (when season (str season))
                               (when venue (name venue))])))

(defn- unknown-team [team]
  (throw (ex-info (str "Unknown team: " team) {:team team})))

(defn search-matches-text [{:keys [matches]} args]
  (let [opts {:team (get args "team")
              :opponent (get args "opponent")
              :competition (get args "competition")
              :season (->long (get args "season"))
              :from (get args "date_from")
              :to (get args "date_to")
              :venue (->keyword-venue (get args "venue"))}
        limit (or (->long (get args "limit")) 20)
        ms (q/search-matches matches opts)]
    (str "Found " (count ms) " matches (showing " (min limit (count ms)) "):\n"
         (str/join "\n" (map #(str "- " (match-line %)) (take limit ms))))))

(defn team-record-text [{:keys [matches]} args]
  (let [team (get args "team")
        opts {:team team
              :competition (get args "competition")
              :season (->long (get args "season"))
              :venue (or (->keyword-venue (get args "venue")) :any)}
        {:keys [team-key record]} (q/team-record matches opts)]
    (when-not team-key (unknown-team team))
    (str team " record (" (scope-label opts) "):\n" (format-record record))))

(defn head-to-head-text [{:keys [matches]} args]
  (let [a (get args "team_a")
        b (get args "team_b")
        {:keys [team-a-key team-b-key record matches] } (q/head-to-head matches a b)]
    (when-not team-a-key (unknown-team a))
    (when-not team-b-key (unknown-team b))
    (str a " vs " b " head-to-head in dataset:\n"
         (format-record record) "\n"
         (str/join "\n" (map #(str "- " (match-line %)) (take 10 matches)))
         (when (> (count matches) 10) (str "\n... (" (- (count matches) 10) " more matches)")))))

(defn standings-text [{:keys [matches]} args]
  (let [season (->long (get args "season"))
        competition (or (get args "competition") "Brasileirão")
        rows (q/standings matches {:season season :competition competition})]
    (if (empty? rows)
      (str "No " competition " matches found for season " season ".")
      (str season " " competition " standings (calculated from matches):\n"
           (str/join "\n"
                     (map-indexed
                      (fn [i {:keys [team points wins draws losses goals-for goals-against]}]
                        (format "%d. %s - %d pts (%dW, %dD, %dL) GF %d GA %d"
                                (inc i) team points wins draws losses goals-for goals-against))
                      rows))))))

(defn league-stats-text [{:keys [matches]} args]
  (let [opts {:competition (get args "competition")
              :season (->long (get args "season"))
              :from (get args "date_from")
              :to (get args "date_to")}
        {:keys [matches goals-per-match home-win-rate away-win-rate draw-rate biggest-wins]}
        (q/league-stats matches opts)]
    (str "Statistics (" (scope-label opts) ", " matches " matches):\n"
         (format "Average goals per match: %.2f\n" goals-per-match)
         (format "Home win rate: %s, Away win rate: %s, Draw rate: %s\n"
                 (pct home-win-rate) (pct away-win-rate) (pct draw-rate))
         "Biggest wins:\n"
         (str/join "\n" (map #(str "- " (match-line %)) biggest-wins)))))

(defn- player-line [i p]
  (format "%d. %s - Overall: %s, Position: %s, Club: %s"
          (inc i) (:name p) (:overall p) (or (:position p) "?") (or (:club p) "none")))

(defn search-players-text [{:keys [players]} args]
  (let [opts {:name (get args "name")
              :nationality (get args "nationality")
              :club (get args "club")
              :position (get args "position")
              :min-overall (->long (get args "min_overall"))
              :limit (or (->long (get args "limit")) 20)}
        ps (q/search-players players opts)]
    (if (empty? ps)
      "No players found."
      (str "Players (" (count ps) " shown, highest rated first):\n"
           (str/join "\n" (map-indexed player-line ps))))))

(defn club-summary-text [{:keys [players]} _args]
  (let [rows (take 20 (q/brazilian-club-summary players))]
    (str "Brazilian players at clubs (count, average overall):\n"
         (str/join "\n" (map (fn [{:keys [club players average-overall]}]
                               (format "- %s: %d players (avg rating: %.0f)" club players average-overall))
                             rows)))))

(defn- int-prop [desc] {:type "integer" :description desc})
(defn- str-prop [desc] {:type "string" :description desc})

(def tool-specs
  [{:name "search_matches"
    :description "Find matches in the Brazilian football datasets by team, opponent, competition, season, date range and venue."
    :inputSchema {:type "object"
                  :properties {:team (str-prop "Team name, e.g. Flamengo")
                               :opponent (str-prop "Opponent team name")
                               :competition (str-prop "Brasileirão, Copa do Brasil, Libertadores, Brasileirão Série B or C")
                               :season (int-prop "Season year, e.g. 2023")
                               :date_from (str-prop "Earliest date, yyyy-mm-dd")
                               :date_to (str-prop "Latest date, yyyy-mm-dd")
                               :venue (str-prop "home, away or any (requires team)")
                               :limit (int-prop "Maximum matches to list (default 20)")}}
    :handler search-matches-text}

   {:name "team_record"
    :description "Win/draw/loss and goals record for a team, optionally by competition, season and venue."
    :inputSchema {:type "object"
                  :properties {:team (str-prop "Team name")
                               :competition (str-prop "Competition name")
                               :season (int-prop "Season year")
                               :venue (str-prop "home, away or any")}
                  :required ["team"]}
    :handler team-record-text}

   {:name "head_to_head"
    :description "Head-to-head record between two teams across all matches in the datasets."
    :inputSchema {:type "object"
                  :properties {:team_a (str-prop "First team")
                               :team_b (str-prop "Second team")}
                  :required ["team_a" "team_b"]}
    :handler head-to-head-text}

   {:name "standings"
    :description "Calculated league table for a season (3 points for a win, 1 for a draw)."
    :inputSchema {:type "object"
                  :properties {:season (int-prop "Season year")
                               :competition (str-prop "Competition, default Brasileirão")}
                  :required ["season"]}
    :handler standings-text}

   {:name "league_stats"
    :description "Aggregate statistics: goals per match, home/away/draw rates and biggest wins."
    :inputSchema {:type "object"
                  :properties {:competition (str-prop "Competition name")
                               :season (int-prop "Season year")
                               :date_from (str-prop "Earliest date, yyyy-mm-dd")
                               :date_to (str-prop "Latest date, yyyy-mm-dd")}}
    :handler league-stats-text}

   {:name "search_players"
    :description "Search FIFA player data by name, nationality, club, position and minimum overall rating."
    :inputSchema {:type "object"
                  :properties {:name (str-prop "Player name (partial match)")
                               :nationality (str-prop "Nationality, e.g. Brazil")
                               :club (str-prop "Club name (partial match)")
                               :position (str-prop "Position code, e.g. ST, GK")
                               :min_overall (int-prop "Minimum overall rating")
                               :limit (int-prop "Maximum players to list (default 20)")}}
    :handler search-players-text}

   {:name "brazilian_club_summary"
    :description "Brazilian players grouped by club with counts and average overall rating."
    :inputSchema {:type "object" :properties {}}
    :handler club-summary-text}])

(defn tool-descriptors
  "Tool list for tools/list, without the handler functions."
  []
  (mapv #(dissoc % :handler) tool-specs))

(defn call-tool
  "Runs a tool by name against loaded data {:matches :players}. Returns the
  response text. Throws ex-info with :unknown-tool when the name is not registered."
  [data tool-name args]
  (if-let [{:keys [handler]} (first (filter #(= tool-name (:name %)) tool-specs))]
    (handler data args)
    (throw (ex-info (str "Unknown tool: " tool-name) {:unknown-tool tool-name}))))
