(ns brazilian-soccer.format
  "Rendering of query results as the plain text an MCP client shows to an LLM.

  CONTEXT
  -------
  MCP tools return text content, so every tool answer is rendered here.  The
  wording follows the answer formats in the specification: a match line reads

      2019-10-27: Flamengo 5-0 Grêmio (Brasileirão Série A, Round 27)

  and a team record reads

      Matches: 19 | Wins: 11, Draws: 5, Losses: 3 | GF: 28, GA: 15 | Win rate: 57.9%

  Numbers are always accompanied by what they were calculated from, because the
  dataset is a sample of Brazilian football, not the complete record - standings
  and averages are derived from the matches actually present in the CSVs."
  (:require [clojure.string :as str]
            [brazilian-soccer.data :as data]))

(defn pct [x] (format "%.1f%%" (* 100.0 (or x 0.0))))
(defn dec2 [x] (format "%.2f" (double (or x 0.0))))

(defn match-line
  "One match as a single line."
  ([m] (match-line m nil))
  ([m {:keys [show-competition? show-sources?] :or {show-competition? true}}]
   (let [score (if (:played? m)
                 (str (:home-goals m) "-" (:away-goals m))
                 "(no score in dataset)")
         ctx (cond-> []
               show-competition? (conj (:competition-name m))
               (:round m)  (conj (str "Round " (:round m)))
               (:stage m)  (conj (str/capitalize (:stage m)))
               (and (not show-competition?) (:season m)) (conj (str (:season m)))
               (:venue m)  (conj (:venue m))
               (:derby m)  (conj (str "derby: " (:derby m)))
               show-sources? (conj (str "sources: " (str/join "+" (:sources m)))))]
     (str (or (:date m) "date unknown") ": "
          (:home m) " " score " " (:away m)
          (when (seq ctx) (str " (" (str/join ", " ctx) ")"))))))

