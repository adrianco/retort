(ns brazilian-soccer.format
  "Context
  =======
  Renders query results (plain data from `brazilian-soccer.queries`) into the
  human-readable text blocks shown in the specification's \"Example answer
  format\" sections. These strings are what the MCP tools hand back to the
  calling LLM."
  (:require [clojure.string :as str]
            [brazilian-soccer.queries :as q]))

(defn- comp-label [m]
  (str (:competition m)
       (cond
         (:stage m) (str " - " (:stage m))
         (:round m) (str " Round " (:round m))
         :else "")))

(defn match-line
  "One match as `YYYY-MM-DD: Home H-A Away (Competition Round N)`."
  [m]
  (format "%s: %s %d-%d %s (%s)"
          (or (:date m) "????-??-??")
          (:home m) (:home-goal m) (:away-goal m) (:away m)
          (comp-label m)))

(defn matches-block
  ([ms] (matches-block ms 20))
  ([ms shown]
   (if (empty? ms)
     "No matches found."
     (let [head (take shown ms)
           more (- (count ms) (count head))]
       (str/join "\n"
                 (concat (map #(str "- " (match-line %)) head)
                         (when (pos? more)
                           [(format "- ... (%d more match%s in dataset)"
                                    more (if (= 1 more) "" "es"))])))))))

(defn head-to-head-block [{:keys [team1 team2 team1-wins team2-wins draws
                                  team1-goals team2-goals matches] :as h}]
  (if (empty? matches)
    (format "No matches found between %s and %s in the dataset." team1 team2)
    (str (format "%s vs %s (head-to-head in dataset):\n" team1 team2)
         (matches-block matches 15)
         "\n\n"
         (format "Head-to-head: %s %d win%s, %s %d win%s, %d draw%s\n"
                 team1 team1-wins (if (= 1 team1-wins) "" "s")
                 team2 team2-wins (if (= 1 team2-wins) "" "s")
                 draws (if (= 1 draws) "" "s"))
         (format "Goals: %s %d - %d %s" team1 team1-goals team2-goals team2))))

(defn team-record-block [{:keys [display matches wins draws losses goals-for
                                 goals-against win-rate season competition venue]}]
  (let [scope (str/join " "
                        (remove str/blank?
                                [(when season (str season))
                                 (when (and competition (seq (str competition))) (str competition))
                                 (case venue :home "(home)" :away "(away)" "")]))]
    (if (zero? matches)
      (format "No matches found for %s%s." display
              (if (str/blank? scope) "" (str " " scope)))
      (str (format "%s record%s:\n" display
                   (if (str/blank? scope) "" (str " " scope)))
           (format "- Matches: %d\n" matches)
           (format "- Wins: %d, Draws: %d, Losses: %d\n" wins draws losses)
           (format "- Goals For: %d, Goals Against: %d (diff %+d)\n"
                   goals-for goals-against (- goals-for goals-against))
           (format "- Win rate: %.1f%%" win-rate)))))

(defn standings-block [rows {:keys [competition season]}]
  (if (empty? rows)
    (format "No standings available for %s %s." competition season)
    (str (format "%s%s Final Standings (calculated from matches):\n"
                 (or competition "")
                 (if season (str " " season) ""))
         (str/join "\n"
                   (map (fn [r]
                          (format "%2d. %s - %d pts (%dW, %dD, %dL, GD %+d)"
                                  (:position r) (:team r) (:points r)
                                  (:wins r) (:draws r) (:losses r) (:goal-diff r)))
                        (take 20 rows))))))

(defn league-stats-block [{:keys [competition season matches total-goals
                                  avg-goals home-wins away-wins draws
                                  home-win-rate]}]
  (str (format "%s%s statistics:\n"
               (or competition "All competitions")
               (if season (str " " season) ""))
       (format "- Matches: %d\n" matches)
       (format "- Total goals: %d\n" total-goals)
       (format "- Average goals per match: %.2f\n" avg-goals)
       (format "- Home wins: %d, Away wins: %d, Draws: %d\n" home-wins away-wins draws)
       (format "- Home win rate: %.1f%%" home-win-rate)))

(defn players-block [ps]
  (if (empty? ps)
    "No players found."
    (str/join "\n"
              (map-indexed
               (fn [i p]
                 (format "%d. %s - Overall: %s, Position: %s, Club: %s, Nationality: %s"
                         (inc i) (:name p)
                         (or (:overall p) "?") (or (:position p) "?")
                         (or (:club p) "—") (or (:nationality p) "?")))
               ps))))

(defn club-breakdown-block [rows {:keys [nationality]}]
  (if (empty? rows)
    (format "No %s players found." nationality)
    (str (format "%s players by club:\n" (or nationality "Brazilian"))
         (str/join "\n"
                   (map (fn [r]
                          (format "- %s: %d players (avg rating: %d)"
                                  (:club r) (:players r) (:avg-overall r)))
                        rows)))))
