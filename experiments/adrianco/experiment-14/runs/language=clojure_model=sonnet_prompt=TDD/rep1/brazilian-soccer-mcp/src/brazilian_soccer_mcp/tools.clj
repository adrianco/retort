(ns brazilian-soccer-mcp.tools
  (:require [clojure.string :as str]
            [brazilian-soccer-mcp.queries :as q]
            [brazilian-soccer-mcp.players :as p]
            [brazilian-soccer-mcp.normalization :as norm]))

(defn- param
  "Get a parameter by string or keyword key (handles both JSON decoded forms)."
  [params k]
  (let [sk (if (keyword? k) (name k) (str k))
        kk (keyword sk)]
    (or (get params sk) (get params kk))))

(defn- format-date [d]
  (when d (str d)))

(defn- format-match [m]
  (let [date  (format-date (:date m))
        comp  (or (:competition m) "")
        round (when (:round m) (str " Round " (:round m)))
        stage (when (:stage m) (str " [" (:stage m) "]"))]
    (str date ": " (:home-team m) " " (:home-goal m) "-" (:away-goal m)
         " " (:away-team m) " (" comp (or round stage "") ")")))

(defn call-find-matches
  "Executes the find_matches tool. Returns formatted string."
  [matches params]
  (let [team        (param params "team")
        team1       (param params "team1")
        team2       (param params "team2")
        season      (when-let [s (param params "season")] (Integer/parseInt (str s)))
        competition (param params "competition")
        date-from   (param params "date_from")
        date-to     (param params "date_to")
        criteria    (cond-> {}
                      team        (assoc :team team)
                      team1       (assoc :team1 team1)
                      team2       (assoc :team2 team2)
                      season      (assoc :season season)
                      competition (assoc :competition competition)
                      date-from   (assoc :date-from date-from)
                      date-to     (assoc :date-to date-to))
        results     (q/find-matches matches criteria)
        n           (count results)]
    (if (zero? n)
      (str "No matches found" (when team (str " for " team)) ".")
      (let [header (if (and team1 team2)
                     (str team1 " vs " team2 " - Head-to-Head (" n " matches)")
                     (str (or team "All teams") " - " n " match" (when (> n 1) "es") " found"))
            lines  (map format-match (take 20 results))
            footer (when (> n 20)
                     (str "\n... and " (- n 20) " more matches."))]
        (str header "\n\n" (str/join "\n" lines) footer)))))

(defn call-team-stats
  "Returns formatted team statistics string."
  [matches team-name season competition]
  (let [criteria (cond-> {}
                   season      (assoc :season season)
                   competition (assoc :competition competition))
        filtered (if (or season competition)
                   (q/find-matches matches criteria)
                   matches)
        stats    (q/calculate-team-stats filtered team-name)]
    (if (zero? (:matches stats))
      (str "No matches found for " team-name
           (when season (str " in " season))
           (when competition (str " in " competition)) ".")
      (let [pct (if (pos? (:matches stats))
                  (format "%.1f" (* 100.0 (/ (:wins stats) (:matches stats))))
                  "0.0")]
        (str team-name " Statistics"
             (when season (str " (" season ")"))
             (when competition (str " [" competition "]"))
             "\n"
             "Matches: " (:matches stats) "\n"
             "Wins: " (:wins stats) " | Draws: " (:draws stats) " | Losses: " (:losses stats) "\n"
             "Goals For: " (:goals-for stats) " | Goals Against: " (:goals-against stats) "\n"
             "Win Rate: " pct "%")))))

(defn- format-player [rank p]
  (str rank ". " (:name p)
       " - Overall: " (:overall p)
       ", Pos: " (:position p)
       ", Club: " (:club p)
       ", Nat: " (:nationality p)
       ", Age: " (:age p)))

(defn call-find-players
  "Returns formatted player search results."
  [players params]
  (let [name        (param params "name")
        nationality (param params "nationality")
        club        (param params "club")
        position    (param params "position")
        limit       (or (when-let [l (param params "limit")] (Integer/parseInt (str l))) 20)
        criteria    (cond-> {:sort-by :overall :limit limit}
                      name        (assoc :name name)
                      nationality (assoc :nationality nationality)
                      club        (assoc :club club)
                      position    (assoc :position position))
        results     (p/find-players players criteria)
        n           (count results)]
    (if (zero? n)
      (str "No players found"
           (when name (str " matching '" name "'"))
           (when nationality (str " from " nationality))
           (when club (str " at " club)) ".")
      (let [header (str "Players found: " n
                        (when nationality (str " | Nationality: " nationality))
                        (when club (str " | Club: " club)))
            lines  (map-indexed (fn [i p] (format-player (inc i) p)) results)]
        (str header "\n\n" (str/join "\n" lines))))))

