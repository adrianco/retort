(ns brazil-soccer.queries
  "Query functions over the database map produced by brazil-soccer.data/load-db.
  Team, club and competition arguments may be given in any of the spellings the
  datasets use; they are normalized here."
  (:require [clojure.string :as str]
            [brazil-soccer.data :as data]
            [brazil-soccer.teams :as teams]))

(defn- ->competition
  "Resolves a competition argument, throwing for labels that match nothing."
  [raw]
  (when raw
    (or (teams/competition-of raw)
        (throw (ex-info (str "Unknown competition: " raw
                             ". Use Serie A, Serie B, Serie C, Copa do Brasil or Libertadores.")
                        {:type :bad-argument})))))

(defn- field-key
  "Keyword for a sort field given as win_rate, :win-rate or win-rate."
  [field]
  (keyword (str/replace (str/replace (str field) #"^:" "") "_" "-")))

(defn- involves? [team m]
  (or (= team (:home m)) (= team (:away m))))

(defn- venue-ok? [team venue m]
  (case venue
    :home (= team (:home m))
    :away (= team (:away m))
    (involves? team m)))

(defn- final-matches
  "Keeps only finals: Libertadores matches whose stage is 'final', or the highest
  round of a season for the Copa do Brasil (which has no explicit final label)."
  [ms]
  (let [max-round (->> ms
                       (filter #(= :copa-do-brasil (:competition %)))
                       (group-by :season)
                       (map (fn [[season ms]] [season (apply max 0 (keep :round ms))]))
                       (into {}))]
    (filter (fn [m]
              (case (:competition m)
                :libertadores (= "final" (some-> (:stage m) str/lower-case))
                :copa-do-brasil (= (:round m) (get max-round (:season m)))
                false))
            ms)))

(defn filter-matches
  "Matches satisfying the given criteria, most recent first.
  Options: :team :opponent :competition :season :from :to (ISO or dd/MM/yyyy strings),
  :venue (:home, :away or :any, relative to :team) and :final-only."
  [db {:keys [team opponent competition season from to venue final-only]}]
  (let [team (some-> team teams/team-key)
        opponent (some-> opponent teams/team-key)
        competition (->competition competition)
        venue (keyword (or venue "any"))
        from (some-> from data/parse-date)
        to (some-> to data/parse-date)
        ms (cond->> (:matches db)
             competition (filter #(= competition (:competition %)))
             season (filter #(= (long season) (long (:season %))))
             from (filter #(not (.isBefore (:date %) from)))
             to (filter #(not (.isAfter (:date %) to)))
             team (filter #(venue-ok? team venue %))
             opponent (filter #(involves? opponent %)))]
    (cond->> ms
      final-only final-matches
      true (sort-by :date #(compare %2 %1))
      true vec)))

(defn- result-for
  "Result of `team` in match `m`, with venue and goals from the team's point of view."
  [team m]
  (let [home? (= team (:home m))
        gf (if home? (:home-goals m) (:away-goals m))
        ga (if home? (:away-goals m) (:home-goals m))]
    {:venue (if home? :home :away)
     :gf gf
     :ga ga
     :result (cond (> gf ga) :win (< gf ga) :loss :else :draw)}))

(defn- pct [part whole]
  (if (zero? whole)
    0.0
    (/ (Math/round (* 1000.0 (/ part whole))) 10.0)))

(defn- summarize
  "Record over a seq of results (as produced by result-for)."
  [results]
  (let [played (count results)
        wins (count (filter #(= :win (:result %)) results))
        draws (count (filter #(= :draw (:result %)) results))
        losses (count (filter #(= :loss (:result %)) results))
        gf (reduce + 0 (map :gf results))
        ga (reduce + 0 (map :ga results))]
    {:played played
     :wins wins
     :draws draws
     :losses losses
     :goals-for gf
     :goals-against ga
     :goal-difference (- gf ga)
     :points (+ (* 3 wins) draws)
     :win-rate (pct wins played)}))

(defn- team-entries
  "Pairs of [team result] for both sides of every match."
  [ms]
  (mapcat (fn [m] [[(:home m) (result-for (:home m) m)]
                   [(:away m) (result-for (:away m) m)]])
          ms))

(defn team-record
  "Win/draw/loss record and goals for one team, optionally limited by season,
  competition and venue."
  [db {:keys [team season competition venue]}]
  (let [key (teams/team-key team)
        ms (filter-matches db {:team team :season season
                               :competition competition :venue venue})]
    (assoc (summarize (map #(result-for key %) ms))
           :team key
           :matches (count ms))))

(defn team-record-by-competition
  "Record of a team split by competition, for the whole dataset."
  [db {:keys [team]}]
  (let [key (teams/team-key team)
        ms (filter-matches db {:team team})]
    (->> ms
         (group-by :competition)
         (map (fn [[comp ms]]
                (assoc (summarize (map #(result-for key %) ms)) :competition comp)))
         (sort-by (comp - :played)))))

(defn head-to-head
  "Record of `team-a` against `team-b` (from team-a's point of view) plus the matches."
  [db {:keys [team-a team-b competition]}]
  (let [ka (teams/team-key team-a)
        ms (filter-matches db {:team team-a :opponent team-b :competition competition})]
    {:team-a ka
     :team-b (teams/team-key team-b)
     :record (summarize (map #(result-for ka %) ms))
     :matches ms}))

(defn standings
  "League table for one season. Points are 3 for a win and 1 for a draw."
  [db {:keys [competition season]}]
  (let [league (->competition competition)]
    (when-not (teams/league-competitions league)
      (throw (ex-info "Standings are only available for Brasileirão Serie A, B and C."
                      {:type :bad-argument})))
    (when-not season
      (throw (ex-info "A season is required for standings." {:type :bad-argument})))
    (let [ms (filter-matches db {:competition competition :season season})]
      (->> (team-entries ms)
           (group-by first)
           (map (fn [[team es]]
                  (assoc (summarize (map second es)) :team team)))
           (sort-by (juxt (comp - :points) (comp - :wins) (comp - :goal-difference)
                          (comp - :goals-for) :team))
           (map-indexed (fn [i row] (assoc row :position (inc i))))
           vec))))

(def ranking-keys #{:points :wins :win-rate :goals-for :goal-difference})

(defn team-rankings
  "Teams ranked by `:sort-by` (a key of ranking-keys) over a season/competition.
  `venue` restricts results to home or away games; teams with fewer than
  `min-matches` games are left out."
  [db {:keys [competition season venue min-matches limit]
       sort-field :sort-by
       :or {sort-field :points min-matches 1 limit 10}}]
  (let [sort-key (field-key sort-field)
        venue (keyword (or venue "any"))
        ms (filter-matches db {:competition competition :season season})]
    (when-not (ranking-keys sort-key)
      (throw (ex-info (str "sort_by must be one of " (str/join ", " (map name ranking-keys)))
                      {:type :bad-argument})))
    (->> (team-entries ms)
         (filter #(or (= venue :any) (= venue (:venue (second %)))))
         (group-by first)
         (map (fn [[team es]]
                (assoc (summarize (map second es)) :team team)))
         (filter #(>= (:played %) (long min-matches)))
         (sort-by (fn [row] [(- (sort-key row)) (:team row)]))
         (take (long limit))
         vec)))

(defn league-summary
  "Aggregate statistics for one competition and season."
  [db {:keys [competition season top]
       :or {top 5}}]
  (let [ms (filter-matches db {:competition competition :season season})
        n (count ms)
        goals (reduce + 0 (map #(+ (:home-goals %) (:away-goals %)) ms))
        home-wins (count (filter #(> (:home-goals %) (:away-goals %)) ms))
        draws (count (filter #(= (:home-goals %) (:away-goals %)) ms))
        away-wins (count (filter #(< (:home-goals %) (:away-goals %)) ms))
        margin (fn [m] (Math/abs (long (- (:home-goals m) (:away-goals m)))))
        total (fn [m] (+ (:home-goals m) (:away-goals m)))]
    {:matches n
     :goals goals
     :goals-per-match (if (zero? n) 0.0 (/ (Math/round (* 100.0 (/ goals n))) 100.0))
     :home-win-rate (pct home-wins n)
     :draw-rate (pct draws n)
     :away-win-rate (pct away-wins n)
     :biggest-wins (vec (take top (sort-by (juxt (comp - margin) (comp - total)) ms)))
     :highest-scoring (vec (take top (sort-by (comp - total) ms)))}))

(def position-groups
  {"goalkeeper" #{"GK"}
   "defender" #{"CB" "LCB" "RCB" "LB" "RB" "LWB" "RWB"}
   "midfielder" #{"CDM" "LDM" "RDM" "CM" "LCM" "RCM" "CAM" "LAM" "RAM" "LM" "RM"}
   "forward" #{"ST" "CF" "LW" "RW" "LS" "RS" "LF" "RF"}})

(defn search-players
  "FIFA players filtered by name, nationality, club, position group and minimum
  overall, sorted by overall or potential (highest first)."
  [db {:keys [name nationality club position-group min-overall limit]
       sort-field :sort-by
       :or {sort-field :overall limit 10}}]
  (let [sort-key (field-key sort-field)
        club-key (some-> club teams/team-key)
        positions (some->> position-group teams/fold (get position-groups))
        ps (cond->> (:players db)
             name (filter #(str/includes? (teams/fold (:name %)) (teams/fold name)))
             nationality (filter #(= (teams/fold nationality) (teams/fold (:nationality %))))
             club (filter #(or (= club-key (:club-key %))
                               (str/includes? (teams/fold (:club %)) (teams/fold club))))
             positions (filter #(contains? positions (:position %)))
             min-overall (filter #(>= (or (:overall %) 0) (long min-overall))))]
    (when-not (#{:overall :potential} sort-key)
      (throw (ex-info "sort_by must be overall or potential." {:type :bad-argument})))
    (let [sorted (sort-by (comp - #(or (sort-key %) 0)) ps)]
      {:total (count sorted)
       :players (vec (take (long limit) sorted))})))

(defn brazilian-players-by-club
  "Brazilian-national players grouped by Brazilian club, largest squads first."
  [db {:keys [limit] :or {limit 20}}]
  (->> (:players db)
       (filter #(and (= "Brazil" (:nationality %))
                     (:club-key %)
                     (teams/brazilian-club? (:club %))))
       (group-by :club-key)
       (map (fn [[club ps]]
              {:club club
               :players (count ps)
               :average-overall (/ (Math/round (* 10.0 (/ (reduce + 0 (keep :overall ps))
                                                          (max 1 (count (keep :overall ps))))))
                                   10.0)}))
       (sort-by (juxt (comp - :players) :club))
       (take (long limit))
       vec))

(defn team-profile
  "Cross-dataset view of a team: match record per competition plus its FIFA squad."
  [db {:keys [team]}]
  (let [key (teams/team-key team)
        squad (filter #(= key (:club-key %)) (:players db))
        rated (sort-by (comp - #(or (:overall %) 0)) squad)]
    {:team key
     :record (summarize (map #(result-for key %) (filter-matches db {:team team})))
     :by-competition (team-record-by-competition db {:team team})
     :squad-size (count squad)
     :squad-average-overall (when (seq squad)
                              (/ (Math/round (* 10.0 (/ (reduce + 0 (keep :overall squad))
                                                        (count squad))))
                                 10.0))
     :top-players (vec (take 5 rated))}))

(defn record-in
  "Win/draw/loss record of `team` across an already-filtered seq of matches."
  [team ms]
  (let [key (teams/team-key team)]
    (summarize (map #(result-for key %) ms))))
