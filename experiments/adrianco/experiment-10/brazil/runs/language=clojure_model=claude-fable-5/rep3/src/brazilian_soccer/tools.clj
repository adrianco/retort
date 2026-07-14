(ns brazilian-soccer.tools
  "MCP tool definitions: schemas, handlers and text formatting."
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.queries :as q]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; Argument coercion

(defn- arg-int [args k]
  (let [v (get args k)]
    (cond
      (number? v) (long v)
      (string? v) (data/parse-num v)
      :else nil)))

(defn- arg-str [args k]
  (some-> (get args k) str str/trim not-empty))

(defn- arg-venue [args]
  (case (some-> (arg-str args "venue") str/lower-case)
    "home" :home
    "away" :away
    :all))

(defn- match-criteria [args]
  {:team        (arg-str args "team")
   :opponent    (arg-str args "opponent")
   :competition (arg-str args "competition")
   :season      (arg-int args "season")
   :date-from   (arg-str args "date_from")
   :date-to     (arg-str args "date_to")})

;; ---------------------------------------------------------------------------
;; Formatting

(defn- pct [x] (format "%.1f%%" (double x)))

(defn fmt-match [m]
  (let [extra (cond
                (:stage m) (:stage m)
                (:round m) (str "Round " (:round m))
                :else nil)
        score (if (q/played? m)
                (format "%d-%d" (:home-goals m) (:away-goals m))
                "?-?")]
    (str "- " (or (:date m) "unknown date") ": "
         (:home-display m) " " score " " (:away-display m)
         " (" (:competition m) (when extra (str ", " extra)) ")"
         (when (:venue m) (str " @ " (:venue m))))))

(defn- fmt-match-list [matches limit]
  (let [shown (take limit matches)
        extra (- (count matches) (count shown))]
    (str (str/join "\n" (map fmt-match shown))
         (when (pos? extra)
           (format "\n... (%d more matches in dataset)" extra)))))

(defn- fmt-record [{:keys [played wins draws losses gf ga] :as rec}]
  (str "- Matches: " played "\n"
       "- Wins: " wins ", Draws: " draws ", Losses: " losses "\n"
       "- Goals For: " gf ", Goals Against: " ga "\n"
       "- Win rate: " (pct (q/win-rate rec))))

(defn- criteria-label [{:keys [competition season venue]}]
  (str/join ", " (remove nil?
                         [(some-> competition data/norm-competition)
                          season
                          (when (and venue (not= venue :all)) (name venue))])))

;; ---------------------------------------------------------------------------
;; Tool handlers (each returns a plain-text answer)

(defn- t-search-matches [db args]
  (let [criteria (match-criteria args)
        limit    (or (arg-int args "limit") 20)
        ms       (q/find-matches db criteria)]
    (if (empty? ms)
      "No matches found for those criteria."
      (str (count ms) " match(es) found"
           (let [l (criteria-label criteria)] (when (seq l) (str " (" l ")")))
           ":\n"
           (fmt-match-list ms limit)))))

(defn- t-head-to-head [db args]
  (let [t1 (arg-str args "team1")
        t2 (arg-str args "team2")
        {:keys [team1-wins team2-wins draws matches]} (q/head-to-head db t1 t2)]
    (if (empty? matches)
      (format "No matches found between %s and %s." t1 t2)
      (str t1 " vs " t2 " (head-to-head, all competitions in dataset):\n"
           "- Matches: " (count matches) "\n"
           (format "- %s: %d wins, %s: %d wins, draws: %d%n" t1 team1-wins t2 team2-wins draws)
           "\nMost recent matches:\n"
           (fmt-match-list matches (or (arg-int args "limit") 10))))))

(defn- t-team-stats [db args]
  (let [criteria (assoc (match-criteria args) :venue (arg-venue args))
        team     (:team criteria)
        rec      (q/team-stats db criteria)]
    (if (zero? (:played rec))
      (format "No completed matches found for %s with those criteria." team)
      (str team " record"
           (let [l (criteria-label criteria)] (when (seq l) (str " (" l ")")))
           ":\n" (fmt-record rec)))))

