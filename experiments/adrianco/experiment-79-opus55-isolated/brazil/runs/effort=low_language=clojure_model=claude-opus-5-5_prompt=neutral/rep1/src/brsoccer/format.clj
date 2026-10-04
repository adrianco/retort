(ns brsoccer.format
  "Renders query results as the plain-text answers returned by the MCP tools."
  (:require [clojure.string :as str])
  (:import (java.util Locale)))

(defn- fmt [pattern & args]
  (String/format Locale/US pattern (to-array args)))

(defn- lines [& xs]
  (str/join "\n" (remove nil? (flatten xs))))

(defn- context
  "\"Copa do Brasil 2019, final\" / \"Brasileirão Série A 2019, Round 22\"."
  [{:keys [competition season round stage arena]}]
  (str competition
       (when season (str " " season))
       (cond stage (str ", " stage)
             round (str ", Round " round))
       (when arena (str ", " arena))))

(defn match-line [m]
  (fmt "- %s: %s %d-%d %s (%s)%s"
       (:date m) (:home-name m) (:home-goals m) (:away-goals m) (:away-name m)
       (context m)
       (if (:derby m) (str " [" (:derby m) "]") "")))

(defn match-list
  "Bulleted matches cut to `limit`, with a note about the remainder."
  [matches limit]
  (let [limit (or limit 20)
        more (- (count matches) limit)]
    (lines (map match-line (take limit matches))
           (when (pos? more) (fmt "- ... (%d more matches in dataset)" more)))))

