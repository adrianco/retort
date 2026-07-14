(ns brazilian-soccer.format
  "Render query results as the human-readable answers shown in the spec.

  Every function returns a plain string suitable for returning directly as an
  MCP tool's text content."
  (:require [clojure.string :as str]))

(defn- pluralize [n word]
  (let [plural (cond
                 (= 1 n) word
                 (str/ends-with? word "ch") (str word "es")
                 :else (str word "s"))]
    (str n " " plural)))

(defn- match-line [m]
  (let [date (if (:date m) (str (:date m)) "?")
        ctx (->> [(:competition m)
                  (when (:round m) (str "Round " (:round m)))]
                 (remove nil?)
                 (str/join " "))]
    (format "- %s: %s %d-%d %s (%s)"
            date (:home-team m) (:home-goal m) (:away-goal m) (:away-team m) ctx)))

(defn matches
  "Render a list of matches, most-recent first."
  [ms]
  (if (empty? ms)
    "No matches found for that query."
    (str (pluralize (count ms) "match") " found:\n"
         (str/join "\n" (map match-line ms)))))

(defn head-to-head
  "Render a head-to-head summary."
  [{:keys [team-a team-b total team-a-wins team-b-wins draws
           team-a-goals team-b-goals]}]
  (if (zero? total)
    (format "No matches found between %s and %s." team-a team-b)
    (str (format "%s vs %s head-to-head (%s in dataset):\n"
                 team-a team-b (pluralize total "match"))
         (format "- %s: %s\n" team-a (pluralize team-a-wins "win"))
         (format "- %s: %s\n" team-b (pluralize team-b-wins "win"))
         (format "- %s\n" (pluralize draws "draw"))
         (format "- Goals: %s %d, %s %d"
                 team-a team-a-goals team-b team-b-goals))))

(defn team-record
  "Render a team's record block."
  [{:keys [team matches wins draws losses goals-for goals-against
           points win-rate]}]
  (str (format "%s record:\n" team)
       (format "- Matches: %d\n" matches)
       (format "- Wins: %d, Draws: %d, Losses: %d\n" wins draws losses)
       (format "- Goals For: %d, Goals Against: %d\n" goals-for goals-against)
       (format "- Points: %d\n" points)
       (format "- Win rate: %s%%" win-rate)))

(defn- standings-line [i {:keys [team points wins draws losses]}]
  (format "%d. %s - %d pts (%dW, %dD, %dL)" (inc i) team points wins draws losses))

(defn standings
  "Render a league table for a competition/season."
  [competition season rows]
  (if (empty? rows)
    (format "No standings available for %s %s." season competition)
    (str (format "%s %s Final Standings (calculated from matches):\n"
                 season competition)
         (str/join "\n" (map-indexed standings-line rows)))))

(defn- player-line [i {:keys [name overall position club]}]
  (format "%d. %s - Overall: %s, Position: %s, Club: %s"
          (inc i) name overall position club))

(defn players
  "Render a numbered player list."
  [ps]
  (if (empty? ps)
    "No players found for that query."
    (str (pluralize (count ps) "player") " found:\n"
         (str/join "\n" (map-indexed player-line ps)))))

(defn statistics
  "Render an aggregate statistics block."
  [{:keys [scope total-matches avg-goals home-win-rate biggest]}]
  (str (when scope (str scope "\n"))
       (format "- Matches: %d\n" total-matches)
       (format "- Average goals per match: %s\n" avg-goals)
       (format "- Home win rate: %s%%\n" home-win-rate)
       "Biggest wins:\n"
       (str/join "\n" (map-indexed
                       (fn [i m]
                         (format "%d. %s %d-%d %s (%s)"
                                 (inc i) (:home-team m) (:home-goal m)
                                 (:away-goal m) (:away-team m) (:competition m)))
                       biggest))))