(defn- t-standings [db args]
  (let [season (arg-int args "season")
        comp   (or (some-> (arg-str args "competition") data/norm-competition)
                   "Brasileirão Série A")
        rows   (q/standings db {:season season :competition comp})]
    (if (empty? rows)
      (format "No completed matches found for %s in season %s." comp season)
      (str season " " comp " standings (calculated from match results):\n"
           (str/join "\n"
                     (map-indexed
                      (fn [i {:keys [display points wins draws losses gf ga gd]}]
                        (format "%2d. %s - %d pts (%dW %dD %dL, GF %d, GA %d, GD %+d)%s"
                                (inc i) display points wins draws losses gf ga gd
                                (cond
                                  (zero? i) " - Champion"
                                  (and (= comp "Brasileirão Série A")
                                       (>= i (- (count rows) 4))) " - Relegation zone"
                                  :else "")))
                      rows))))))

(defn- t-competition-stats [db args]
  (let [criteria (match-criteria args)
        s (q/competition-summary db criteria)]
    (if (zero? (:matches s))
      "No completed matches found for those criteria."
      (str "Statistics"
           (let [l (criteria-label criteria)] (when (seq l) (str " (" l ")")))
           ":\n"
           "- Matches: " (:matches s) "\n"
           "- Total goals: " (:goals s) "\n"
           (format "- Average goals per match: %.2f%n" (:avg-goals s))
           "- Home wins: " (:home-wins s) " (" (pct (:home-win-rate s)) ")\n"
           "- Draws: " (:draws s) " (" (pct (:draw-rate s)) ")\n"
           "- Away wins: " (:away-wins s) " (" (pct (:away-win-rate s)) ")"))))

(defn- t-biggest-wins [db args]
  (let [criteria (match-criteria args)
        limit (or (arg-int args "limit") 10)
        ms (q/biggest-wins db criteria limit)]
    (if (empty? ms)
      "No completed matches found for those criteria."
      (str "Biggest victories"
           (let [l (criteria-label criteria)] (when (seq l) (str " (" l ")")))
           ":\n" (fmt-match-list ms limit)))))

(defn- t-best-records [db args]
  (let [criteria (match-criteria args)
        venue (arg-venue args)
        min-matches (or (arg-int args "min_matches") 10)
        limit (or (arg-int args "limit") 10)
        rows (q/best-records db criteria venue min-matches limit)]
    (if (empty? rows)
      "No teams found with enough matches for those criteria."
      (str "Best " (if (= venue :all) "overall" (name venue)) " records"
           (let [l (criteria-label (dissoc criteria :venue))]
             (when (seq l) (str " (" l ")")))
           " (min " min-matches " matches):\n"
           (str/join "\n"
                     (map-indexed
                      (fn [i {:keys [display played wins draws losses win-rate]}]
                        (format "%2d. %s - %s win rate (%dW %dD %dL in %d matches)"
                                (inc i) display (pct win-rate) wins draws losses played))
                      rows))))))

(defn- fmt-player-line [p]
  (format "%s - Overall: %s, Position: %s, Age: %s, Club: %s (%s)"
          (:name p) (:overall p) (or (:position p) "?") (:age p)
          (or (not-empty (:club p)) "No club") (:nationality p)))

(defn- t-search-players [db args]
  (let [criteria {:name        (arg-str args "name")
                  :nationality (arg-str args "nationality")
                  :club        (arg-str args "club")
                  :position    (arg-str args "position")
                  :min-overall (arg-int args "min_overall")
                  :max-age     (arg-int args "max_age")}
        limit (or (arg-int args "limit") 10)
        ps (q/search-players db criteria)]
    (if (empty? ps)
      "No players found for those criteria."
      (str (count ps) " player(s) found, sorted by overall rating:\n"
           (str/join "\n"
                     (map-indexed (fn [i p] (str (inc i) ". " (fmt-player-line p)))
                                  (take limit ps)))
           (when (> (count ps) limit)
             (format "\n... (%d more players match)" (- (count ps) limit)))))))

