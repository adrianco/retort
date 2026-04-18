(ns brazilian-soccer-mcp.tools
  (:require [brazilian-soccer-mcp.data :as data]
            [clojure.string :as str]))

;;; ─── Formatting helpers ──────────────────────────────────────────────────────

(defn- fmt-match [m]
  (format "%s: %s %d-%d %s (%s%s)"
          (or (:date m) "?")
          (or (:raw-home m) (:home-team m) "?")
          (or (:home-goals m) 0)
          (or (:away-goals m) 0)
          (or (:raw-away m) (:away-team m) "?")
          (or (:competition m) "?")
          (if (:round m) (str " Round " (:round m)) "")))

(defn- fmt-player [i p]
  (format "%d. %s - Overall: %s, Position: %s, Club: %s, Nationality: %s"
          (inc i)
          (or (:name p) "Unknown")
          (or (:overall p) "?")
          (or (:position p) "?")
          (or (:club p) "?")
          (or (:nationality p) "?")))

;;; ─── Tool definitions ────────────────────────────────────────────────────────

(def tools
  [{:name        "search_matches"
    :description "Search for soccer matches by team, season, competition, or date. Returns a list of matches with scores."
    :inputSchema {:type       "object"
                  :properties {:team        {:type "string" :description "Team name to search for (matches either home or away)"}
                               :home_team   {:type "string" :description "Search specifically for home team"}
                               :away_team   {:type "string" :description "Search specifically for away team"}
                               :season      {:type "integer" :description "Season year (e.g. 2023)"}
                               :competition {:type "string" :description "Competition name substring (e.g. 'Brasileirao', 'Copa do Brasil', 'Libertadores')"}
                               :limit       {:type "integer" :description "Maximum number of results to return (default 50)"}}
                  :required   []}}
   {:name        "get_head_to_head"
    :description "Get head-to-head match history and statistics between two teams."
    :inputSchema {:type       "object"
                  :properties {:team_a {:type "string" :description "First team name"}
                               :team_b {:type "string" :description "Second team name"}
                               :limit  {:type "integer" :description "Maximum number of matches to show (default 20)"}}
                  :required   ["team_a" "team_b"]}}
   {:name        "get_team_stats"
    :description "Get win/loss/draw record and goals statistics for a team, optionally filtered by season and competition."
    :inputSchema {:type       "object"
                  :properties {:team        {:type "string" :description "Team name"}
                               :season      {:type "integer" :description "Season year (optional)"}
                               :competition {:type "string" :description "Competition name substring (optional)"}}
                  :required   ["team"]}}
   {:name        "get_standings"
    :description "Calculate league standings for a competition and season based on match results."
    :inputSchema {:type       "object"
                  :properties {:season      {:type "integer" :description "Season year (e.g. 2023)"}
                               :competition {:type "string" :description "Competition name (e.g. 'Brasileirao')"}}
                  :required   ["season" "competition"]}}
   {:name        "search_players"
    :description "Search FIFA player database by name, nationality, club, position, or minimum rating."
    :inputSchema {:type       "object"
                  :properties {:name        {:type "string" :description "Player name substring"}
                               :nationality {:type "string" :description "Player nationality (e.g. 'Brazil')"}
                               :club        {:type "string" :description "Club name substring (e.g. 'Flamengo')"}
                               :position    {:type "string" :description "Playing position (e.g. 'ST', 'GK', 'CB')"}
                               :min_overall {:type "integer" :description "Minimum overall rating (e.g. 80)"}
                               :limit       {:type "integer" :description "Maximum results (default 50)"}}
                  :required   []}}
   {:name        "get_biggest_wins"
    :description "Find matches with the largest goal difference (biggest victories)."
    :inputSchema {:type       "object"
                  :properties {:team        {:type "string" :description "Filter by team (optional)"}
                               :season      {:type "integer" :description "Filter by season year (optional)"}
                               :competition {:type "string" :description "Filter by competition (optional)"}
                               :limit       {:type "integer" :description "Number of results (default 20)"}}
                  :required   []}}
   {:name        "get_global_stats"
    :description "Get aggregate statistics across all matches: average goals, home/away win rates, etc."
    :inputSchema {:type       "object"
                  :properties {:competition {:type "string" :description "Filter by competition (optional)"}
                               :season      {:type "integer" :description "Filter by season year (optional)"}}
                  :required   []}}])

;;; ─── Tool dispatch ───────────────────────────────────────────────────────────

(defmulti call-tool (fn [name _args] name))

(defmethod call-tool "search_matches" [_ args]
  (let [limit   (or (get args "limit") 50)
        matches (data/search-matches
                 {:team        (get args "team")
                  :home-team   (get args "home_team")
                  :away-team   (get args "away_team")
                  :season      (some-> (get args "season") int)
                  :competition (get args "competition")
                  :limit       limit})]
    (if (empty? matches)
      "No matches found for the given criteria."
      (str "Found " (count matches) " match(es):\n\n"
           (str/join "\n" (map fmt-match matches))))))

