(ns brazilian-soccer-mcp.tools
  (:require [clojure.string :as str]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.normalize :as norm]))

;; ── Helpers ───────────────────────────────────────────────────────────────────

(defn- parse-comp-key [s]
  (when s
    (case (str/lower-case (str/trim s))
      ("brasileirao" "serie-a" "serie a" "brasileirão") :brasileirao
      ("copa-brasil" "copa do brasil" "copa brasil")    :copa-brasil
      ("libertadores" "copa libertadores")               :libertadores
      ("historico" "histórico" "historical")             :historico
      ("br-football" "br football" "extended")           :br-football
      nil)))

(defn- filter-matches
  "Filter matches collection by optional criteria map."
  [matches {:keys [team opponent season date-from date-to]}]
  (cond->> matches
    team      (filter (fn [m]
                        (or (norm/team-matches? (:home-team m) team)
                            (norm/team-matches? (:away-team m) team))))
    opponent  (filter (fn [m]
                        (or (norm/team-matches? (:home-team m) opponent)
                            (norm/team-matches? (:away-team m) opponent))))
    season    (filter (fn [m] (= (:season m) season)))
    date-from (filter (fn [m] (and (:date m) (>= (compare (:date m) date-from) 0))))
    date-to   (filter (fn [m] (and (:date m) (<= (compare (:date m) date-to) 0))))))

