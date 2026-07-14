(ns soccer.format
  "=============================================================================
   soccer.format — Render query results as the human-readable text shown in
   the spec's 'Example answer format' blocks.
   -----------------------------------------------------------------------------
   Each function takes the plain data produced by soccer.queries and returns a
   String suitable to hand back to the LLM / display to a user. Keeping
   formatting separate from querying means the raw structured data is still
   available to callers that want it.
   ============================================================================="
  (:require [clojure.string :as str]))

(defn pct [x] (format "%.1f%%" (* 100.0 (double x))))

(defn match-line
  "One-line description of a match, e.g.
   2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A · Round 22)"
  [m]
  (let [tag (->> [(:competition m)
                  (when (:round m) (str "Round " (:round m)))
                  (:stage m)]
                 (remove nil?)
                 (str/join " · "))]
    (format "%s: %s %d-%d %s (%s)"
            (or (:date m) "????-??-??")
            (:home m) (:home-goal m) (:away-goal m) (:away m)
            tag)))

(defn matches [ms]
  (if (empty? ms)
    "No matches found."
    (str/join "\n" (map #(str "- " (match-line %)) ms))))

(defn head-to-head [h]
  (let [{:keys [team1 team2 team1-wins team2-wins draws meetings matches]} h]
    (if (zero? meetings)
      (format "No matches found between %s and %s." team1 team2)
      (str (format "%s vs %s — head-to-head (%d meetings in dataset):\n" team1 team2 meetings)
           (format "  %s wins: %d | %s wins: %d | Draws: %d\n\n" team1 team1-wins team2 team2-wins draws)
           "Most recent meetings:\n"
           (str/join "\n" (map #(str "- " (match-line %)) (take 10 matches)))))))

(defn team-stats [t]
  (let [{:keys [team season competition venue played wins draws losses gf ga gd points win-rate]} t
        scope (->> [(when competition competition)
                    (when season (str "season " season))
                    (when venue (str (clojure.core/name venue) " only"))]
                   (remove nil?) (str/join ", "))]
    (if (zero? played)
      (format "No matches found for %s%s." team (if (seq scope) (str " (" scope ")") ""))
      (str (format "%s record%s:\n" team (if (seq scope) (str " (" scope ")") ""))
           (format "- Matches: %d\n" played)
           (format "- Wins: %d, Draws: %d, Losses: %d\n" wins draws losses)
           (format "- Goals For: %d, Goals Against: %d (GD %+d)\n" gf ga gd)
           (format "- Points: %d\n" points)
           (format "- Win rate: %s" (pct win-rate))))))

(defn standings [rows {:keys [competition season]}]
  (if (empty? rows)
    (format "No standings available for %s %s." competition season)
    (str (format "%s %s Final Standings (calculated from matches):\n" competition season)
         (->> rows
              (map-indexed
               (fn [i {:keys [team played wins draws losses gf ga gd points]}]
                 (format "%2d. %-22s %3d pts  (%2dW %2dD %2dL)  GF %3d GA %3d GD %+d  [%d games]"
                         (inc i) team points wins draws losses gf ga gd played)))
              (str/join "\n")))))

(defn league-stats [s]
  (let [{:keys [competition season matches goals avg-goals home-win-rate away-win-rate draw-rate]} s]
    (str (format "%s%s statistics:\n" competition (if season (str " " season) ""))
         (format "- Matches: %d\n" matches)
         (format "- Total goals: %d\n" goals)
         (format "- Average goals per match: %.2f\n" avg-goals)
         (format "- Home win rate: %s\n" (pct home-win-rate))
         (format "- Away win rate: %s\n" (pct away-win-rate))
         (format "- Draw rate: %s" (pct draw-rate)))))

(defn biggest-wins [ms]
  (if (empty? ms)
    "No matches found."
    (str "Biggest victories (by goal margin):\n"
         (->> ms
              (map-indexed (fn [i m] (format "%2d. %s" (inc i) (match-line m))))
              (str/join "\n")))))

(defn player-line [p]
  (format "%s — Overall: %s, Potential: %s, Position: %s, Club: %s, Nationality: %s, Age: %s"
          (:name p) (:overall p) (:potential p) (:position p)
          (:club p) (:nationality p) (:age p)))

(defn players [ps]
  (if (empty? ps)
    "No players found."
    (str/join "\n"
              (map-indexed (fn [i p] (format "%2d. %s" (inc i) (player-line p))) ps))))

(defn season-summary [rows]
  (str "Season comparison:\n"
       (->> rows
            (map (fn [{:keys [season matches goals avg-goals home-wins]}]
                   (format "- %s: %d matches, %d goals (avg %.2f), %d home wins"
                           season matches goals avg-goals home-wins)))
            (str/join "\n"))))
