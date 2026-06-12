;; =============================================================================
;; brsoccer.format
;;
;; Context:
;;   Turns the plain-data results from brsoccer.query into the human-readable
;;   text blocks shown in the spec's "Example answer format" sections.  The MCP
;;   layer returns this text to the LLM as the tool result, while also returning
;;   the underlying structured data so the model can reason over it.
;; =============================================================================
(ns brsoccer.format
  (:require [clojure.string :as str]))

(defn match-line
  "One match formatted like '2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)'."
  [m]
  (let [ctx (->> [(:competition m)
                  (when (:round m) (str "Round " (:round m)))
                  (:stage m)]
                 (remove str/blank?)
                 (str/join " "))]
    (format "%s: %s %d-%d %s%s"
            (or (:date m) (str (:season m)))
            (:home m) (:home-goal m) (:away-goal m) (:away m)
            (if (str/blank? ctx) "" (str " (" ctx ")")))))

(defn matches-block
  "Render a list of matches with an optional header and a shown/total summary."
  [matches & {:keys [header show] :or {show 15}}]
  (let [total (count matches)
        shown (take show matches)]
    (str (when header (str header "\n"))
         (if (zero? total)
           "No matches found."
           (str (str/join "\n" (map #(str "- " (match-line %)) shown))
                (when (> total show)
                  (format "\n- ... (%d more in dataset)" (- total show))))))))

(defn head-to-head-block [h]
  (if (nil? h)
    "One or both teams were not found in the dataset."
    (str (matches-block (:matches h)
                        :header (format "%s vs %s:" (:team-a h) (:team-b h)))
         (format "\n\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws"
                 (:team-a h) (:a-wins h) (:team-b h) (:b-wins h) (:draws h))
         (format "\nGoals: %s %d, %s %d"
                 (:team-a h) (:a-goals h) (:team-b h) (:b-goals h)))))

(defn record-block [r]
  (if (nil? r)
    "Team not found in the dataset."
    (let [scope (->> [(when (:season r) (str (:season r)))
                      (:competition r)
                      (case (:venue r) :home "home" :away "away" nil)]
                     (remove nil?) (str/join " "))]
      (format (str "%s record%s:\n"
                   "- Matches: %d\n"
                   "- Wins: %d, Draws: %d, Losses: %d\n"
                   "- Goals For: %d, Goals Against: %d (diff %+d)\n"
                   "- Points: %d\n"
                   "- Win rate: %.1f%%")
              (:team r) (if (str/blank? scope) "" (str " (" scope ")"))
              (:matches r) (:wins r) (:draws r) (:losses r)
              (:goals-for r) (:goals-against r) (:goal-diff r)
              (:points r) (double (:win-rate r))))))

(defn player-line [p]
  (format "%s - Overall: %s, Position: %s, Club: %s, Nationality: %s, Age: %s"
          (:name p) (:overall p) (or (:position p) "?")
          (or (:club p) "—") (:nationality p) (:age p)))

(defn players-block [players & {:keys [header show] :or {show 15}}]
  (let [total (count players)]
    (str (when header (str header "\n"))
         (if (zero? total)
           "No players found."
           (str (->> (take show players)
                     (map-indexed (fn [i p] (format "%d. %s" (inc i) (player-line p))))
                     (str/join "\n"))
                (when (> total show)
                  (format "\n... (%d more in dataset)" (- total show))))))))

(defn standings-block [rows & {:keys [header show] :or {show 20}}]
  (if (empty? rows)
    "No standings could be computed (no matches for that competition/season)."
    (str (when header (str header "\n"))
         (->> (take show rows)
              (map (fn [r]
                     (format "%2d. %s - %d pts (%dW, %dD, %dL) GF:%d GA:%d GD:%+d"
                             (:position r) (:team r) (:points r)
                             (:wins r) (:draws r) (:losses r)
                             (:goals-for r) (:goals-against r) (:goal-diff r))))
              (str/join "\n")))))

(defn stats-block [s]
  (format (str "%s%s statistics:\n"
               "- Matches: %d\n"
               "- Total goals: %d\n"
               "- Average goals per match: %.2f\n"
               "- Home win rate: %.1f%%\n"
               "- Away win rate: %.1f%%\n"
               "- Draw rate: %.1f%%")
          (or (:competition s) "All competitions")
          (if (:season s) (str " " (:season s)) "")
          (:matches s) (:total-goals s) (double (:avg-goals s))
          (double (:home-win-rate s)) (double (:away-win-rate s)) (double (:draw-rate s))))

(defn competitions-block [cs]
  (str "Available competitions in the knowledge graph:\n"
       (->> cs
            (map (fn [c]
                   (format "- %s: %d matches (%s-%s)"
                           (:competition c) (:matches c)
                           (:seasons-from c) (:seasons-to c))))
            (str/join "\n"))))