(defn- sort-matches-desc [matches]
  (sort-by :date #(compare %2 %1) matches))

(defn- goal-diff [m]
  (when (and (:home-goals m) (:away-goals m))
    (Math/abs (- (:home-goals m) (:away-goals m)))))

(defn- winner [m]
  (cond
    (nil? (:home-goals m)) nil
    (nil? (:away-goals m)) nil
    (> (:home-goals m) (:away-goals m)) :home
    (< (:home-goals m) (:away-goals m)) :away
    :else :draw))

;; ── Tool: search_matches ──────────────────────────────────────────────────────

(defn search-matches [args]
  (let [team      (get args "team")
        opponent  (get args "opponent")
        comp-str  (get args "competition")
        season    (some-> (get args "season") norm/parse-int)
        date-from (get args "date_from")
        date-to   (get args "date_to")
        limit     (or (some-> (get args "limit") norm/parse-int) 20)
        comp-key  (parse-comp-key comp-str)
        source    (if comp-key
                    (data/matches-for-competition comp-key)
                    (data/get-all-matches))
        criteria  {:team team :opponent opponent :season season
                   :date-from date-from :date-to date-to}
        filtered  (filter-matches source criteria)
        sorted    (sort-matches-desc filtered)
        total     (count sorted)
        displayed (take limit sorted)]
    (if (zero? total)
      (str "No matches found" (when team (str " for " team))
           (when opponent (str " vs " opponent))
           (when season (str " in " season)) ".")
      (str/join "\n"
                (concat
                 [(str "Found " total " match" (when (> total 1) "es")
                       (when team (str " involving " team))
                       (when opponent (str " vs " opponent))
                       (when season (str " in season " season))
                       (when comp-str (str " in " comp-str))
                       ":"
                       (when (> total limit) (str " (showing first " limit ")")))]
                 [""]
                 (map norm/match-result-line displayed)
                 (when (> total limit)
                   [(str "\n... and " (- total limit) " more matches.")]))))))

;; ── Tool: get_team_stats ──────────────────────────────────────────────────────

(defn- calc-stats
  "Calculate W/D/L/GF/GA from a sequence of matches for a given team."
  [matches team]
  (reduce (fn [acc m]
            (let [home? (norm/team-matches? (:home-team m) team)
                  away? (norm/team-matches? (:away-team m) team)
                  hg    (:home-goals m)
                  ag    (:away-goals m)]
              (if (and (or home? away?) hg ag)
                (let [my-goals    (if home? hg ag)
                      their-goals (if home? ag hg)
                      result      (cond (> hg ag) (if home? :win :loss)
                                        (< hg ag) (if home? :loss :win)
                                        :else :draw)]
                  (-> acc
                      (update :played inc)
                      (update result inc)
                      (update :gf + my-goals)
                      (update :ga + their-goals)))
                acc)))
          {:played 0 :win 0 :draw 0 :loss 0 :gf 0 :ga 0}
          matches))

(defn get-team-stats [args]
  (let [team     (get args "team")
        comp-str (get args "competition")
        season   (some-> (get args "season") norm/parse-int)
        venue    (get args "venue" "both")]
    (when-not team
      (throw (ex-info "team parameter is required" {})))
    (let [comp-key (parse-comp-key comp-str)
          source   (if comp-key
                     (data/matches-for-competition comp-key)
                     (data/get-all-matches))
          filtered (cond->> source
                     season (filter #(= (:season %) season))
                     (= venue "home") (filter #(norm/team-matches? (:home-team %) team))
                     (= venue "away") (filter #(norm/team-matches? (:away-team %) team))
                     true (filter #(or (norm/team-matches? (:home-team %) team)
                                       (norm/team-matches? (:away-team %) team))))
          stats    (calc-stats filtered team)
          pts      (+ (* 3 (:win stats)) (:draw stats))
          gd       (- (:gf stats) (:ga stats))
          win-rate (if (pos? (:played stats))
                     (double (/ (:win stats) (:played stats)))
                     0.0)
          comp-label (if comp-str comp-str "all competitions")
          season-label (if season (str season " ") "")]
      (if (zero? (:played stats))
        (str "No matches found for " team
             (when season (str " in " season))
             (when comp-str (str " in " comp-str)) ".")
        (str/join "\n"
                  [(str team " Statistics (" season-label comp-label "):")
                   (str "  Matches played: " (:played stats))
                   (str "  Wins: " (:win stats)
                        ", Draws: " (:draw stats)
                        ", Losses: " (:loss stats))
                   (str "  Goals For: " (:gf stats)
                        ", Goals Against: " (:ga stats)
                        ", Goal Difference: " (if (>= gd 0) (str "+" gd) (str gd)))
                   (str "  Win rate: " (format "%.1f%%" (* 100 win-rate)))
                   (str "  Points (3W+1D): " pts)])))))

;; ── Tool: search_players ─────────────────────────────────────────────────────

(defn search-players [args]
  (let [name-q      (some-> (get args "name") str/lower-case)
        nationality (some-> (get args "nationality") str/lower-case)
        club-q      (some-> (get args "club") str/lower-case)
        min-overall (some-> (get args "min_overall") norm/parse-int)
        max-overall (some-> (get args "max_overall") norm/parse-int)
        position    (some-> (get args "position") str/upper-case)
        limit       (or (some-> (get args "limit") norm/parse-int) 20)
        players     (data/get-fifa)
        filtered    (cond->> players
                      name-q      (filter #(when (:name %)
                                             (str/includes?
                                              (str/lower-case (:name %)) name-q)))
                      nationality (filter #(when (:nationality %)
                                             (str/includes?
                                              (str/lower-case (:nationality %)) nationality)))
                      club-q      (filter #(when (:club %)
                                             (str/includes?
                                              (str/lower-case (:club %)) club-q)))
                      min-overall (filter #(and (:overall %) (>= (:overall %) min-overall)))
                      max-overall (filter #(and (:overall %) (<= (:overall %) max-overall)))
                      position    (filter #(when (:position %)
                                             (str/includes?
                                              (str/upper-case (:position %)) position))))
        sorted      (sort-by #(- (or (:overall %) 0)) filtered)
        total       (count sorted)
        displayed   (take limit sorted)]
    (if (zero? total)
      "No players found matching the given criteria."
      (str/join "\n"
                (concat
                 [(str "Found " total " player" (when (> total 1) "s")
                       (when (> total limit) (str " (showing top " limit " by rating)")) ":")]
                 [""]
                 (map-indexed
                  (fn [i p]
                    (str (format "%3d. " (inc i))
                         (:name p)
                         (when (:nationality p) (str " (" (:nationality p) ")"))
                         " - Overall: " (or (:overall p) "?")
                         (when (:potential p) (str ", Potential: " (:potential p)))
                         ", Position: " (or (:position p) "?")
                         ", Club: " (or (:club p) "?")
                         (when (:age p) (str "\n      Age: " (:age p)))
                         (when (:wage p) (str ", Wage: " (:wage p)))))
                  displayed)
                 (when (> total limit)
                   [(str "\n... and " (- total limit) " more players.")]))))))

;; ── Tool: get_standings ───────────────────────────────────────────────────────

(defn- build-standings [matches]
  ;; Use raw team names as keys — within a single dataset the naming is consistent,
  ;; and normalization would incorrectly merge e.g. "Atletico-MG" with "Atletico-PR".
  (let [teams (reduce (fn [acc m]
                        (let [hg (:home-goals m)
                              ag (:away-goals m)
                              ht (:home-team m)
                              at (:away-team m)]
                          (if (and ht at hg ag)
                            (let [result (cond (> hg ag) [:home-win :away-loss]
                                               (< hg ag) [:home-loss :away-win]
                                               :else      [:draw :draw])]
                              (-> acc
                                  (update ht (fnil identity {:team ht :mp 0 :w 0 :d 0 :l 0 :gf 0 :ga 0}))
                                  (update at (fnil identity {:team at :mp 0 :w 0 :d 0 :l 0 :gf 0 :ga 0}))
                                  (update ht #(-> %
                                                  (update :mp inc)
                                                  (update :gf + hg)
                                                  (update :ga + ag)
                                                  (update :w + (if (= (first result) :home-win) 1 0))
                                                  (update :d + (if (= (first result) :draw) 1 0))
                                                  (update :l + (if (= (first result) :home-loss) 1 0))))
                                  (update at #(-> %
                                                  (update :mp inc)
                                                  (update :gf + ag)
                                                  (update :ga + hg)
                                                  (update :w + (if (= (second result) :away-win) 1 0))
                                                  (update :d + (if (= (second result) :draw) 1 0))
                                                  (update :l + (if (= (second result) :away-loss) 1 0))))))
                            acc)))
                      {} matches)]
    (->> (vals teams)
         (map #(assoc % :pts (+ (* 3 (:w %)) (:d %))
                        :gd  (- (:gf %) (:ga %))))
         (sort-by (juxt #(- (:pts %)) #(- (:gd %)) #(- (:gf %)))))))

(defn get-standings [args]
  (let [season   (some-> (get args "season") norm/parse-int)
        comp-str (get args "competition" "brasileirao")
        comp-key (or (parse-comp-key comp-str) :brasileirao)]
    (when-not season
      (throw (ex-info "season parameter is required" {})))
    (let [source   (case comp-key
                     ;; Use brasileirao for 2012+, historico for pre-2012
                     :brasileirao          (if (and season (< season 2012))
                                             (data/get-historico)
                                             (data/get-brasileirao))
                     :brasileirao-historico (data/get-historico)
                     (data/matches-for-competition comp-key))
          filtered (filter #(= (:season %) season) source)
          standings (build-standings filtered)]
      (if (empty? standings)
        (str "No standings data found for " season " " comp-str ".")
        (str/join "\n"
                  (concat
                   [(str season " " (norm/competition-label comp-key) " Standings")
                    "(calculated from match results)"
                    ""
                    (format "%-4s %-25s %4s %4s %4s %4s %4s %4s %5s %4s"
                            "Pos" "Team" "MP" "W" "D" "L" "GF" "GA" "GD" "Pts")
                    (str/join "" (repeat 70 "-"))]
                   (map-indexed
                    (fn [i row]
                      (format "%-4s %-25s %4d %4d %4d %4d %4d %4d %5s %4d"
                              (str (inc i))
                              (subs (or (:team row) "?") 0 (min 25 (count (or (:team row) "?"))))
                              (:mp row)
                              (:w row)
                              (:d row)
                              (:l row)
                              (:gf row)
                              (:ga row)
                              (let [gd (:gd row)]
                                (if (>= gd 0) (str "+" gd) (str gd)))
                              (:pts row)))
                    standings)))))))

;; ── Tool: get_head_to_head ────────────────────────────────────────────────────

(defn get-head-to-head [args]
  (let [team1    (get args "team1")
        team2    (get args "team2")
        comp-str (get args "competition")
        season   (some-> (get args "season") norm/parse-int)
        limit    (or (some-> (get args "limit") norm/parse-int) 20)]
    (when-not (and team1 team2)
      (throw (ex-info "team1 and team2 parameters are required" {})))
    (let [comp-key (parse-comp-key comp-str)
          source   (if comp-key
                     (data/matches-for-competition comp-key)
                     (data/get-all-matches))
          h2h      (cond->> source
                     season (filter #(= (:season %) season))
                     true   (filter (fn [m]
                                      (or (and (norm/team-matches? (:home-team m) team1)
                                               (norm/team-matches? (:away-team m) team2))
                                          (and (norm/team-matches? (:home-team m) team2)
                                               (norm/team-matches? (:away-team m) team1))))))
          sorted   (sort-matches-desc h2h)
          total    (count sorted)
          t1-wins  (count (filter (fn [m]
                                    (let [w (winner m)]
                                      (or (and (= w :home) (norm/team-matches? (:home-team m) team1))
                                          (and (= w :away) (norm/team-matches? (:away-team m) team1))))) h2h))
          t2-wins  (count (filter (fn [m]
                                    (let [w (winner m)]
                                      (or (and (= w :home) (norm/team-matches? (:home-team m) team2))
                                          (and (= w :away) (norm/team-matches? (:away-team m) team2))))) h2h))
          draws    (- total t1-wins t2-wins)]
      (if (zero? total)
        (str "No matches found between " team1 " and " team2
             (when season (str " in " season)) ".")
        (str/join "\n"
                  (concat
                   [(str "Head-to-Head: " team1 " vs " team2)
                    ""
                    (str "Total matches: " total
                         (when season (str " (in " season ")"))
                         (when comp-str (str " in " comp-str)))
                    (str "  " team1 " wins: " t1-wins)
                    (str "  " team2 " wins: " t2-wins)
                    (str "  Draws: " draws)
                    ""
                    (str "Matches (most recent first"
                         (when (> total limit) (str ", showing " limit))
                         "):")]
                   (map norm/match-result-line (take limit sorted))
                   (when (> total limit)
                     [(str "\n... and " (- total limit) " more matches.")])))))))

;; ── Tool: get_biggest_wins ────────────────────────────────────────────────────

(defn get-biggest-wins [args]
  (let [team     (get args "team")
        comp-str (get args "competition")
        season   (some-> (get args "season") norm/parse-int)
        limit    (or (some-> (get args "limit") norm/parse-int) 10)
        comp-key (parse-comp-key comp-str)
        source   (if comp-key
                   (data/matches-for-competition comp-key)
                   (data/get-all-matches))
        filtered (cond->> source
                   season (filter #(= (:season %) season))
                   team   (filter #(or (norm/team-matches? (:home-team %) team)
                                       (norm/team-matches? (:away-team %) team)))
                   true   (filter #(and (:home-goals %) (:away-goals %))))
        sorted   (sort-by #(- (goal-diff %)) filtered)
        total    (count sorted)
        displayed (take limit sorted)]
    (if (zero? total)
      "No match data found with the given criteria."
      (str/join "\n"
                (concat
                 [(str "Biggest victories"
                       (when team (str " involving " team))
                       (when season (str " in " season))
                       (when comp-str (str " (" comp-str ")"))
                       ":"
                       (when (> total limit) (str " (showing top " limit ")")))]
                 [""]
                 (map-indexed
                  (fn [i m]
                    (str (format "%3d. " (inc i))
                         (norm/match-result-line m)
                         (format " [diff: %d]" (goal-diff m))))
                  displayed)
                 (when (> total limit)
                   [(str "\n... and " (- total limit) " more matches.")]))))))

;; ── Tool: get_competition_stats ───────────────────────────────────────────────

(defn get-competition-stats [args]
  (let [comp-str (get args "competition")
        season   (some-> (get args "season") norm/parse-int)
        comp-key (parse-comp-key comp-str)
        source   (if comp-key
                   (data/matches-for-competition comp-key)
                   (data/get-all-matches))
        filtered (cond->> source
                   season (filter #(= (:season %) season))
                   true   (filter #(and (:home-goals %) (:away-goals %))))
        total    (count filtered)]
    (if (zero? total)
      (str "No match data found"
           (when comp-str (str " for " comp-str))
           (when season (str " in " season)) ".")
      (let [total-goals (reduce + 0 (map #(+ (:home-goals %) (:away-goals %)) filtered))
            home-wins   (count (filter #(> (:home-goals %) (:away-goals %)) filtered))
            draws       (count (filter #(= (:home-goals %) (:away-goals %)) filtered))
            away-wins   (count (filter #(< (:home-goals %) (:away-goals %)) filtered))
            avg-goals   (double (/ total-goals total))
            biggest     (->> filtered
                              (sort-by #(- (goal-diff %)))
                              first)]
        (str/join "\n"
                  [(str (if comp-str comp-str "All competitions")
                        (if season (str " " season) "")
                        " Summary:")
                   (str "  Total matches: " total)
                   (str "  Total goals: " total-goals)
                   (str "  Goals per match: " (format "%.2f" avg-goals))
                   (str "  Home wins: " home-wins " (" (format "%.1f%%" (* 100.0 (/ home-wins total))) ")")
                   (str "  Draws: " draws " (" (format "%.1f%%" (* 100.0 (/ draws total))) ")")
                   (str "  Away wins: " away-wins " (" (format "%.1f%%" (* 100.0 (/ away-wins total))) ")")
                   (str "  Biggest victory: " (norm/match-result-line biggest)
                        " [diff: " (goal-diff biggest) "]")])))))

;; ── Tool registry ─────────────────────────────────────────────────────────────

(def tool-definitions
  [{"name"        "search_matches"
    "description" "Search for soccer matches across all Brazilian competitions. Supports filtering by team, opponent, competition, season, and date range. Competitions: 'brasileirao', 'copa-brasil', 'libertadores', 'historico', 'br-football', or 'all' (default)."
    "inputSchema" {"type"       "object"
                   "properties" {"team"        {"type" "string"  "description" "Team name (partial match, accent-insensitive)"}
                                 "opponent"    {"type" "string"  "description" "Opponent team name for head-to-head search"}
                                 "competition" {"type" "string"  "description" "Competition filter: brasileirao, copa-brasil, libertadores, historico, or all"}
                                 "season"      {"type" "integer" "description" "Season year (e.g. 2023)"}
                                 "date_from"   {"type" "string"  "description" "Start date YYYY-MM-DD"}
                                 "date_to"     {"type" "string"  "description" "End date YYYY-MM-DD"}
                                 "limit"       {"type" "integer" "description" "Max results (default 20)"}}
                   "required"   []}}

   {"name"        "get_team_stats"
    "description" "Get win/draw/loss record and goals statistics for a team, optionally filtered by competition and season."
    "inputSchema" {"type"       "object"
                   "properties" {"team"        {"type" "string"  "description" "Team name (required)"}
                                 "competition" {"type" "string"  "description" "Competition filter"}
                                 "season"      {"type" "integer" "description" "Season year"}
                                 "venue"       {"type" "string"  "description" "home, away, or both (default)"}}
                   "required"   ["team"]}}

   {"name"        "search_players"
    "description" "Search FIFA player database by name, nationality, club, position, or rating."
    "inputSchema" {"type"       "object"
                   "properties" {"name"        {"type" "string"  "description" "Player name (partial match)"}
                                 "nationality" {"type" "string"  "description" "Player nationality (e.g. Brazil)"}
                                 "club"        {"type" "string"  "description" "Club name (partial match)"}
                                 "min_overall" {"type" "integer" "description" "Minimum FIFA overall rating"}
                                 "max_overall" {"type" "integer" "description" "Maximum FIFA overall rating"}
                                 "position"    {"type" "string"  "description" "Position (e.g. ST, GK, CB, LW)"}
                                 "limit"       {"type" "integer" "description" "Max results (default 20)"}}
                   "required"   []}}

   {"name"        "get_standings"
    "description" "Calculate league standings for a given season from match results. Returns table with points, wins, draws, losses, goals."
    "inputSchema" {"type"       "object"
                   "properties" {"season"      {"type" "integer" "description" "Season year (required)"}
                                 "competition" {"type" "string"  "description" "Competition (default: brasileirao)"}}
                   "required"   ["season"]}}

   {"name"        "get_head_to_head"
    "description" "Show all matches between two teams with aggregate win/draw/loss record."
    "inputSchema" {"type"       "object"
                   "properties" {"team1"       {"type" "string"  "description" "First team name (required)"}
                                 "team2"       {"type" "string"  "description" "Second team name (required)"}
                                 "competition" {"type" "string"  "description" "Optional competition filter"}
                                 "season"      {"type" "integer" "description" "Optional season filter"}
                                 "limit"       {"type" "integer" "description" "Max matches to show (default 20)"}}
                   "required"   ["team1" "team2"]}}

   {"name"        "get_biggest_wins"
    "description" "Find matches with the largest goal margin. Can filter by team, competition, or season."
    "inputSchema" {"type"       "object"
                   "properties" {"team"        {"type" "string"  "description" "Optional team filter"}
                                 "competition" {"type" "string"  "description" "Optional competition filter"}
                                 "season"      {"type" "integer" "description" "Optional season filter"}
                                 "limit"       {"type" "integer" "description" "Max results (default 10)"}}
                   "required"   []}}

   {"name"        "get_competition_stats"
    "description" "Get aggregate statistics for a competition/season: total matches, goals per game, home win rate, etc."
    "inputSchema" {"type"       "object"
                   "properties" {"competition" {"type" "string"  "description" "Competition name (or omit for all)"}
                                 "season"      {"type" "integer" "description" "Season year (or omit for all years)"}}
                   "required"   []}}])

(defn call-tool
  "Dispatch a tool call by name with the given arguments map."
  [tool-name arguments]
  (case tool-name
    "search_matches"       (search-matches arguments)
    "get_team_stats"       (get-team-stats arguments)
    "search_players"       (search-players arguments)
    "get_standings"        (get-standings arguments)
    "get_head_to_head"     (get-head-to-head arguments)
    "get_biggest_wins"     (get-biggest-wins arguments)
    "get_competition_stats" (get-competition-stats arguments)
    (throw (ex-info (str "Unknown tool: " tool-name) {:tool tool-name}))))
