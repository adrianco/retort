;; =============================================================================
;; brazilian-soccer.format
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   Turns the plain-data results from brazilian-soccer.queries into the
;;   human-readable text blocks shown in TASK.md's "Example answer format"
;;   sections. The MCP server returns these strings as tool-call text content so
;;   the connected LLM (and a human reading the transcript) sees tidy answers.
;;
;;   Kept separate from queries.clj so the analytics stay pure/testable and the
;;   presentation can evolve independently.
;; =============================================================================
(ns brazilian-soccer.format
  (:require [clojure.string :as str]
            [brazilian-soccer.queries :as q]))

(defn- pct [x] (format "%.1f%%" (* 100.0 (double x))))

(defn- score [m]
  (str (or (:home-goals m) "?") "-" (or (:away-goals m) "?")))

(defn- comp-tag [m]
  (let [bits (remove nil? [(:competition m)
                           (when (:round m) (str "Round " (:round m)))
                           (:stage m)
                           (:season m)])]
    (str "(" (str/join ", " bits) ")")))

(defn match-line [m]
  (str (or (:date m) "????-??-??") ": "
       (:home m) " " (score m) " " (:away m) " " (comp-tag m)))

;; ---------------------------------------------------------------------------

(defn format-matches [matches {:keys [title]}]
  (if (empty? matches)
    "No matches found for that query."
    (str (when title (str title "\n"))
         (str/join "\n" (map #(str "- " (match-line %)) matches))
         "\n\nTotal: " (count matches) " match(es).")))

(defn format-head-to-head [h]
  (if (zero? (:total h))
    (str "No matches found between " (:team-a h) " and " (:team-b h) ".")
    (str (:team-a h) " vs " (:team-b h) " — head-to-head (provided data):\n"
         "- Matches: " (:total h) "\n"
         "- " (:team-a h) " wins: " (:a-wins h) "\n"
         "- " (:team-b h) " wins: " (:b-wins h) "\n"
         "- Draws: " (:draws h) "\n"
         "- Goals: " (:team-a h) " " (:a-goals h) " — " (:b-goals h) " " (:team-b h) "\n\n"
         "Recent meetings:\n"
         (str/join "\n" (map #(str "- " (match-line %)) (take 10 (:matches h)))))))

(defn format-team-stats [s]
  (if (nil? s)
    "No matches found for that team / filters."
    (let [scope (->> [(when (:competition s) (:competition s))
                      (when (:season s) (str "season " (:season s)))]
                     (remove nil?) (str/join ", "))
          wr (if (pos? (:matches s)) (/ (:wins s) (double (:matches s))) 0.0)]
      (str (:team s) " record" (when (seq scope) (str " (" scope ")")) ":\n"
           "- Matches: " (:matches s) "\n"
           "- Wins: " (:wins s) ", Draws: " (:draws s) ", Losses: " (:losses s) "\n"
           "- Goals For: " (:goals-for s) ", Goals Against: " (:goals-against s)
           " (diff " (let [d (- (:goals-for s) (:goals-against s))] (if (pos? d) (str "+" d) d)) ")\n"
           "- Win rate: " (pct wr)))))

(defn format-players [players {:keys [title]}]
  (if (empty? players)
    "No players found for that query."
    (str (when title (str title "\n"))
         (str/join "\n"
                   (map-indexed
                    (fn [i p]
                      (format "%d. %s — Overall: %s, Position: %s, Club: %s%s"
                              (inc i) (:name p) (or (:overall p) "?")
                              (or (:position p) "?") (or (:club p) "Free agent")
                              (if (:nationality p) (str " [" (:nationality p) "]") "")))
                    players))
         "\n\nShowing " (count players) " player(s).")))

(defn format-standings [rows {:keys [competition season]}]
  (if (empty? rows)
    (str "No standings available for " competition " " season ".")
    (str competition " " season " — table (calculated from matches):\n"
         (str/join "\n"
                   (map (fn [r]
                          (format "%2d. %-22s %3d pts  (%2dW %2dD %2dL, GF %d GA %d, GD %+d)"
                                  (:rank r) (:team r) (:points r)
                                  (:wins r) (:draws r) (:losses r)
                                  (:gf r) (:ga r) (:gd r)))
                        rows)))))

(defn format-league-stats [s {:keys [competition season]}]
  (let [scope (->> [competition (when season (str season))]
                   (remove nil?) (str/join " "))]
    (str "Statistics" (when (seq scope) (str " for " scope)) ":\n"
         "- Matches: " (:matches s) " (with scores: " (:scored-matches s) ")\n"
         "- Total goals: " (:total-goals s) "\n"
         "- Average goals per match: " (format "%.2f" (:avg-goals s)) "\n"
         "- Home win rate: " (pct (:home-win-rate s)) "\n"
         "- Away win rate: " (pct (:away-win-rate s)) "\n"
         "- Draw rate: " (pct (:draw-rate s)))))

(defn format-biggest-wins [matches {:keys [title]}]
  (if (empty? matches)
    "No matches found for that query."
    (str (or title "Biggest victories (provided data):") "\n"
         (str/join "\n"
                   (map-indexed
                    (fn [i m] (str (inc i) ". " (match-line m)
                                   "  [margin " (:margin m) "]"))
                    matches)))))

(defn format-competitions [comps]
  (str "Competitions in the knowledge graph:\n"
       (str/join "\n"
                 (map (fn [c]
                        (let [ss (:seasons c)]
                          (format "- %s: %d matches, %d teams, seasons %s–%s"
                                  (:competition c) (:matches c) (:teams c)
                                  (str (first ss)) (str (last ss)))))
                      comps))))