(defn- scope
  "Human description of the filters that were applied."
  [{:keys [competition season venue]}]
  (let [parts (remove nil? [(when season (str season))
                            competition
                            (when (#{:home :away} venue) (name venue))])]
    (if (seq parts) (str " (" (str/join ", " parts) ")") "")))

(defn- record-lines [r]
  [(fmt "- Matches: %d" (:played r))
   (fmt "- Wins: %d, Draws: %d, Losses: %d" (:wins r) (:draws r) (:losses r))
   (fmt "- Goals For: %d, Goals Against: %d (difference %+d)"
        (:goals-for r) (:goals-against r) (:goal-difference r))
   (fmt "- Win rate: %.1f%%" (:win-rate r))])

(defn- record-summary [r]
  (fmt "%d played, %dW %dD %dL, goals %d-%d"
       (:played r) (:wins r) (:draws r) (:losses r) (:goals-for r) (:goals-against r)))

(defn matches [found {:keys [limit]}]
  (if (empty? found)
    "No matches found for those criteria in the dataset."
    (lines (fmt "%d matches found (most recent first):" (count found))
           (match-list found limit))))

(defn head-to-head [h {:keys [limit]}]
  (if (zero? (:played h))
    (fmt "No matches between %s and %s in the dataset." (:team-a h) (:team-b h))
    (lines (fmt "%s vs %s%s:" (:team-a h) (:team-b h)
                (if (:derby h) (str " (" (:derby h) ")") ""))
           (match-list (:matches h) limit)
           ""
           (fmt "Head-to-head in dataset (%d matches): %s %d wins, %s %d wins, %d draws"
                (:played h) (:team-a h) (:a-wins h) (:team-b h) (:b-wins h) (:draws h))
           (fmt "Goals: %s %d, %s %d" (:team-a h) (:a-goals h) (:team-b h) (:b-goals h)))))

(defn team-stats [s]
  (if (zero? (:played (:overall s)))
    (fmt "No matches found for %s%s in the dataset." (:team s) (scope s))
    (lines (fmt "%s record%s:" (:team s) (scope s))
           (record-lines (:overall s))
           (when (= :either (:venue s))
             [(str "- Home: " (record-summary (:home s)))
              (str "- Away: " (record-summary (:away s)))])
           (when (> (count (:by-competition s)) 1)
             ["" "By competition:"
              (for [c (:by-competition s)]
                (str "- " (:competition c) ": " (record-summary c)))]))))

(defn standings [s]
  (cond
    (empty? (:rows s))
    (fmt "No %s matches for season %d in the dataset." (:competition s) (:season s))

    (not (:league? s))
    (lines (fmt "%d %s is a knockout/group competition; aggregate record of each team:"
                (:season s) (:competition s))
           (for [r (take 20 (:rows s))]
             (fmt "%d. %s - %s" (:position r) (:name r) (record-summary r))))

    :else
    (let [relegated (set (:relegated s))]
      (lines (fmt "%d %s %s (calculated from %d matches):"
                  (:season s) (:competition s)
                  (if (:complete? s) "Final Standings" "Standings")
                  (:matches s))
             (for [r (:rows s)]
               (fmt "%d. %s - %d pts (%dW, %dD, %dL), goals %d-%d%s"
                    (:position r) (:name r) (:points r) (:wins r) (:draws r) (:losses r)
                    (:goals-for r) (:goals-against r)
                    (cond (and (:champion s) (= 1 (:position r))) " - Champion"
                          (relegated (:name r)) " - Relegated"
                          :else "")))
             (when-not (:complete? s)
               "Note: the dataset does not hold a complete double round-robin for this season, so no champion or relegation is inferred.")
             "Note: points deducted by sporting courts are not in the data; official tables can differ slightly."))))

(defn- metric-value [metric r]
  (case metric
    "win_rate" (fmt "%.1f%% wins" (:win-rate r))
    "points_per_match" (fmt "%.2f pts/match" (:points-per-match r))
    "points" (fmt "%d pts" (:points r))
    "wins" (fmt "%d wins" (:wins r))
    "losses" (fmt "%d losses" (:losses r))
    "goals_for" (fmt "%d goals scored" (:goals-for r))
    "goals_against" (fmt "%d goals conceded" (:goals-against r))
    "goal_difference" (fmt "%+d goal difference" (:goal-difference r))))

(defn ranking [r]
  (if (empty? (:rows r))
    "No teams match those criteria in the dataset."
    (lines (fmt "Teams ranked by %s%s:" (:metric r) (scope r))
           (map-indexed (fn [i row]
                          (fmt "%d. %s - %s (%s)" (inc i) (:name row)
                               (metric-value (:metric r) row) (record-summary row)))
                        (:rows r)))))

(defn competition-stats [s]
  (if (zero? (:matches s))
    "No matches found for those criteria in the dataset."
    (lines (fmt "Statistics%s:" (scope s))
           (fmt "- Matches: %d" (:matches s))
           (fmt "- Goals: %d" (:goals s))
           (fmt "- Average goals per match: %.2f" (:goals-per-match s))
           (fmt "- Home win rate: %.1f%%" (:home-win-rate s))
           (fmt "- Draw rate: %.1f%%" (:draw-rate s))
           (fmt "- Away win rate: %.1f%%" (:away-win-rate s))
           (when (> (count (:by-competition s)) 1)
             ["" "Goals per match by competition:"
              (for [c (:by-competition s)]
                (fmt "- %s: %.2f (%d matches)" (:competition c) (:goals-per-match c) (:matches c)))]))))

(defn biggest-wins [found]
  (if (empty? found)
    "No matches found for those criteria in the dataset."
    (lines "Biggest victories (provided data):"
           (map-indexed (fn [i m] (str (inc i) ". " (subs (match-line m) 2))) found))))

(defn- seasons-range [seasons]
  (cond (empty? seasons) ""
        (= 1 (count seasons)) (str (first seasons))
        :else (str (first seasons) "-" (last seasons))))

(defn team-competitions [t]
  (lines (fmt "%s appears in %d competitions in the dataset:" (:team t) (count (:competitions t)))
         (for [c (:competitions t)]
           (fmt "- %s (%s, %d seasons): %s" (:competition c) (seasons-range (:seasons c))
                (count (:seasons c)) (record-summary c)))))

(defn derbies [found {:keys [limit]}]
  (if (empty? found)
    "No derby matches found for those criteria in the dataset."
    (lines (fmt "%d derby matches found (most recent first):" (count found))
           (match-list found (or limit 50)))))

(defn competitions [c]
  (lines "Brazilian soccer dataset:"
         (for [x (:competitions c)]
           (fmt "- %s: %d matches, seasons %d-%d"
                (:competition x) (:matches x) (:first-season x) (:last-season x)))
         (fmt "- FIFA player database: %d players" (:players c))
         (fmt "- %d distinct teams" (:teams c))
         "" "Source files (rows):"
         (for [[f n] (sort (:files c))] (fmt "- %s: %d" f n))))

(defn player-line [p]
  (fmt "%s - Overall: %s, Position: %s, Club: %s, Nationality: %s, Age: %s"
       (:name p) (or (:overall p) "?") (or (:position p) "?")
       (or (:club p) "no club") (:nationality p) (or (:age p) "?")))

(defn players [{:keys [total] found :players}]
  (if (zero? total)
    "No players found for those criteria in the FIFA dataset."
    (lines (fmt "%d players found (best rated first):" total)
           (map-indexed (fn [i p] (str (inc i) ". " (player-line p))) found)
           (when (> total (count found))
             (fmt "... (%d more players in dataset)" (- total (count found)))))))

(defn player-details [{:keys [total] found :players}]
  (if (zero? total)
    "No players found with that name in the FIFA dataset."
    (lines (for [p found]
             [(fmt "%s (FIFA id %s)" (:name p) (:id p))
              (fmt "- Nationality: %s, Age: %s" (:nationality p) (or (:age p) "?"))
              (fmt "- Club: %s, Position: %s, Jersey: %s"
                   (or (:club p) "no club") (or (:position p) "?") (or (:jersey p) "?"))
              (fmt "- Overall: %s, Potential: %s" (or (:overall p) "?") (or (:potential p) "?"))
              (fmt "- Height: %s, Weight: %s, Preferred foot: %s"
                   (or (:height p) "?") (or (:weight p) "?") (or (:foot p) "?"))
              (fmt "- Value: %s, Wage: %s" (or (:value p) "?") (or (:wage p) "?"))
              (when (seq (:skills p))
                (str "- Top attributes: "
                     (->> (:skills p) (sort-by (comp - val)) (take 6)
                          (map (fn [[k v]] (str k " " v))) (str/join ", "))))
              ""])
           (when (> total (count found))
             (fmt "... (%d more players match that name)" (- total (count found)))))))

(defn club-squads [squads {:keys [nationality]}]
  (if (empty? squads)
    "No matching players at Brazilian clubs in the FIFA dataset."
    (lines (fmt "%s at Brazilian clubs (FIFA data joined with league data):"
                (if nationality (str "Players from " nationality) "Players"))
           (for [s squads]
             (fmt "- %s: %d players (avg rating: %.0f, best: %s %s)"
                  (:club s) (:players s) (:average-overall s)
                  (:name (:best s)) (:overall (:best s)))))))

(defn team-profile [p]
  (lines (fmt "%s - profile from match and player data:" (:team p))
         (str "Overall: " (record-summary (:overall p)))
         "" "Competitions:"
         (for [c (:competitions p)]
           (fmt "- %s (%s): %s" (:competition c) (seasons-range (:seasons c)) (record-summary c)))
         "" "Most recent matches:"
         (map match-line (:recent p))
         ""
         (if (zero? (:squad-size p))
           "FIFA squad: this club is not in the FIFA player dataset."
           [(fmt "FIFA squad (%d players), top rated:" (:squad-size p))
            (for [x (:squad p)] (str "- " (player-line x)))])))
