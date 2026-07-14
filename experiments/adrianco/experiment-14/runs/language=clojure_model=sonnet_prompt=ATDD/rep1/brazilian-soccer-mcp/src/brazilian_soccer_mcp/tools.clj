(ns brazilian-soccer-mcp.tools
  "MCP tool implementations for Brazilian soccer data queries.
   Each function takes the loaded data map and an arguments map,
   and returns a structured result map."
  (:require [clojure.string :as str]
            [brazilian-soccer-mcp.normalize :as norm]))

;; ---------------------------------------------------------------------------
;; Internal helpers
;; ---------------------------------------------------------------------------

(defn- all-matches
  "Concatenate all match datasets into a single seq."
  [data]
  (concat (:brasileirao-matches data)
          (:cup-matches data)
          (:libertadores-matches data)
          (:historical-brasileirao data)
          (:br-football data)))

(defn- competition-filter
  "Return a predicate matching the given competition keyword, or nil if no competition."
  [competition]
  (when competition
    (let [c (str/lower-case (str competition))]
      (cond
        (or (str/includes? c "brasileirao")
            (str/includes? c "serie-a")
            (str/includes? c "serie a"))
        #(= (:competition %) "brasileirao")

        (or (str/includes? c "copa-do-brasil")
            (str/includes? c "copa do brasil")
            (str/includes? c "cup"))
        #(= (:competition %) "copa-do-brasil")

        (str/includes? c "libertadores")
        #(= (:competition %) "libertadores")

        :else
        #(str/includes? (str/lower-case (str (:competition %))) c)))))

(defn- team-in-match?
  "True if the given team name appears in this match (home or away)."
  [team match]
  (or (norm/team-matches? team (:home-team match))
      (norm/team-matches? team (:away-team match))))

(defn- both-teams-in-match?
  "True if both team1 and team2 appear in the match."
  [team1 team2 match]
  (let [h (:home-team match)
        a (:away-team match)]
    (or (and (norm/team-matches? team1 h) (norm/team-matches? team2 a))
        (and (norm/team-matches? team2 h) (norm/team-matches? team1 a)))))

(defn- date-in-range?
  "True if match date falls within [from, to] (both inclusive, yyyy-MM-dd strings)."
  [date-from date-to match]
  (let [d (str (:date match))]
    (and (or (nil? date-from) (>= (compare d date-from) 0))
         (or (nil? date-to)   (<= (compare d date-to)   0)))))

(defn- apply-match-filters
  "Filter matches seq by the given criteria map.
   Arg order: opts first, matches second — so it works in ->> chains."
  [{:keys [team team1 team2 competition season date-from date-to]} matches]
  (let [season-int (when season
                     (if (string? season)
                       (Integer/parseInt season)
                       (int season)))
        comp-pred  (or (competition-filter competition) (constantly true))]
    (cond->> matches
      team        (filter #(team-in-match? team %))
      (and team1 team2) (filter #(both-teams-in-match? team1 team2 %))
      competition (filter comp-pred)
      season-int  (filter #(= (:season %) season-int))
      (or date-from date-to) (filter #(date-in-range? date-from date-to %)))))

;; ---------------------------------------------------------------------------
;; 1. find-matches
;; ---------------------------------------------------------------------------

(defn find-matches
  "Find matches matching the given criteria.
   Args: {:team :team1 :team2 :competition :season :date-from :date-to :limit}
   Returns: {:matches [...] :total-found N}"
  [data {:keys [limit] :as args}]
  (let [limit   (or limit 200)
        matches (->> (all-matches data)
                     (apply-match-filters args)
                     (sort-by :date #(compare %2 %1))
                     (take limit)
                     vec)]
    {:matches     matches
     :total-found (count matches)}))

;; ---------------------------------------------------------------------------
;; 2. get-team-stats
;; ---------------------------------------------------------------------------

(defn get-team-stats
  "Compute team statistics for the given team, competition, season, and venue.
   Args: {:team :competition :season :venue} (venue: 'home'|'away'|nil for all)
   Returns: {:team :matches-played :wins :draws :losses :goals-for :goals-against :win-rate}"
  [data {:keys [team competition season venue]}]
  (let [all   (apply-match-filters {:team team :competition competition :season season}
                                   (all-matches data))
        relevant (case (and venue (str/lower-case venue))
                   "home"  (filter #(norm/team-matches? team (:home-team %)) all)
                   "away"  (filter #(norm/team-matches? team (:away-team %)) all)
                   all)
        wins   (count (filter (fn [m]
                                (let [home? (norm/team-matches? team (:home-team m))
                                      hg    (or (:home-goal m) 0)
                                      ag    (or (:away-goal m) 0)]
                                  (if home? (> hg ag) (> ag hg))))
                              relevant))
        draws  (count (filter (fn [m]
                                (= (or (:home-goal m) 0)
                                   (or (:away-goal m) 0)))
                              relevant))
        losses (count (filter (fn [m]
                                (let [home? (norm/team-matches? team (:home-team m))
                                      hg    (or (:home-goal m) 0)
                                      ag    (or (:away-goal m) 0)]
                                  (if home? (< hg ag) (< ag hg))))
                              relevant))
        gf     (reduce (fn [acc m]
                         (+ acc (if (norm/team-matches? team (:home-team m))
                                  (or (:home-goal m) 0)
                                  (or (:away-goal m) 0))))
                       0 relevant)
        ga     (reduce (fn [acc m]
                         (+ acc (if (norm/team-matches? team (:home-team m))
                                  (or (:away-goal m) 0)
                                  (or (:home-goal m) 0))))
                       0 relevant)
        played (count relevant)]
    {:team            team
     :matches-played  played
     :wins            wins
     :draws           draws
     :losses          losses
     :goals-for       gf
     :goals-against   ga
     :win-rate        (if (pos? played) (double (/ wins played)) 0.0)}))

;; ---------------------------------------------------------------------------
;; 3. find-players
;; ---------------------------------------------------------------------------

(defn find-players
  "Find FIFA players matching the given criteria.
   Args: {:name :nationality :club :position :min-overall :sort-key :limit}
   Returns: {:players [...] :total-found N}"
  [data {:keys [name nationality club position min-overall sort-key limit]
         :or {limit 50 sort-key "overall"}}]
  (let [key-fn (case (str sort-key)
                 "overall"   #(- (or (:overall %) 0))
                 "potential" #(- (or (:potential %) 0))
                 "age"       :age
                 #(- (or (:overall %) 0)))
        players (->> (:fifa-players data)
                     (filter (fn [p]
                               (and (or (nil? name)
                                        (str/includes? (str/lower-case (str (:name p)))
                                                       (str/lower-case name)))
                                    (or (nil? nationality)
                                        (str/includes? (str/lower-case (str (:nationality p)))
                                                       (str/lower-case nationality)))
                                    (or (nil? club)
                                        (str/includes? (str/lower-case (str (:club p)))
                                                       (str/lower-case club)))
                                    (or (nil? position)
                                        (str/includes? (str/lower-case (str (:position p)))
                                                       (str/lower-case position)))
                                    (or (nil? min-overall)
                                        (>= (or (:overall p) 0) min-overall)))))
                     (sort-by key-fn)
                     (take limit)
                     vec)]
    {:players     players
     :total-found (count players)}))

;; ---------------------------------------------------------------------------
;; 4. get-head-to-head
;; ---------------------------------------------------------------------------

(defn get-head-to-head
  "Compute head-to-head record between two teams.
   Args: {:team1 :team2 :competition :season}
   Returns: {:team1 :team2 :team1-wins :team2-wins :draws :total-matches :matches}"
  [data {:keys [team1 team2 competition season]}]
  (let [season-int (when season (if (string? season) (Integer/parseInt season) (int season)))
        comp-pred  (or (competition-filter competition) (constantly true))
        matches (->> (all-matches data)
                     (filter #(both-teams-in-match? team1 team2 %))
                     (filter comp-pred)
                     (filter #(or (nil? season-int) (= (:season %) season-int)))
                     (sort-by :date #(compare %2 %1))
                     vec)
        t1-wins (count (filter (fn [m]
                                 (let [h1? (norm/team-matches? team1 (:home-team m))
                                       hg  (or (:home-goal m) 0)
                                       ag  (or (:away-goal m) 0)]
                                   (if h1? (> hg ag) (> ag hg))))
                               matches))
        draws   (count (filter #(= (or (:home-goal %) 0)
                                   (or (:away-goal %) 0))
                               matches))
        t2-wins (- (count matches) t1-wins draws)]
    {:team1         team1
     :team2         team2
     :team1-wins    t1-wins
     :team2-wins    t2-wins
     :draws         draws
     :total-matches (count matches)
     :matches       (take 20 matches)}))

;; ---------------------------------------------------------------------------
;; 5. get-standings
;; ---------------------------------------------------------------------------

(defn- add-match-to-team
  "Update a team's entry in the standings table with the result of one match."
  [table team gf ga win? draw? loss?]
  (update table team
          (fn [s]
            (let [s (or s {:team team :played 0 :wins 0 :draws 0
                           :losses 0 :goals-for 0 :goals-against 0})]
              (-> s
                  (update :played + 1)
                  (update :wins + (if win? 1 0))
                  (update :draws + (if draw? 1 0))
                  (update :losses + (if loss? 1 0))
                  (update :goals-for + gf)
                  (update :goals-against + ga))))))

(defn- compute-standings
  "Calculate a league table from a collection of matches."
  [matches]
  (let [table (reduce
               (fn [acc match]
                 (let [ht  (:home-team match)
                       at  (:away-team match)
                       hg  (or (:home-goal match) 0)
                       ag  (or (:away-goal match) 0)
                       hw? (> hg ag)
                       aw? (> ag hg)
                       d?  (= hg ag)]
                   (-> acc
                       (add-match-to-team ht hg ag hw? d? aw?)
                       (add-match-to-team at ag hg aw? d? hw?))))
               {} matches)]
    (->> (vals table)
         (map #(assoc % :points (+ (* 3 (:wins %)) (:draws %))
                      :goal-diff (- (:goals-for %) (:goals-against %))))
         (sort-by (juxt (comp - :points) (comp - :goal-diff) (comp - :goals-for)))
         (map-indexed (fn [i t] (assoc t :position (inc i)
                                       :matches-played (:played t))))
         vec)))

(defn get-standings
  "Calculate competition standings for a given season.
   Args: {:season :competition}
   Returns: {:season :competition :standings [...]}"
  [data {:keys [season competition]}]
  (let [comp-pred   (or (competition-filter competition) (constantly true))
        season-int  (if (string? season) (Integer/parseInt season) (int season))
        matches (->> (all-matches data)
                     (filter comp-pred)
                     (filter #(= (:season %) season-int)))
        standings (compute-standings matches)]
    {:season      season
     :competition (or competition "all")
     :standings   standings}))

;; ---------------------------------------------------------------------------
;; 6. get-statistics
;; ---------------------------------------------------------------------------

(defn get-statistics
  "Compute aggregate statistics.
   Args: {:stat-type :competition :season :limit}
   Stat types: 'biggest-wins' 'goals-per-match' 'home-away-record' 'top-scoring-teams'
   Returns: varies by stat-type"
  [data {:keys [stat-type competition season limit]
         :or {limit 10}}]
  (let [comp-pred    (or (competition-filter competition) (constantly true))
        season-int   (when season (if (string? season) (Integer/parseInt season) (int season)))
        base-matches (cond->> (filter comp-pred (all-matches data))
                       season-int (filter #(= (:season %) season-int)))]
    (case (str stat-type)
      "biggest-wins"
      (let [wins (->> base-matches
                      (filter #(and (:home-goal %) (:away-goal %)))
                      (sort-by #(Math/abs (- (:home-goal %) (:away-goal %))) >)
                      (take limit)
                      vec)]
        {:stat-type "biggest-wins"
         :results   wins})

      "goals-per-match"
      (let [with-goals (filter #(and (:home-goal %) (:away-goal %)) base-matches)
            total      (count with-goals)
            goal-sum   (reduce #(+ %1 (:home-goal %2) (:away-goal %2)) 0 with-goals)]
        {:stat-type              "goals-per-match"
         :total-matches          total
         :total-goals            goal-sum
         :average-goals-per-match (if (pos? total) (double (/ goal-sum total)) 0.0)})

      "home-away-record"
      (let [with-goals (filter #(and (:home-goal %) (:away-goal %)) base-matches)
            total      (count with-goals)
            home-wins  (count (filter #(> (:home-goal %) (:away-goal %)) with-goals))
            away-wins  (count (filter #(< (:home-goal %) (:away-goal %)) with-goals))
            draws      (- total home-wins away-wins)]
        {:stat-type      "home-away-record"
         :total-matches  total
         :home-wins      home-wins
         :away-wins      away-wins
         :draws          draws
         :home-win-rate  (if (pos? total) (double (/ home-wins total)) 0.0)
         :away-win-rate  (if (pos? total) (double (/ away-wins total)) 0.0)
         :draw-rate      (if (pos? total) (double (/ draws total)) 0.0)})

      "top-scoring-teams"
      (let [team-goals (reduce (fn [acc m]
                                 (-> acc
                                     (update (:home-team m) (fnil + 0) (or (:home-goal m) 0))
                                     (update (:away-team m) (fnil + 0) (or (:away-goal m) 0))))
                               {} base-matches)
            results (->> team-goals
                         (map (fn [[t g]] {:team t :goals g}))
                         (sort-by :goals >)
                         (take limit)
                         vec)]
        {:stat-type "top-scoring-teams"
         :results   results})

      {:stat-type stat-type
       :error     (str "Unknown stat-type: " stat-type)})))
