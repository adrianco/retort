(ns brazilian-soccer.format
  "=============================================================================
   Brazilian Soccer MCP Server - Human-Readable Formatting
   =============================================================================

   CONTEXT
     Turns the plain-data results from brazilian-soccer.query into the natural,
     readable text blocks shown in the spec's 'Example answer format' sections.
     Kept separate from the query engine so the data functions stay pure and
     the MCP tools can choose text (for LLM display) without re-deriving values.

   PUBLIC API
     match-line        - one match as \"date: Home G-G Away (Competition Round)\"
     matches           - a bulleted list of matches (with optional cap note)
     team-stats        - the W/D/L + goals + win-rate block
     head-to-head      - the head-to-head summary block
     standings         - a numbered league table
     players           - a numbered player list
     club-roster       - club roster summary
     competition-stats - aggregate stats block
   ============================================================================="
  (:require [clojure.string :as str]))

(defn- pct [x] (format "%.1f%%" (double x)))

(defn match-line
  "Format a single match record as a readable line."
  [{:keys [date home away home-goal away-goal competition round stage]}]
  (let [score (if (and home-goal away-goal)
                (format "%d-%d" home-goal away-goal)
                "?-?")
        ctx (->> [competition
                  (when (and round (not (str/blank? round))) (str "Round " round))
                  (when (and stage (not (str/blank? stage))) stage)]
                 (remove nil?)
                 (distinct)
                 (str/join " "))]
    (format "%s: %s %s %s (%s)"
            (or date "????-??-??") home score away ctx)))

(defn matches
  "Bulleted list of matches. total, when larger than the shown count, adds a
   '... (N more in dataset)' note."
  ([ms] (matches ms (count ms)))
  ([ms total]
   (if (empty? ms)
     "No matches found."
     (let [lines (map #(str "- " (match-line %)) ms)
           extra (- total (count ms))]
       (str/join "\n"
                 (cond-> (vec lines)
                   (pos? extra) (conj (format "- ... (%d more in dataset)" extra))))))))

(defn team-stats
  "Format a team-stats map into the spec's record block."
  [{:keys [team venue season competition matches win draw loss
           goals-for goals-against win-rate] :as s}]
  (if (nil? s)
    "Team not found."
    (let [scope (->> [(when season (str season))
                      (when competition competition)
                      (case venue :home "home" :away "away" nil)]
                     (remove nil?)
                     (str/join " "))
          header (if (str/blank? scope)
                   (format "%s record:" team)
                   (format "%s record (%s):" team scope))]
      (str/join "\n"
                [header
                 (format "- Matches: %d" matches)
                 (format "- Wins: %d, Draws: %d, Losses: %d" win draw loss)
                 (format "- Goals For: %d, Goals Against: %d" goals-for goals-against)
                 (format "- Win rate: %s" (pct win-rate))]))))

(defn head-to-head
  "Format a head-to-head map, optionally showing the first `show` matches."
  ([h2h] (head-to-head h2h 0))
  ([{:keys [team1 team2 total team1-wins team2-wins draws matches] :as h2h} show]
   (if (nil? h2h)
     "One or both teams not found."
     (str/join "\n"
               (concat
                [(format "%s vs %s:" team1 team2)]
                (when (pos? show)
                  (map #(str "- " (match-line %)) (take show matches)))
                (when (and (pos? show) (> total show))
                  [(format "- ... (%d more in dataset)" (- total show))])
                [(format "Head-to-head in dataset: %s %d wins, %s %d wins, %d draws"
                         team1 team1-wins team2 team2-wins draws)])))))

(defn standings
  "Format a standings sequence as a numbered table. `top`, if positive, caps
   the number of rows shown."
  ([rows] (standings rows 0))
  ([rows top]
   (if (empty? rows)
     "No standings available."
     (let [rows (if (pos? top) (take top rows) rows)]
       (str/join "\n"
                 (map (fn [{:keys [rank team points win draw loss]}]
                        (format "%d. %s - %d pts (%dW, %dD, %dL)"
                                rank team points win draw loss))
                      rows))))))

(defn players
  "Numbered list of players in the spec's format."
  [ps]
  (if (empty? ps)
    "No players found."
    (str/join "\n"
              (map-indexed
               (fn [i {:keys [name overall position club]}]
                 (format "%d. %s - Overall: %s, Position: %s, Club: %s"
                         (inc i) name (or overall "?") (or position "?") (or club "?")))
               ps))))

(defn club-roster
  "Format a club roster summary plus its player list."
  [{:keys [club count avg-overall players]}]
  (if (zero? count)
    (format "No players found for club \"%s\"." club)
    (str/join "\n"
              (concat
               [(format "%s: %d players (avg rating: %s)"
                        club count
                        (if avg-overall (format "%.0f" avg-overall) "n/a"))]
               (map-indexed
                (fn [i {:keys [name overall position]}]
                  (format "%d. %s - Overall: %s, Position: %s"
                          (inc i) name (or overall "?") (or position "?")))
                players)))))

(defn competition-stats
  "Format aggregate competition statistics."
  [{:keys [competition season matches total-goals avg-goals-per-match
           home-wins away-wins draws home-win-rate]}]
  (let [scope (->> [competition (when season (str season))]
                   (remove nil?) (str/join " "))]
    (str/join "\n"
              [(format "Statistics%s:" (if (str/blank? scope) "" (str " (" scope ")")))
               (format "- Matches: %d" matches)
               (format "- Total goals: %d" total-goals)
               (format "- Average goals per match: %.2f" (double avg-goals-per-match))
               (format "- Home wins: %d, Away wins: %d, Draws: %d" home-wins away-wins draws)
               (format "- Home win rate: %s" (pct home-win-rate))])))
