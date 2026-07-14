(ns soccer.tools
  "The catalogue of MCP tools exposed by the server.

   Each tool maps a category of natural-language question from the spec onto a
   query function in `soccer.query`.  A tool is {:name :description
   :inputSchema :handler}; the handler takes the loaded dataset and the parsed
   call arguments and returns the answer text."
  (:require [soccer.query :as query]))

(defn- s [type desc] {:type type :description desc})

(def tools
  [{:name "find_matches"
    :description (str "Find matches by team, opponent, competition, season or "
                      "date range. Provide both team and opponent for a "
                      "head-to-head listing.")
    :inputSchema
    {:type "object"
     :properties {:team (s "string" "Team name (any spelling, e.g. 'Flamengo').")
                  :opponent (s "string" "Opponent team name.")
                  :competition (s "string" "Brasileirão, Copa do Brasil or Copa Libertadores.")
                  :season (s "integer" "Season year, e.g. 2019.")
                  :start_date (s "string" "Inclusive ISO start date yyyy-MM-dd.")
                  :end_date (s "string" "Inclusive ISO end date yyyy-MM-dd.")
                  :limit (s "integer" "Maximum number of matches to return.")}}
    :handler (fn [ds a] (query/find-matches ds a))}

   {:name "team_stats"
    :description (str "A team's record (matches, wins/draws/losses, goals for "
                      "and against, win rate), optionally scoped by season, "
                      "competition and venue (home/away).")
    :inputSchema
    {:type "object"
     :properties {:team (s "string" "Team name (required).")
                  :season (s "integer" "Season year.")
                  :competition (s "string" "Competition name.")
                  :venue (s "string" "'home', 'away' or omit for all.")}
     :required ["team"]}
    :handler (fn [ds a] (query/team-stats ds a))}

   {:name "compare_teams"
    :description "Head-to-head record and match list between two teams."
    :inputSchema
    {:type "object"
     :properties {:team1 (s "string" "First team (required).")
                  :team2 (s "string" "Second team (required).")}
     :required ["team1" "team2"]}
    :handler (fn [ds a] (query/compare-teams ds a))}

   {:name "search_players"
    :description (str "Search the FIFA player database by name, nationality, "
                      "club or position; results are sorted by overall rating.")
    :inputSchema
    {:type "object"
     :properties {:name (s "string" "Full or partial player name.")
                  :nationality (s "string" "Nationality, e.g. 'Brazil'.")
                  :club (s "string" "Club name, e.g. 'Flamengo'.")
                  :position (s "string" "Position code, e.g. 'ST'.")
                  :limit (s "integer" "Maximum players to return (default 20).")}}
    :handler (fn [ds a] (query/search-players ds a))}

   {:name "competition_standings"
    :description (str "League standings for a competition and season, "
                      "calculated from match results (points, W/D/L, goals).")
    :inputSchema
    {:type "object"
     :properties {:competition (s "string" "Competition name (e.g. 'Brasileirão').")
                  :season (s "integer" "Season year (e.g. 2019).")}
     :required ["competition"]}
    :handler (fn [ds a] (query/competition-standings ds a))}

   {:name "competition_stats"
    :description (str "Aggregate statistics for a competition: average goals "
                      "per match, home/away win rates and the biggest wins.")
    :inputSchema
    {:type "object"
     :properties {:competition (s "string" "Competition name.")
                  :season (s "integer" "Season year (optional).")}}
    :handler (fn [ds a] (query/competition-stats ds a))}])

(def by-name (into {} (map (juxt :name identity)) tools))

(defn public-list
  "Tool descriptors for tools/list (without the internal :handler)."
  []
  (mapv #(dissoc % :handler) tools))
