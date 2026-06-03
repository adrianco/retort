;; =============================================================================
;; brazilian-soccer.format
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   Part of the Brazilian Soccer MCP server (see TASK.md). Turns the structured
;;   results produced by brazilian-soccer.queries into the human-readable text
;;   blocks shown in the spec's "Example answer format" sections. The MCP layer
;;   returns both this formatted text and the raw structured data, so an LLM
;;   client can either present the prose directly or reason over the data.
;; =============================================================================
(ns brazilian-soccer.format
  (:require [clojure.string :as str]))

(defn- comp-tag [m]
  (let [parts (remove str/blank?
                      [(:competition m)
                       (when (:round m) (str "Round " (:round m)))
                       (:stage m)])]
    (when (seq parts) (str " (" (str/join ", " parts) ")"))))

(defn match-line
  "One-line description of a match, e.g.
   \"2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)\"."
  [m]
  (str (or (:date m) "????-??-??") ": "
       (:home m) " " (:home-goal m) "-" (:away-goal m) " " (:away m)
       (comp-tag m)))

(defn matches->text [ms]
  (if (empty? ms)
    "No matches found."
    (str/join "\n" (map #(str "- " (match-line %)) ms))))

(defn head-to-head->text [{:keys [team-a team-b matches record]}]
  (let [{:keys [a-wins b-wins draws total a-goals b-goals]} record]
    (if (zero? total)
      (format "No matches found between %s and %s in the dataset." team-a team-b)
      (str (format "%s vs %s — %d matches in dataset\n" team-a team-b total)
           (matches->text (take 15 matches))
           (when (> total 15) (format "\n- ... (%d more)" (- total 15)))
           (format "\n\nHead-to-head: %s %d wins, %s %d wins, %d draws (goals %d-%d)"
                   team-a a-wins team-b b-wins draws a-goals b-goals)))))

(defn team-stats->text [{:keys [team venue matches wins draws losses
                                goals-for goals-against win-rate]}]
  (if (zero? matches)
    (format "No matches found for %s with the given filters." team)
    (format "%s record%s:\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Win rate: %s%%"
            team
            (case venue :home " (home)" :away " (away)" "")
            matches wins draws losses goals-for goals-against win-rate)))

(defn standings->text [rows {:keys [competition season limit] :or {limit 20}}]
  (if (empty? rows)
    (format "No %s data found for %s." competition season)
    (str (format "%s %s standings (computed from matches):\n" season competition)
         (str/join "\n"
                   (map-indexed
                    (fn [i {:keys [team points wins draws losses goal-diff]}]
                      (format "%2d. %s - %d pts (%dW %dD %dL, GD %+d)"
                              (inc i) team points wins draws losses goal-diff))
                    (take limit rows))))))

(defn competition-stats->text [{:keys [matches total-goals avg-goals-per-match
                                       home-win-rate away-win-rate draw-rate]}]
  (format (str "Matches: %d\nTotal goals: %d\nAverage goals per match: %s\n"
               "Home win rate: %s%%  |  Away win rate: %s%%  |  Draw rate: %s%%")
          matches total-goals avg-goals-per-match
          home-win-rate away-win-rate draw-rate))

(defn biggest-wins->text [ms]
  (if (empty? ms)
    "No matches found."
    (str/join "\n"
              (map-indexed
               (fn [i m] (format "%d. %s [margin %d]" (inc i) (match-line m) (:margin m)))
               ms))))

(defn player-line [p]
  (format "%s - Overall: %s, Potential: %s, Position: %s, Club: %s, Nationality: %s, Age: %s"
          (:name p) (:overall p) (:potential p) (:position p)
          (:club p) (:nationality p) (:age p)))

(defn players->text [ps]
  (if (empty? ps)
    "No players found."
    (str/join "\n"
              (map-indexed (fn [i p] (str (inc i) ". " (player-line p))) ps))))
