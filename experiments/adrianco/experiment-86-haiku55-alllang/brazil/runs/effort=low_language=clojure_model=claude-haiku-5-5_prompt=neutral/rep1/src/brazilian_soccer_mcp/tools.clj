(ns brazilian-soccer-mcp.tools
  "MCP tool definitions: argument parsing, query dispatch and plain-text rendering."
  (:require [clojure.string :as str]
            [brazilian-soccer-mcp.normalize :as n]
            [brazilian-soccer-mcp.query :as q]))

(defn- fail [msg]
  (throw (ex-info msg {})))

;; ---------------------------------------------------------------------------
;; Argument parsing

(defn- text-arg [a k]
  (let [v (get a k)]
    (when-not (str/blank? (some-> v str))
      (str/trim (str v)))))

(defn- required-text [a k]
  (or (text-arg a k) (fail (str "Missing required argument: " (name k)))))

(defn- int-arg [a k]
  (let [v (get a k)]
    (when (some? v)
      (or (if (number? v) (long v) (parse-long (str v)))
          (fail (str "Invalid integer for " (name k) ": " v))))))

(defn- date-arg [a k]
  (when-let [v (text-arg a k)]
    (or (n/parse-date v)
        (fail (str "Invalid date for " (name k) " (use YYYY-MM-DD): " v)))))

(defn- competition-arg [a k]
  (when-let [v (text-arg a k)]
    (or (q/parse-competition v)
        (fail (str "Unknown competition: " v
                   ". Use brasileirao, copa do brasil, libertadores, serie b or serie c.")))))

(defn- venue-arg [a]
  (case (some-> (text-arg a :venue) str/lower-case)
    "home" :home
    "away" :away
    (nil "any") :any
    (fail (str "venue must be home, away or any: " (get a :venue)))))

(defn- filters
  "Shared match filters parsed from tool arguments."
  [a]
  {:team (text-arg a :team)
   :opponent (text-arg a :opponent)
   :venue (venue-arg a)
   :competition (competition-arg a :competition)
   :season (int-arg a :season)
   :from (date-arg a :from)
   :to (date-arg a :to)})

;; ---------------------------------------------------------------------------
;; Rendering

(defn- competition-label [c]
  (get q/competition-labels c "all competitions"))