(defn call-standings
  "Returns formatted league standings."
  [matches season competition]
  (let [criteria (cond-> {}
                   season      (assoc :season season)
                   competition (assoc :competition competition))
        filtered (if (or season competition)
                   (q/find-matches matches criteria)
                   matches)
        standings (q/calculate-standings filtered)
        header   (str "Standings"
                      (when season (str " - " season))
                      (when competition (str " [" competition "]")))]
    (str header "\n\n"
         (str/join "\n"
                   (map-indexed
                    (fn [i s]
                      (format "%2d. %-25s %3d pts  %2dW %2dD %2dL  GF:%2d GA:%2d GD:%+d"
                              (inc i) (:team s) (:points s)
                              (:wins s) (:draws s) (:losses s)
                              (:goals-for s) (:goals-against s) (:goal-diff s)))
                    (take 25 standings))))))

(defn call-biggest-wins
  "Returns formatted biggest wins."
  [matches n]
  (let [wins (q/biggest-wins matches (or n 10))
        header (str "Biggest Wins (Top " (count wins) ")")]
    (str header "\n\n"
         (str/join "\n"
                   (map-indexed
                    (fn [i m]
                      (let [diff (Math/abs (int (- (:home-goal m) (:away-goal m))))]
                        (str (inc i) ". " (format-date (:date m)) ": "
                             (:home-team m) " " (:home-goal m) "-" (:away-goal m)
                             " " (:away-team m)
                             " (margin: " diff ", " (:competition m) ")")))
                    wins)))))

(defn call-head-to-head
  "Returns formatted head-to-head stats."
  [matches team1 team2]
  (let [stats (q/head-to-head-stats matches team1 team2)
        h2h   (q/find-matches matches {:team1 team1 :team2 team2})]
    (if (zero? (:total stats))
      (str "No matches found between " team1 " and " team2 ".")
      (str team1 " vs " team2 " Head-to-Head\n\n"
           "Total Meetings: " (:total stats) "\n"
           team1 " Wins: " (:team1-wins stats) "\n"
           "Draws: " (:draws stats) "\n"
           team2 " Wins: " (:team2-wins stats) "\n\n"
           "Match History:\n"
           (str/join "\n" (map format-match (take 20 h2h)))))))

(defn list-tools
  "Returns the MCP tool definitions."
  []
  [{:name "find_matches"
    :description "Search for matches by team, season, competition, date range, or head-to-head between two teams."
    :inputSchema {:type "object"
                  :properties {"team"        {:type "string" :description "Team name to search (home or away)"}
                               "team1"       {:type "string" :description "First team for head-to-head search"}
                               "team2"       {:type "string" :description "Second team for head-to-head search"}
                               "season"      {:type "integer" :description "Season year (e.g. 2023)"}
                               "competition" {:type "string" :description "Competition: brasileirao, copa-do-brasil, libertadores"}
                               "date_from"   {:type "string" :description "Start date (YYYY-MM-DD)"}
                               "date_to"     {:type "string" :description "End date (YYYY-MM-DD)"}}}}
   {:name "team_stats"
    :description "Get win/loss/draw statistics, goals scored and conceded for a team, optionally filtered by season and competition."
    :inputSchema {:type "object"
                  :required ["team"]
                  :properties {"team"        {:type "string" :description "Team name"}
                               "season"      {:type "integer" :description "Filter by season year"}
                               "competition" {:type "string" :description "Filter by competition"}}}}
   {:name "find_players"
    :description "Search for players by name, nationality, club, or position. Returns FIFA ratings and attributes."
    :inputSchema {:type "object"
                  :properties {"name"        {:type "string" :description "Player name (partial match)"}
                               "nationality" {:type "string" :description "Player nationality (e.g. Brazil)"}
                               "club"        {:type "string" :description "Club name (partial match)"}
                               "position"    {:type "string" :description "Position (GK, ST, LW, CAM, etc.)"}
                               "limit"       {:type "integer" :description "Max results (default 20)"}}}}
   {:name "standings"
    :description "Calculate league standings from match results, optionally filtered by season and competition."
    :inputSchema {:type "object"
                  :properties {"season"      {:type "integer" :description "Season year"}
                               "competition" {:type "string" :description "Competition name"}}}}
   {:name "biggest_wins"
    :description "Find the biggest winning margins in the dataset."
    :inputSchema {:type "object"
                  :properties {"n"           {:type "integer" :description "Number of results (default 10)"}
                               "competition" {:type "string" :description "Filter by competition"}
                               "season"      {:type "integer" :description "Filter by season"}}}}
   {:name "head_to_head"
    :description "Get head-to-head record and match history between two teams."
    :inputSchema {:type "object"
                  :required ["team1" "team2"]
                  :properties {"team1" {:type "string" :description "First team name"}
                               "team2" {:type "string" :description "Second team name"}
                               "season" {:type "integer" :description "Filter by season"}}}}])