(defmethod call-tool "get_head_to_head" [_ args]
  (let [team-a  (get args "team_a")
        team-b  (get args "team_b")
        limit   (or (get args "limit") 20)
        matches (take limit (data/head-to-head team-a team-b))
        stats   (data/head-to-head-stats team-a team-b)]
    (if (empty? matches)
      (format "No head-to-head matches found between %s and %s." team-a team-b)
      (str (format "Head-to-head: %s vs %s\n\n" team-a team-b)
           (format "Summary: %d matches | %s wins: %d | %s wins: %d | Draws: %d\n\n"
                   (:total-matches stats)
                   team-a (:team-a-wins stats)
                   team-b (:team-b-wins stats)
                   (:draws stats))
           "Recent matches:\n"
           (str/join "\n" (map fmt-match (reverse matches)))))))

(defmethod call-tool "get_team_stats" [_ args]
  (let [team   (get args "team")
        season (some-> (get args "season") int)
        comp   (get args "competition")
        stats  (data/team-stats {:team team :season season :competition comp})
        pts    (data/team-points stats)]
    (format "Statistics for %s%s%s:\n  Matches: %d\n  Wins: %d | Draws: %d | Losses: %d\n  Points: %d\n  Goals For: %d | Goals Against: %d | GD: %+d\n  Home: %d played, %d wins\n  Away: %d played, %d wins\n  Win rate: %.1f%%"
            team
            (if season (str " - Season " season) "")
            (if comp (str " - " comp) "")
            (:matches stats 0)
            (:win stats 0) (:draw stats 0) (:loss stats 0)
            pts
            (:goals-for stats 0) (:goals-against stats 0)
            (- (:goals-for stats 0) (:goals-against stats 0))
            (:home-matches stats 0) (:home-wins stats 0)
            (:away-matches stats 0) (:away-wins stats 0)
            (if (pos? (:matches stats 0))
              (* 100.0 (/ (:win stats 0) (double (:matches stats 0))))
              0.0))))

(defmethod call-tool "get_standings" [_ args]
  (let [season  (some-> (get args "season") int)
        comp    (get args "competition")
        table   (take 20 (data/competition-standings {:season season :competition comp}))]
    (if (empty? table)
      (format "No standings data found for %s %s." comp season)
      (str (format "Standings: %s %s (top %d teams)\n\n" comp season (count table))
           (str/join "\n"
                     (map (fn [s]
                            (format "%2d. %-25s %3d pts (%dW %dD %dL) GF:%d GA:%d GD:%+d"
                                    (:position s)
                                    (:team s)
                                    (data/team-points s)
                                    (:win s 0) (:draw s 0) (:loss s 0)
                                    (:goals-for s 0) (:goals-against s 0)
                                    (- (:goals-for s 0) (:goals-against s 0))))
                          table))))))

(defmethod call-tool "search_players" [_ args]
  (let [limit   (or (get args "limit") 50)
        players (data/search-players
                 {:name        (get args "name")
                  :nationality (get args "nationality")
                  :club        (get args "club")
                  :position    (get args "position")
                  :min-overall (some-> (get args "min_overall") int)
                  :limit       limit})]
    (if (empty? players)
      "No players found matching the given criteria."
      (str "Found " (count players) " player(s):\n\n"
           (str/join "\n" (map-indexed fmt-player players))))))

(defmethod call-tool "get_biggest_wins" [_ args]
  (let [limit   (or (get args "limit") 20)
        matches (data/biggest-wins
                 {:team        (get args "team")
                  :season      (some-> (get args "season") int)
                  :competition (get args "competition")
                  :limit       limit})]
    (if (empty? matches)
      "No matches found."
      (str "Biggest victories (by goal difference):\n\n"
           (str/join "\n"
                     (map-indexed
                      (fn [i m]
                        (format "%d. %s" (inc i) (fmt-match m)))
                      matches))))))

(defmethod call-tool "get_global_stats" [_ args]
  (let [stats (data/global-stats
               {:competition (get args "competition")
                :season      (some-> (get args "season") int)})]
    (if (zero? (:total-matches stats 0))
      "No match data found for given filters."
      (format "Global Statistics%s%s:\n  Total Matches: %d\n  Total Goals: %d\n  Avg Goals/Match: %.2f\n  Home Wins: %d (%.1f%%)\n  Away Wins: %d (%.1f%%)\n  Draws: %d (%.1f%%)"
              (if-let [c (get args "competition")] (str " - " c) "")
              (if-let [s (get args "season")] (str " " s) "")
              (:total-matches stats)
              (:total-goals stats)
              (:avg-goals-per-match stats)
              (:home-wins stats) (* 100.0 (:home-win-rate stats))
              (:away-wins stats) (* 100.0 (:away-win-rate stats))
              (:draws stats) (* 100.0 (:draw-rate stats))))))

(defmethod call-tool :default [name _args]
  (str "Unknown tool: " name))
