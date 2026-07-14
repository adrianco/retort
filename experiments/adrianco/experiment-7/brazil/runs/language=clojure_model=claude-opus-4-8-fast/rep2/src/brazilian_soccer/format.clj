(ns brazilian-soccer.format
  "=============================================================================
   format.clj — Human-readable rendering of query results
   -----------------------------------------------------------------------------
   Context:
     The MCP tools return text content to the calling LLM/user. This namespace
     turns the plain-data results from brazilian-soccer.queries into the
     readable, example-style strings shown in the specification (match lines,
     standings tables, team records, player rankings, etc.).
   ============================================================================="
  (:require [clojure.string :as str]))

(defn- pct [x] (format "%.1f%%" (* 100.0 (or x 0.0))))

(defn match-line
  "Render a single match like:
     2023-09-03: Flamengo 2-1 Fluminense (Brasileirão, Round 22)"
  [{:keys [date home-team away-team home-goal away-goal competition round stage]}]
  (let [score (if (and home-goal away-goal)
                (str home-goal "-" away-goal)
                "?-?")
        extra (cond
                round (str ", Round " round)
                stage (str ", " stage)
                :else "")]
    (format "%s: %s %s %s (%s%s)"
            (or date "????-??-??") home-team score away-team competition extra)))

(defn matches-report
  "Render a list of matches with a header and optional truncation note."
  [matches {:keys [title shown]}]
  (if (empty? matches)
    (str (or title "Matches") ": none found.")
    (let [shown   (or shown (count matches))
          listed  (take shown matches)
          more    (- (count matches) shown)]
      (str (when title (str title "\n"))
           (str/join "\n" (map #(str "- " (match-line %)) listed))
           (when (pos? more) (format "\n- ... (%d more matches)" more))))))

(defn team-stats-report
  [{:keys [team season competition venue played wins draws losses
           goals-for goals-against win-rate]}]
  (let [scope (str/join " " (remove str/blank?
                                    [(when competition (str competition))
                                     (when season (str season))
                                     (when (not= venue :all) (str (clojure.core/name venue) " only"))]))]
    (str team " record" (when (seq scope) (str " (" scope ")")) ":\n"
         (format "- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Win rate: %s"
                 played wins draws losses goals-for goals-against (pct win-rate)))))

(defn head-to-head-report
  [{:keys [team1 team2 team1-wins team2-wins draws total matches]}]
  (str (format "%s vs %s — head-to-head (%d matches in dataset):\n" team1 team2 total)
       (format "%s %d wins, %s %d wins, %d draws" team1 team1-wins team2 team2-wins draws)
       (when (seq matches)
         (str "\n\nRecent meetings:\n"
              (str/join "\n" (map #(str "- " (match-line %)) (take 10 matches)))))))

(defn standings-report
  [rows {:keys [title limit] :or {limit 20}}]
  (if (empty? rows)
    (str (or title "Standings") ": no data.")
    (str (when title (str title "\n"))
         (str/join "\n"
                   (map (fn [{:keys [rank team points played wins draws losses goal-diff]}]
                          (format "%2d. %s - %d pts (%dW %dD %dL, GD %+d)"
                                  rank team points wins draws losses goal-diff))
                        (take limit rows))))))

(defn competition-stats-report
  [{:keys [competition season matches total-goals avg-goals
           home-wins away-wins draws home-win-rate]}]
  (str (str/join " " (remove nil? [competition season "statistics:"])) "\n"
       (format "- Matches: %d\n- Total goals: %d\n- Average goals per match: %.2f\n- Home wins: %d, Away wins: %d, Draws: %d\n- Home win rate: %s"
               matches total-goals avg-goals home-wins away-wins draws (pct home-win-rate))))

(defn players-report
  [players {:keys [title limit] :or {limit 25}}]
  (if (empty? players)
    (str (or title "Players") ": none found.")
    (str (when title (str title "\n"))
         (str/join "\n"
                   (map-indexed
                    (fn [i {:keys [name overall position club nationality age]}]
                      (format "%d. %s - Overall: %s, Position: %s, Club: %s, Nationality: %s%s"
                              (inc i) name (or overall "?") (or position "?")
                              (or club "Free agent") (or nationality "?")
                              (if age (str ", Age: " age) "")))
                    (take limit players))))))

(defn club-summary-report
  [rows {:keys [title limit] :or {limit 20}}]
  (if (empty? rows)
    (str (or title "Clubs") ": none found.")
    (str (when title (str title "\n"))
         (str/join "\n"
                   (map (fn [{:keys [club count avg-overall]}]
                          (format "- %s: %d players (avg rating: %.1f)" club count avg-overall))
                        (take limit rows))))))