(defn- round-label [{:keys [competition round]}]
  (cond
    (nil? round) nil
    (= :libertadores competition) round
    (re-matches #"\d+" round) (str "Round " round)
    :else round))

(defn- match-line [m]
  (str "- " (:date m) ": " (:home m) " " (:home-goals m) "-" (:away-goals m) " " (:away m)
       " (" (str/join " " (remove nil? [(competition-label (:competition m)) (round-label m)])) ")"))

(defn- scope-label
  "Human description of the filters, e.g. \"2022, Brasileirão, home\"."
  [{:keys [season competition venue]}]
  (let [parts (remove nil? [(some-> season str)
                            (some-> competition competition-label)
                            (when (and venue (not= venue :any)) (name venue))])]
    (if (seq parts) (str/join ", " parts) "all seasons and competitions")))

(defn- pct-text [rate]
  (if rate (str rate "%") "n/a"))

(defn- render-matches [{:keys [total matches]}]
  (if (zero? total)
    "No matches found for those filters."
    (str "Showing " (count matches) " of " total " matches:\n"
         (str/join "\n" (map match-line matches)))))

(defn- render-team-record [{:keys [team matches wins draws losses goals-for goals-against win-rate]} opts]
  (str team " (" (scope-label opts) "):\n"
       "- Matches: " matches "\n"
       "- Wins: " wins ", Draws: " draws ", Losses: " losses "\n"
       "- Goals For: " goals-for ", Goals Against: " goals-against "\n"
       "- Win rate: " (pct-text win-rate)))

(defn- render-head-to-head [{:keys [team-a team-b total a-wins draws b-wins a-goals b-goals matches]}]
  (if (zero? total)
    (str "No matches between " team-a " and " team-b " in the dataset.")
    (str team-a " vs " team-b " head-to-head (" total " matches in dataset):\n"
         team-a " " a-wins " wins, " team-b " " b-wins " wins, " draws " draws"
         " (goals " a-goals "-" b-goals ")\n"
         "Most recent:\n"
         (str/join "\n" (map (comp match-line :match) matches)))))

(defn- render-standings [rows competition season]
  (if (empty? rows)
    (str "No " (competition-label competition) " matches for " season " in the dataset.")
    (str season " " (competition-label competition) " standings (calculated from matches):\n"
         (str/join "\n"
                   (for [{:keys [position team points wins draws losses goals-for goals-against goal-diff]} rows]
                     (str position ". " team " - " points " pts (" wins "W, " draws "D, " losses "L) "
                          goals-for ":" goals-against " GD " (if (pos? goal-diff) (str "+" goal-diff) goal-diff)))))))

(defn- render-match-stats [{:keys [matches goals goals-per-match home-win-rate draw-rate away-win-rate biggest-wins]} opts]
  (if (zero? matches)
    "No matches found for those filters."
    (str "Match statistics (" (scope-label opts) "):\n"
         "- Matches: " matches "\n"
         "- Goals: " goals " (" goals-per-match " per match)\n"
         "- Home win rate: " (pct-text home-win-rate)
         ", Draw rate: " (pct-text draw-rate)
         ", Away win rate: " (pct-text away-win-rate) "\n"
         "Biggest wins:\n"
         (str/join "\n" (map match-line biggest-wins)))))

(defn- render-players [{:keys [total players]}]
  (if (zero? total)
    "No players found for those filters."
    (str "Showing " (count players) " of " total " players:\n"
         (str/join "\n"
                   (map-indexed
                    (fn [i p]
                      (str (inc i) ". " (:name p) " - Overall: " (:overall p)
                           ", Potential: " (:potential p)
                           ", Position: " (:position p)
                           ", Club: " (:club p)
                           ", Nationality: " (:nationality p)))
                    players)))))

;; ---------------------------------------------------------------------------
;; Tool handlers: (fn [db arguments] -> text)

(defn- search-matches-tool [db a]
  (let [f (filters a)]
    (render-matches (q/search-matches db (assoc f :limit (or (int-arg a :limit) 20))))))

(defn- team-record-tool [db a]
  (let [f (filters a)
        team (required-text a :team)]
    (render-team-record (q/team-record db team (dissoc f :team)) (assoc f :team team))))

(defn- head-to-head-tool [db a]
  (render-head-to-head
   (q/head-to-head db (required-text a :team_a) (required-text a :team_b)
                   {:limit (or (int-arg a :limit) 10)})))

(defn- standings-tool [db a]
  (let [competition (competition-arg a :competition)
        season (or (int-arg a :season) (fail "Missing required argument: season"))]
    (when-not competition
      (fail "Missing required argument: competition"))
    (render-standings (q/standings db competition season) competition season)))

(defn- match-stats-tool [db a]
  (let [f (filters a)]
    (render-match-stats (q/match-stats db (assoc f :top (or (int-arg a :top) 5))) f)))

(defn- search-players-tool [db a]
  (render-players
   (q/search-players db {:name (text-arg a :name)
                         :nationality (text-arg a :nationality)
                         :club (text-arg a :club)
                         :position (text-arg a :position)
                         :min-overall (int-arg a :min_overall)
                         :limit (or (int-arg a :limit) 20)})))

;; ---------------------------------------------------------------------------
;; MCP tool specs

(defn- prop [type description]
  {:type type :description description})

(def ^:private team-prop
  (prop "string" "Team name, e.g. \"Flamengo\" or \"Palmeiras-SP\". State suffixes and accents are optional."))
(def ^:private opponent-prop
  (prop "string" "Opponent team name, optional."))
(def ^:private venue-prop
  (prop "string" "home, away or any (default any). Only applies with team."))
(def ^:private competition-prop
  (prop "string" "brasileirao, copa do brasil, libertadores, serie b or serie c."))
(def ^:private season-prop
  (prop "integer" "Season year, e.g. 2023."))
(def ^:private from-prop
  (prop "string" "Earliest match date, YYYY-MM-DD."))
(def ^:private to-prop
  (prop "string" "Latest match date, YYYY-MM-DD."))
(def ^:private limit-prop
  (prop "integer" "Maximum rows to return."))

(def specs
  [{:name "search_matches"
    :description "Find matches by team, opponent, venue, competition, season or date range. Most recent first."
    :inputSchema {:type "object"
                  :properties {:team team-prop
                               :opponent opponent-prop
                               :venue venue-prop
                               :competition competition-prop
                               :season season-prop
                               :from from-prop
                               :to to-prop
                               :limit limit-prop}}}
   {:name "team_record"
    :description "Wins, draws, losses, goals and win rate for a team, optionally filtered by season, competition or venue."
    :inputSchema {:type "object"
                  :properties {:team team-prop
                               :venue venue-prop
                               :competition competition-prop
                               :season season-prop}
                  :required ["team"]}}
   {:name "head_to_head"
    :description "Head-to-head record between two teams across all competitions in the dataset."
    :inputSchema {:type "object"
                  :properties {:team_a (prop "string" "First team name.")
                               :team_b (prop "string" "Second team name.")
                               :limit limit-prop}
                  :required ["team_a" "team_b"]}}
   {:name "standings"
    :description "League table for a competition and season, calculated from match results (3 points per win, 1 per draw)."
    :inputSchema {:type "object"
                  :properties {:competition competition-prop
                               :season season-prop}
                  :required ["competition" "season"]}}
   {:name "match_stats"
    :description "Average goals per match, home/draw/away win rates and the biggest wins for a set of matches."
    :inputSchema {:type "object"
                  :properties {:team team-prop
                               :venue venue-prop
                               :competition competition-prop
                               :season season-prop
                               :from from-prop
                               :to to-prop
                               :top (prop "integer" "How many biggest wins to list (default 5).")}}}
   {:name "search_players"
    :description "Search FIFA player data by name, nationality, club, position group or minimum overall rating."
    :inputSchema {:type "object"
                  :properties {:name (prop "string" "Player name, partial match allowed, e.g. \"Neymar\".")
                               :nationality (prop "string" "Nationality, e.g. \"Brazil\".")
                               :club (prop "string" "Club name, partial match, e.g. \"Flamengo\".")
                               :position (prop "string" "forward, midfielder, defender, goalkeeper, or a position code such as ST.")
                               :min_overall (prop "integer" "Minimum overall rating.")
                               :limit limit-prop}}}])

(def ^:private handlers
  {"search_matches" search-matches-tool
   "team_record" team-record-tool
   "head_to_head" head-to-head-tool
   "standings" standings-tool
   "match_stats" match-stats-tool
   "search_players" search-players-tool})

(defn call
  "Runs the named tool against the loaded dataset and returns an MCP CallToolResult."
  [db tool-name arguments]
  (if-let [handler (handlers tool-name)]
    (try
      {:content [{:type "text" :text (handler db (or arguments {}))}]
       :isError false}
      (catch Exception e
        {:content [{:type "text" :text (or (ex-message e) "Unexpected error")}]
         :isError true}))
    {:content [{:type "text" :text (str "Unknown tool: " tool-name)}]
     :isError true}))