(defn match-list [matches opts]
  (if (empty? matches)
    "  (no matches)"
    (str/join "\n" (map #(str "  - " (match-line % opts)) matches))))

(defn record-line [r]
  (str "Matches: " (:matches r)
       " | Wins: " (:wins r) ", Draws: " (:draws r) ", Losses: " (:losses r)
       " | Goals For: " (:goals-for r) ", Goals Against: " (:goals-against r)
       " (" (if (neg? (:goal-difference r)) "" "+") (:goal-difference r) ")"
       " | Points: " (:points r)
       " | Win rate: " (pct (:win-rate r))))

(defn filters-line [{:keys [competition season season-from season-to date-from date-to venue]}]
  (let [parts (cond-> []
                competition (conj (data/competition-name competition))
                season      (conj (str "season " season))
                season-from (conj (str "from " season-from))
                season-to   (conj (str "to " season-to))
                date-from   (conj (str "after " date-from))
                date-to     (conj (str "before " date-to))
                (and venue (not= venue :any)) (conj (str (clojure.core/name venue) " matches only")))]
    (if (seq parts) (str/join ", " parts) "all competitions and seasons")))

;; ---------------------------------------------------------------------------
;; Tool renderings
;; ---------------------------------------------------------------------------

(defn matches-answer [{:keys [title matches total filters]}]
  (str title "\n"
       (when filters (str "Filter: " filters "\n"))
       (match-list matches nil)
       "\n\n" (count matches) " shown"
       (when (and total (> total (count matches))) (str " of " total " in the dataset"))
       "."))

(defn team-stats-answer [{:keys [team overall home away by-competition by-season
                                 biggest-win recent filters]}]
  (str (:display team) (when (:state team) (str " (" (:state team) ")"))
       " - " filters "\n"
       (record-line overall) "\n"
       "  Home: " (record-line home) "\n"
       "  Away: " (record-line away) "\n"
       (when (> (count by-competition) 1)
         (str "\nBy competition:\n"
              (str/join "\n" (for [[c r] by-competition]
                               (str "  - " (data/competition-name c) ": "
                                    (:matches r) " matches, " (:wins r) "W " (:draws r) "D "
                                    (:losses r) "L, " (:goals-for r) ":" (:goals-against r))))
              "\n"))
       (when (> (count by-season) 1)
         (str "\nBy season:\n"
              (str/join "\n" (for [[s r] by-season]
                               (str "  - " s ": " (:matches r) " matches, "
                                    (:wins r) "W " (:draws r) "D " (:losses r) "L, "
                                    (:points r) " pts")))
              "\n"))
       (when biggest-win (str "\nBiggest win: " (match-line biggest-win) "\n"))
       (when (seq recent)
         (str "\nMost recent matches:\n" (match-list recent nil)))))

(defn head-to-head-answer [{:keys [team-a team-b matches played a-record b-record draws
                                   by-competition first-meeting last-meeting biggest]}
                           {:keys [limit filters]}]
  (let [a (:display team-a) b (:display team-b)]
    (if (zero? played)
      (str "No matches between " a " and " b " in the dataset (" filters ").")
      (str a " vs " b " - head-to-head (" filters ")\n"
           "Matches: " played
           " | " a " wins: " (:wins a-record)
           " | " b " wins: " (:wins b-record)
           " | Draws: " draws "\n"
           "Goals: " a " " (:goals-for a-record) " - " (:goals-for b-record) " " b "\n"
           "First meeting: " (match-line first-meeting) "\n"
           "Last meeting:  " (match-line last-meeting) "\n"
           (when biggest (str "Biggest margin: " (match-line biggest) "\n"))
           "\nBy competition:\n"
           (str/join "\n" (for [[c agg] by-competition
                                :let [ra (:a agg) rb (:b agg)]]
                            (str "  - " (data/competition-name c) ": " (:matches agg)
                                 (if (= 1 (:matches agg)) " match, " " matches, ")
                                 a " " (:wins ra) "W - " (:wins rb) "W " b
                                 ", " (:draws ra) " draws")))
           "\n\nMatches (most recent first):\n"
           (match-list (take (or limit 20) matches) nil)
           (when (> (count matches) (or limit 20))
             (str "\n  ... " (- (count matches) (or limit 20)) " more"))))))

(defn standings-answer [{:keys [competition season table match-count]}]
  (let [teams (count table)
        relegation (when (and (= :serie-a competition) (>= teams 20)) 4)]
    (str (data/competition-name competition) " " season
         " - table calculated from " match-count " matches in the dataset\n"
         (format "%-4s %-26s %3s %3s %3s %3s %4s %4s %4s %5s"
                 "#" "Team" "P" "W" "D" "L" "GF" "GA" "GD" "Pts") "\n"
         (str/join "\n"
                   (for [r table]
                     (str (format "%-4s %-26s %3s %3s %3s %3s %4s %4s %4s %5s"
                                  (str (:position r)) (:team r) (:matches r) (:wins r)
                                  (:draws r) (:losses r) (:goals-for r) (:goals-against r)
                                  (str (when (pos? (:goal-difference r)) "+") (:goal-difference r))
                                  (:points r))
                          (cond
                            (= 1 (:position r)) "  <- champion (by points)"
                            (and relegation (> (:position r) (- teams relegation))) "  <- relegation zone"
                            :else ""))))
         "\n\nCalculated from match results only: 3 points per win, ranked on"
         " points, wins, goal difference, goals for.")))

(defn rankings-answer [{:keys [metric venue min-matches rows]} filters]
  (str "Clubs ranked by " (clojure.core/name metric)
       (when-not (= :any venue) (str " (" (clojure.core/name venue) " matches only)"))
       " - " filters "\n"
       "Minimum " min-matches " matches played.\n"
       (str/join "\n"
                 (for [r rows]
                   (str "  " (:position r) ". " (:team r) " - "
                        (case metric
                          :points-per-match (str (dec2 (:points-per-match r)) " pts/match")
                          :win-rate (str (pct (:win-rate r)) " win rate")
                          :goals-per-match (str (dec2 (:goals-per-match r)) " goals/match")
                          (str (get r metric) " " (clojure.core/name metric)))
                        " (" (record-line r) ")")))))

(defn competition-summary-answer [{:keys [competition season matches goals goals-per-match
                                          home-wins away-wins draws home-win-rate draw-rate
                                          away-win-rate seasons teams biggest-win
                                          highest-scoring top-scoring-teams]}]
  (str (if competition (data/competition-name competition) "All competitions")
       (when season (str " " season)) " - statistics from the dataset\n"
       "Matches: " matches
       (when (and (not season) (seq seasons))
         (str " across seasons " (first seasons) "-" (last seasons)))
       "\n"
       "Distinct teams: " teams "\n"
       "Goals: " goals " (" (dec2 goals-per-match) " per match)\n"
       "Home wins: " home-wins " (" (pct home-win-rate) ")"
       " | Away wins: " away-wins " (" (pct away-win-rate) ")"
       " | Draws: " draws " (" (pct draw-rate) ")\n"
       (when biggest-win (str "Biggest margin: " (match-line biggest-win) "\n"))
       (when highest-scoring (str "Highest scoring: " (match-line highest-scoring) "\n"))
       (when (seq top-scoring-teams)
         (str "\nTop scoring teams:\n"
              (str/join "\n" (map-indexed (fn [i t] (str "  " (inc i) ". " (:team t) " - " (:goals t) " goals"))
                                          top-scoring-teams))))
       "\n\nNote: goalscorer data is not part of any provided dataset, so individual"
       " top scorers cannot be derived; team totals are shown instead."))

(defn player-line [p]
  (str (:name p)
       " - Overall: " (:overall p)
       ", Potential: " (:potential p)
       ", Position: " (or (:position p) "n/a")
       ", Age: " (:age p)
       ", Club: " (or (:club p) "free agent")
       ", Nationality: " (:nationality p)))

(defn players-answer [{:keys [title players total note]}]
  (str title "\n"
       (if (empty? players)
         "  (no players matched)"
         (str/join "\n" (map-indexed (fn [i p] (str "  " (inc i) ". " (player-line p))) players)))
       "\n\n" (count players) " shown of " total " matching players."
       (when note (str "\n" note))))

(defn player-profile-answer [{:keys [player team-id alternatives]} team]
  (let [p player]
    (str (:name p) " - FIFA 19 player profile\n"
         "Nationality: " (:nationality p) " | Age: " (:age p)
         " | Position: " (or (:position p) "n/a")
         (when (:jersey p) (str " | Shirt: " (:jersey p))) "\n"
         "Club: " (or (:club p) "free agent")
         (when team-id (str " (linked to " (:display team) " in the match data)")) "\n"
         "Overall: " (:overall p) " | Potential: " (:potential p)
         " | Value: " (or (:value p) "n/a") " | Wage: " (or (:wage p) "n/a") "\n"
         "Height: " (or (:height p) "n/a") " | Weight: " (or (:weight p) "n/a")
         " | Preferred foot: " (or (:foot p) "n/a") "\n"
         (when (seq (:skills p))
           (str "Top attributes: "
                (->> (:skills p) (sort-by (comp - val)) (take 8)
                     (map (fn [[k v]] (str k " " v)))
                     (str/join ", "))
                "\n"))
         (when (seq alternatives)
           (str "\nOther players matching that name: "
                (str/join ", " (map #(str (:name %) " (" (:club %) ", " (:overall %) ")")
                                    alternatives)))))))

(defn squad-answer [{:keys [clubs players player-count brazilians avg-overall nationalities]}
                    team]
  (str "Squad: " (str/join " / " clubs)
       (when team (str " - " (:display team) " in the match data")) "\n"
       "Players: " player-count " | Brazilians: " brazilians
       " | Average overall rating: " (dec2 avg-overall) "\n"
       "Nationalities: " (str/join ", " (map (fn [[n c]] (str n " " c)) nationalities)) "\n\n"
       (str/join "\n" (map-indexed (fn [i p] (str "  " (inc i) ". " (player-line p)))
                                   (take 30 players)))))

(defn teams-answer [teams]
  (str "Clubs in the dataset (" (count teams) " shown)\n"
       (str/join "\n"
                 (for [t teams]
                   (str "  - " (:display t)
                        (when (:state t) (str " [" (:state t) "]"))
                        (when (:country t) (str " [" (:country t) "]"))
                        " - " (:match-count t) " matches, competitions: "
                        (str/join ", " (map data/competition-name (:competitions t)))
                        "\n    id: " (:id t)
                        " | spellings in the data: " (str/join " / " (:variants t)))))))

(defn dataset-answer [{:keys [data-dir sources stats matches played teams players
                              linked-clubs by-competition date-range]}]
  (str "Brazilian soccer knowledge graph\n"
       "Data directory: " data-dir "\n"
       "Rows read: " (:raw-match-rows stats)
       " -> unique matches after de-duplicating overlapping files: " matches
       " (" played " with a score)\n"
       "Clubs: " teams " | FIFA players: " players
       " | FIFA squads linked to clubs in the match data: " linked-clubs "\n"
       "Match dates: " (first date-range) " to " (second date-range) "\n\n"
       "Competitions:\n"
       (str/join "\n" (for [c by-competition]
                        (str "  - " (:name c) ": " (:matches c) " matches, seasons "
                             (first (:seasons c)) "-" (second (:seasons c)))))
       "\n\nSource files:\n"
       (str/join "\n" (for [s sources]
                        (str "  - " (:file s) " - " (:title s)
                             "\n    license: " (:license s) " | " (:url s))))
       "\n\nRows per file: "
       (str/join ", " (for [[k v] (sort-by key (:rows-by-source stats))]
                        (str (clojure.core/name k) " " v)))
       "\nMatches appearing in more than one file are merged, so a fixture is"
       " counted once while keeping the round, stadium and shot/corner detail"
       " each file contributes."))