(defn- t-get-player [db args]
  (let [name (arg-str args "name")
        p (q/find-player db name)]
    (if-not p
      (format "No player named \"%s\" found in the FIFA dataset." name)
      (let [top-skills (->> (:skills p) (sort-by val) reverse (take 6))]
        (str (:name p) "\n"
             "- Nationality: " (:nationality p) "\n"
             "- Age: " (:age p) ", Height: " (:height p) ", Weight: " (:weight p) "\n"
             "- Club: " (or (not-empty (:club p)) "No club")
             (when (:jersey p) (str " (#" (:jersey p) ")")) "\n"
             "- Position: " (or (:position p) "?")
             ", Preferred foot: " (:preferred-foot p) "\n"
             "- Overall: " (:overall p) ", Potential: " (:potential p) "\n"
             "- Value: " (:value p) ", Wage: " (:wage p) "\n"
             "- Top skills: "
             (str/join ", " (map (fn [[k v]] (str k " " v)) top-skills)))))))

(defn- t-extended-stats [db args]
  (let [criteria (match-criteria args)
        limit (or (arg-int args "limit") 10)
        {:keys [matches averages]} (q/extended-stats db criteria)
        fmt-avg #(if % (format "%.1f" (double %)) "n/a")]
    (if (empty? matches)
      "No matches with extended statistics found for those criteria (extended stats cover Série A/B/C and Copa do Brasil, 2014-2023)."
      (str "Extended stats for " (:team criteria)
           " (" (count matches) " matches in BR-Football dataset):\n"
           "- Avg corners: " (fmt-avg (:corners-for averages))
           " for / " (fmt-avg (:corners-against averages)) " against\n"
           "- Avg shots: " (fmt-avg (:shots-for averages))
           " for / " (fmt-avg (:shots-against averages)) " against\n"
           "- Avg attacks: " (fmt-avg (:attacks-for averages))
           " for / " (fmt-avg (:attacks-against averages)) " against\n"
           "\nMost recent matches:\n"
           (fmt-match-list matches limit)))))

(defn- t-list-competitions [db _args]
  (str "Competitions in the dataset:\n"
       (str/join "\n"
                 (for [{:keys [competition matches seasons]} (q/competitions-overview db)]
                   (format "- %s: %d matches, seasons %s-%s"
                           competition matches (first seasons) (last seasons))))))

;; ---------------------------------------------------------------------------
;; Tool registry

(def ^:private team-prop
  {:type "string" :description "Team name, e.g. \"Flamengo\", \"Palmeiras\", \"Atlético-MG\". Name variations and accents are handled."})

(def ^:private competition-prop
  {:type "string"
   :description "Competition: \"Brasileirão\"/\"Serie A\", \"Serie B\", \"Serie C\", \"Copa do Brasil\" or \"Libertadores\"."})

(def ^:private season-prop
  {:type "integer" :description "Season year, e.g. 2019."})

(def tools
  [{:name "search_matches"
    :description "Search matches by team, opponent, competition, season and/or date range. Covers Brasileirão Série A 2003-2023, Série B/C 2014-2023, Copa do Brasil 2012-2023 and Copa Libertadores 2013-2022."
    :inputSchema {:type "object"
                  :properties {:team team-prop
                               :opponent (assoc team-prop :description "Opposing team name, to find matches between two specific teams.")
                               :competition competition-prop
                               :season season-prop
                               :date_from {:type "string" :description "Earliest date, ISO format (YYYY-MM-DD)."}
                               :date_to {:type "string" :description "Latest date, ISO format (YYYY-MM-DD)."}
                               :limit {:type "integer" :description "Max matches to list (default 20)."}}
                  :required []}
    :handler t-search-matches}

   {:name "head_to_head"
    :description "Head-to-head record between two teams across all competitions in the dataset: wins, draws, and recent matches."
    :inputSchema {:type "object"
                  :properties {:team1 team-prop
                               :team2 team-prop
                               :limit {:type "integer" :description "Max recent matches to list (default 10)."}}
                  :required ["team1" "team2"]}
    :handler t-head-to-head}

   {:name "get_team_stats"
    :description "A team's win/draw/loss record, goals for/against and win rate, optionally narrowed by season, competition and home/away venue."
    :inputSchema {:type "object"
                  :properties {:team team-prop
                               :season season-prop
                               :competition competition-prop
                               :venue {:type "string" :enum ["home" "away" "all"]
                                       :description "Only home matches, only away matches, or all (default)."}}
                  :required ["team"]}
    :handler t-team-stats}

   {:name "get_standings"
    :description "League standings table for a season, calculated from match results (3 points per win). Defaults to Brasileirão Série A; the last 4 places are the relegation zone."
    :inputSchema {:type "object"
                  :properties {:season season-prop
                               :competition competition-prop}
                  :required ["season"]}
    :handler t-standings}

   {:name "get_competition_stats"
    :description "Aggregate statistics for a competition/season/team filter: match count, total goals, average goals per match, and home/draw/away win rates."
    :inputSchema {:type "object"
                  :properties {:competition competition-prop
                               :season season-prop
                               :team team-prop}
                  :required []}
    :handler t-competition-stats}

   {:name "get_biggest_wins"
    :description "Matches with the largest victory margins, optionally filtered by team, competition or season."
    :inputSchema {:type "object"
                  :properties {:team team-prop
                               :competition competition-prop
                               :season season-prop
                               :limit {:type "integer" :description "Max matches to list (default 10)."}}
                  :required []}
    :handler t-biggest-wins}

   {:name "get_best_records"
    :description "Teams ranked by win rate, optionally restricted to home or away matches and filtered by competition/season."
    :inputSchema {:type "object"
                  :properties {:venue {:type "string" :enum ["home" "away" "all"]
                                       :description "Rank by home record, away record, or overall (default)."}
                               :competition competition-prop
                               :season season-prop
                               :min_matches {:type "integer" :description "Minimum matches played to qualify (default 10)."}
                               :limit {:type "integer" :description "Max teams to list (default 10)."}}
                  :required []}
    :handler t-best-records}

   {:name "search_players"
    :description "Search the FIFA player database (18,207 players) by name, nationality, club, position, minimum overall rating and/or maximum age. Results sorted by overall rating."
    :inputSchema {:type "object"
                  :properties {:name {:type "string" :description "Player name or part of it."}
                               :nationality {:type "string" :description "Nationality, e.g. \"Brazil\"."}
                               :club {:type "string" :description "Club name or part of it, e.g. \"Flamengo\"."}
                               :position {:type "string" :description "Position code, e.g. ST, GK, CAM, LW, CDM, CB."}
                               :min_overall {:type "integer" :description "Minimum FIFA overall rating."}
                               :max_age {:type "integer" :description "Maximum age."}
                               :limit {:type "integer" :description "Max players to list (default 10)."}}
                  :required []}
    :handler t-search-players}

   {:name "get_player"
    :description "Detailed profile of a single player from the FIFA database: ratings, club, position, physical attributes and top skills."
    :inputSchema {:type "object"
                  :properties {:name {:type "string" :description "Player name, e.g. \"Neymar Jr\"."}}
                  :required ["name"]}
    :handler t-get-player}

   {:name "get_extended_match_stats"
    :description "Average corners, shots and attacks for a team, from the BR-Football extended dataset (Série A/B/C and Copa do Brasil, 2014-2023), plus recent matches."
    :inputSchema {:type "object"
                  :properties {:team team-prop
                               :opponent (assoc team-prop :description "Optional opposing team filter.")
                               :competition competition-prop
                               :season season-prop
                               :limit {:type "integer" :description "Max matches to list (default 10)."}}
                  :required ["team"]}
    :handler t-extended-stats}

   {:name "list_competitions"
    :description "Lists the competitions covered by the dataset with match counts and season ranges."
    :inputSchema {:type "object" :properties {} :required []}
    :handler t-list-competitions}])

(def tool-index (into {} (map (juxt :name identity)) tools))

(defn list-tools
  "Tool descriptors for the MCP tools/list response."
  []
  (mapv #(select-keys % [:name :description :inputSchema]) tools))

(defn call-tool
  "Executes a tool by name. Returns the MCP tools/call result map."
  [db tool-name args]
  (if-let [{:keys [handler]} (tool-index tool-name)]
    (try
      {:content [{:type "text" :text (handler db (or args {}))}]
       :isError false}
      (catch Exception e
        {:content [{:type "text" :text (str "Error executing " tool-name ": " (ex-message e))}]
         :isError true}))
    {:content [{:type "text" :text (str "Unknown tool: " tool-name)}]
     :isError true}))
