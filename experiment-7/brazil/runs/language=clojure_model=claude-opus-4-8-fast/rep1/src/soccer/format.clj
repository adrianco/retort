;; =============================================================================
;; soccer.format — Human-readable formatting of query results
;; -----------------------------------------------------------------------------
;; Project: brazilian-soccer-mcp
;;
;; Context:
;;   The MCP tools return text content to the calling LLM.  This namespace turns
;;   the plain data structures produced by soccer.query into the readable,
;;   spec-shaped strings (match lines, league tables, stat blocks, player lists).
;;   Kept separate from query so the analytics stay pure/testable and the
;;   presentation can evolve independently.
;; =============================================================================
(ns soccer.format
  (:require [clojure.string :as str]))

(defn- pct [x] (format "%.1f%%" (* 100.0 (double x))))

(defn- date-str [d] (if d (str d) "????-??-??"))

(defn match-line
  "One-line summary of a match record, e.g.
   '2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)'."
  [m]
  (let [score (if (and (:home-goals m) (:away-goals m))
                (str (:home-goals m) "-" (:away-goals m))
                "vs")
        ctx   (->> [(:competition m)
                    (when (:round m) (str "Round " (:round m)))
                    (when (and (:season m) (not (:round m))) (str (:season m)))]
                   (remove nil?)
                   (str/join ", "))]
    (format "%s: %s %s %s (%s)"
            (date-str (:date m)) (:home m) score (:away m) ctx)))

(defn format-matches
  "Format a match search result, capping the listing at `show` lines."
  [matches & {:keys [show title] :or {show 25}}]
  (let [n* (count matches)]
    (if (zero? n*)
      "No matches found for those criteria."
      (str (when title (str title "\n"))
           (str/join "\n" (map #(str "- " (match-line %)) (take show matches)))
           (when (> n* show)
             (format "\n... (%d more match%s in dataset)"
                     (- n* show) (if (= 1 (- n* show)) "" "es")))
           (format "\n\nTotal: %d match%s." n* (if (= 1 n*) "" "es"))))))

(defn format-team-stats [s]
  (let [scope (->> [(when (:season s) (str (:season s)))
                    (or (:competition s) "all competitions")
                    (case (:venue s) :home "home" :away "away" "")]
                   (remove str/blank?)
                   (str/join " "))]
    (str (format "%s record (%s):\n" (:team s) scope)
         (format "- Matches: %d\n" (:matches s))
         (format "- Wins: %d, Draws: %d, Losses: %d\n"
                 (:wins s) (:draws s) (:losses s))
         (format "- Goals For: %d, Goals Against: %d (diff %+d)\n"
                 (:goals-for s) (:goals-against s) (:goal-diff s))
         (format "- Points: %d\n" (:points s))
         (format "- Win rate: %s" (pct (:win-rate s))))))

(defn format-head-to-head [h]
  (str (format "%s vs %s head-to-head (%d matches in dataset):\n"
               (:team-a h) (:team-b h) (:matches h))
       (format "- %s wins: %d\n" (:team-a h) (:a-wins h))
       (format "- %s wins: %d\n" (:team-b h) (:b-wins h))
       (format "- Draws: %d\n" (:draws h))
       (format "- Goals: %s %d - %d %s\n"
               (:team-a h) (:a-goals h) (:b-goals h) (:team-b h))
       (when (seq (:match-list h))
         (str "\nRecent meetings:\n"
              (str/join "\n" (map #(str "- " (match-line %))
                                  (take 10 (:match-list h))))))))

(defn format-standings [rows competition season & {:keys [show] :or {show 20}}]
  (if (empty? rows)
    (format "No standings could be computed for %s %s." competition season)
    (str (format "%s %s standings (calculated from matches):\n"
                 season competition)
         (str/join "\n"
           (map (fn [r]
                  (format "%2d. %-22s %3d pts (%dW %dD %dL, GF %d GA %d, GD %+d)"
                          (:position r) (:team r) (:points r)
                          (:wins r) (:draws r) (:losses r)
                          (:goals-for r) (:goals-against r) (:goal-diff r)))
                (take show rows))))))

(defn format-competition-stats [s]
  (let [scope (->> [(when (:season s) (str (:season s)))
                    (or (:competition s) "all competitions")]
                   (remove str/blank?) (str/join " "))]
    (str (format "Statistics for %s:\n" scope)
         (format "- Matches: %d\n" (:matches s))
         (format "- Total goals: %d\n" (:total-goals s))
         (format "- Average goals per match: %.2f\n" (:goals-per-match s))
         (format "- Home win rate: %s\n" (pct (:home-win-rate s)))
         (format "- Away win rate: %s\n" (pct (:away-win-rate s)))
         (format "- Draw rate: %s" (pct (:draw-rate s))))))

(defn format-biggest-wins [matches]
  (if (empty? matches)
    "No matches found."
    (str "Biggest victories (by goal margin):\n"
         (str/join "\n"
           (map-indexed
            (fn [i m] (format "%d. %s" (inc i) (match-line m)))
            matches)))))

(defn player-line [p]
  (format "%s - Overall: %s, Potential: %s, Position: %s, Club: %s, Age: %s, Nat: %s"
          (:name p) (:overall p) (:potential p) (or (:position p) "?")
          (or (:club p) "?") (:age p) (:nationality p)))

(defn format-players [players & {:keys [show title] :or {show 25}}]
  (let [n* (count players)]
    (if (zero? n*)
      "No players found for those criteria."
      (str (when title (str title "\n"))
           (str/join "\n"
             (map-indexed (fn [i p] (format "%d. %s" (inc i) (player-line p)))
                          (take show players)))
           (when (> n* show) (format "\n... (%d more)" (- n* show)))
           (format "\n\nTotal: %d player%s." n* (if (= 1 n*) "" "s"))))))

(defn format-club-summary [rows & {:keys [nationality]}]
  (if (empty? rows)
    "No clubs found."
    (str (format "%splayers by club:\n" (if nationality (str nationality " ") ""))
         (str/join "\n"
           (map (fn [r] (format "- %s: %d players (avg rating: %.1f)"
                                (:club r) (:players r) (:avg-overall r)))
                rows)))))
