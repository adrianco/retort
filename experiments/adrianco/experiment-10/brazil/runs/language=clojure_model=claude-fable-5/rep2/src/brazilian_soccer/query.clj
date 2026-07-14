(ns brazilian-soccer.query
  "Query and statistics functions over the unified match/player model.
  All functions take plain option maps and return plain data; formatting
  for MCP responses lives in brazilian-soccer.tools."
  (:require [brazilian-soccer.data :as data]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; Competition handling

(defn competition-key
  "Maps a free-form competition query to a canonical competition name,
  or nil when the query is blank/unrecognized (meaning: no filter)."
  [q]
  (when-not (str/blank? (str q))
    (let [n (data/norm q)]
      (cond
        (str/includes? n "serie b")                       "Brasileirão Série B"
        (str/includes? n "serie c")                       "Brasileirão Série C"
        (or (str/includes? n "serie a")
            (str/includes? n "brasileir"))                "Brasileirão Série A"
        (or (str/includes? n "copa do brasil")
            (str/includes? n "brazilian cup")
            (str/includes? n "cup"))                      "Copa do Brasil"
        (str/includes? n "libertadores")                  "Copa Libertadores"
        :else                                             nil))))

;; ---------------------------------------------------------------------------
;; Match search

(defn- stage-matches?
  "Token-prefix match so 'final' hits the final but not 'semifinals',
  while 'semi' still hits 'semifinals' and 'group' hits 'group stage'."
  [q m]
  (let [q-toks (str/split (data/norm q) #" ")
        s-toks (-> (str (:stage m) " round " (:round m)) data/norm (str/split #" "))]
    (and (seq q-toks)
         (every? (fn [qt] (some #(str/starts-with? % qt) s-toks)) q-toks))))

(defn find-matches
  "Filters all matches. Options (all optional):
  :team        either side matches this name
  :opponent    the other side (requires :team)
  :competition free-form competition name
  :season      year (int)
  :date-from / :date-to  ISO date strings (inclusive)
  Returns matches sorted by date descending."
  [{:keys [team opponent competition season date-from date-to stage]}]
  (let [comp-name (when competition (competition-key competition))]
    (cond->> @data/all-matches
      team        (filter #(or (data/team-matches? team (:home %))
                               (data/team-matches? team (:away %))))
      opponent    (filter #(let [pair? (fn [a b]
                                         (and (data/team-matches? a (:home %))
                                              (data/team-matches? b (:away %))))]
                             (or (pair? team opponent) (pair? opponent team))))
      comp-name   (filter #(= comp-name (:competition %)))
      season      (filter #(= season (:season %)))
      date-from   (filter #(and (:date %) (<= (compare date-from (:date %)) 0)))
      date-to     (filter #(and (:date %) (<= (compare (:date %) date-to) 0)))
      stage       (filter #(stage-matches? stage %))
      true        (sort-by #(or (:date %) ""))
      true        reverse
      true        vec)))

(defn- result-for
  "Returns :win :draw or :loss from the perspective of canonical `team`,
  plus goals for/against. Nil when goals are missing."
  [team m]
  (when (and (:home-goals m) (:away-goals m))
    (let [home? (data/team-matches? team (:home m))
          [gf ga] (if home?
                    [(:home-goals m) (:away-goals m)]
                    [(:away-goals m) (:home-goals m)])]
      {:result (cond (> gf ga) :win (= gf ga) :draw :else :loss)
       :gf gf :ga ga})))

;; ---------------------------------------------------------------------------
;; Team statistics & head-to-head

(defn team-stats
  "W/D/L, goals for/against for a team. Options: :season :competition
  :venue (\"home\"/\"away\"/nil for both)."
  [team {:keys [season competition venue]}]
  (let [matches (cond->> (find-matches {:team team :season season
                                        :competition competition})
                  (= venue "home") (filter #(data/team-matches? team (:home %)))
                  (= venue "away") (filter #(data/team-matches? team (:away %))))
        results (keep #(result-for team %) matches)
        tally   (frequencies (map :result results))]
    {:team       team
     :matches    (count results)
     :wins       (get tally :win 0)
     :draws      (get tally :draw 0)
     :losses     (get tally :loss 0)
     :goals-for     (reduce + 0 (map :gf results))
     :goals-against (reduce + 0 (map :ga results))}))

(defn head-to-head
  "All matches between two teams plus a win/draw tally."
  [team1 team2 {:keys [competition season]}]
  (let [matches (find-matches {:team team1 :opponent team2
                               :competition competition :season season})
        verdicts (keep #(result-for team1 %) matches)
        tally (frequencies (map :result verdicts))]
    {:team1 team1 :team2 team2
     :matches matches
     :team1-wins (get tally :win 0)
     :team2-wins (get tally :loss 0)
     :draws      (get tally :draw 0)}))

;; ---------------------------------------------------------------------------
;; Standings

(defn standings
  "League table calculated from match results (3 pts win, 1 draw),
  sorted by the CBF criteria: points, wins, goal difference, goals for."
  [{:keys [season competition]}]
  (let [comp-name (or (competition-key (or competition "")) "Brasileirão Série A")
        matches (filter #(and (= comp-name (:competition %))
                              (= season (:season %))
                              (:home-goals %) (:away-goals %))
                        @data/all-matches)
        update-row (fn [table team gf ga]
                     (update table team
                             (fnil (fn [row]
                                     (-> row
                                         (update :played inc)
                                         (update (cond (> gf ga) :wins
                                                       (= gf ga) :draws
                                                       :else :losses) inc)
                                         (update :gf + gf)
                                         (update :ga + ga)))
                                   {:played 0 :wins 0 :draws 0 :losses 0 :gf 0 :ga 0})))
        table (reduce (fn [t {:keys [home away home-goals away-goals]}]
                        (-> t
                            (update-row home home-goals away-goals)
                            (update-row away away-goals home-goals)))
                      {} matches)]
    {:competition comp-name
     :season season
     :rows (let [rows (map (fn [[team {:keys [wins draws gf ga] :as row}]]
                             (assoc row :team team
                                    :points (+ (* 3 wins) draws)
                                    :goal-diff (- gf ga)))
                           table)
                 ;; A handful of mislabeled rows in the extended dataset can
                 ;; inject teams with one or two matches into a league season;
                 ;; a real participant plays at least half the maximum.
                 max-played (transduce (map :played) max 0 rows)]
             (->> rows
                  (filter #(>= (* 2 (:played %)) max-played))
                  (sort-by (juxt :points :wins :goal-diff :gf))
                  reverse
                  (map-indexed (fn [i row] (assoc row :position (inc i))))
                  vec))}))

;; ---------------------------------------------------------------------------
;; Aggregate statistics

(defn competition-stats
  "Average goals, home/draw/away split for matches with known scores."
  [{:keys [competition season]}]
  (let [comp-name (when competition (competition-key competition))
        matches (cond->> @data/all-matches
                  comp-name (filter #(= comp-name (:competition %)))
                  season    (filter #(= season (:season %)))
                  true      (filter #(and (:home-goals %) (:away-goals %))))
        n (count matches)
        goals (reduce + 0 (map #(+ (:home-goals %) (:away-goals %)) matches))
        outcome (frequencies (map #(compare (:home-goals %) (:away-goals %)) matches))]
    {:competition (or comp-name "all competitions")
     :season season
     :matches n
     :total-goals goals
     :avg-goals (if (pos? n) (/ (double goals) n) 0.0)
     :home-wins (get outcome 1 0)
     :draws     (get outcome 0 0)
     :away-wins (get outcome -1 0)}))

(defn biggest-wins
  "Matches with the largest goal margin, descending."
  [{:keys [competition season limit] :or {limit 10}}]
  (let [comp-name (when competition (competition-key competition))]
    (cond->> @data/all-matches
      true      (filter #(and (:home-goals %) (:away-goals %)))
      comp-name (filter #(= comp-name (:competition %)))
      season    (filter #(= season (:season %)))
      true      (sort-by #(- (abs (- (:home-goals %) (:away-goals %)))))
      true      (take limit)
      true      vec)))

(defn list-teams
  "Distinct canonical team names, optionally per competition/season."
  [{:keys [competition season]}]
  (let [comp-name (when competition (competition-key competition))]
    (->> @data/all-matches
         (filter #(and (or (nil? comp-name) (= comp-name (:competition %)))
                       (or (nil? season) (= season (:season %)))))
         (mapcat (juxt :home :away))
         distinct
         (sort-by data/norm)
         vec)))

;; ---------------------------------------------------------------------------
;; Players

(defn search-players
  "Filters FIFA players; result stays sorted by overall rating descending."
  [{:keys [name nationality club position min-overall limit] :or {limit 20}}]
  (let [name-n (data/norm name)
        nat-n  (data/norm nationality)
        club-n (data/norm club)
        pos-n  (some-> position str/trim str/upper-case)]
    (cond->> @data/all-players
      (seq name-n) (filter #(str/includes? (or (data/norm (:name %)) "") name-n))
      (seq nat-n)  (filter #(= nat-n (data/norm (:nationality %))))
      (seq club-n) (filter #(let [cn (data/norm (:club %))]
                              (and cn (or (str/includes? cn club-n)
                                          (str/includes? (data/norm (data/canonical-team (:club %))) club-n)))))
      pos-n        (filter #(= pos-n (some-> (:position %) str/upper-case)))
      min-overall  (filter #(>= (or (:overall %) 0) min-overall))
      true         (take limit)
      true         vec)))

(defn get-player
  "Best name match for a single player (exact normalized match preferred,
  then substring), nil if none."
  [name]
  (let [n (data/norm name)
        candidates (filter #(str/includes? (or (data/norm (:name %)) "") n)
                           @data/all-players)]
    (or (first (filter #(= n (data/norm (:name %))) candidates))
        (first candidates))))
