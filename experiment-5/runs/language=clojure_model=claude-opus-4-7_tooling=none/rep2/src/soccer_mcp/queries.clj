(ns soccer-mcp.queries
  "Query layer over the in-memory match and player collections.

   All functions are pure — they take the loaded dataset (`{:matches :players}`)
   plus query parameters and return plain Clojure data. Display/formatting and
   transport concerns live in `soccer-mcp.server`.

   The query API is intentionally broad enough to answer every category of
   question listed in TASK.md:
     - Match search (find-matches)
     - Team statistics (team-stats)
     - Head-to-head (head-to-head)
     - Standings (standings)
     - Biggest victories (biggest-wins)
     - League-wide averages (average-goals, home-win-rate)
     - Player search (find-players)
     - Player aggregates by club (players-by-club, top-rated-brazilians)"
  (:require [clojure.string :as str]
            [soccer-mcp.data :as data]))

;; ----------------------------------------------------------------------------
;; Competition filter

(def competition-aliases
  ;; Per-competition aliases each map to ONE source by default to avoid
  ;; double-counting matches that appear in multiple bundled CSVs. The
  ;; "-all" variants explicitly union overlapping sources for users who
  ;; want the broadest possible view.
  {"brasileirao"             #{:brasileirao}
   "brasileirao-serie-a"     #{:brasileirao}
   "brasileirao-historical"  #{:brasileirao-historical}
   "brasileirao-extended"    #{:brasileirao-extended}
   "brasileirao-all"         #{:brasileirao :brasileirao-historical
                               :brasileirao-extended}
   "copa-do-brasil"          #{:copa-do-brasil}
   "copa-do-brasil-extended" #{:copa-do-brasil-extended}
   "copa-do-brasil-all"      #{:copa-do-brasil :copa-do-brasil-extended}
   "libertadores"            #{:libertadores}
   "libertadores-extended"   #{:libertadores-extended}
   "libertadores-all"        #{:libertadores :libertadores-extended}
   "serie-b"                 #{:serie-b-extended}
   "serie-c"                 #{:serie-c-extended}
   "extended"                #{:brasileirao-extended :copa-do-brasil-extended
                               :libertadores-extended :serie-b-extended
                               :serie-c-extended :other}})

(defn- competition-filter
  "Predicate that keeps matches whose :competition is in `comp-key` (a string
   alias from competition-aliases, a keyword, a set, or nil for no filter)."
  [comp-key]
  (cond
    (nil? comp-key)     (constantly true)
    (set? comp-key)     #(contains? comp-key (:competition %))
    (keyword? comp-key) #(= comp-key (:competition %))
    :else
    (if-let [s (get competition-aliases (data/ascii-fold (str comp-key)))]
      #(contains? s (:competition %))
      (constantly true))))

(defn- season-filter [season]
  (if (nil? season)
    (constantly true)
    (let [s (data/parse-long-safe season)]
      #(= s (:season %)))))

(defn- date-filter [from to]
  (let [from* (data/normalize-date from)
        to*   (data/normalize-date to)]
    (fn [m]
      (let [d (:date m)]
        (and (or (nil? from*) (and d (>= (compare d from*) 0)))
             (or (nil? to*)   (and d (<= (compare d to*) 0))))))))

;; ----------------------------------------------------------------------------
;; Match search

(defn- team-side-filter
  "Build a predicate matching a team name on one or both sides."
  [team {:keys [side]}]
  (if (str/blank? team)
    (constantly true)
    (case (some-> side str/lower-case keyword)
      :home  #(data/team-matches? (:home %) team)
      :away  #(data/team-matches? (:away %) team)
      ;; default: either side
      #(or (data/team-matches? (:home %) team)
           (data/team-matches? (:away %) team)))))

(defn find-matches
  "Filter `:matches` by team(s), competition, season, and/or date range.

   Options:
     :team        — match either side (after team-name normalization)
     :team-a/:team-b — both teams must play (in either home/away combo)
     :side        — :home | :away | nil (only honored with :team)
     :competition — string alias or keyword (see competition-aliases)
     :season      — int year
     :from / :to  — inclusive YYYY-MM-DD (or any normalize-able date)
     :limit       — cap result size

   Results are sorted by date ascending (nil dates last)."
  [dataset {:keys [team team-a team-b side competition season from to limit]
            :or   {limit 0}}]
  (let [pred (every-pred
              (competition-filter competition)
              (season-filter season)
              (date-filter from to)
              (team-side-filter team {:side side})
              (if (and team-a team-b)
                #(or (and (data/team-matches? (:home %) team-a)
                          (data/team-matches? (:away %) team-b))
                     (and (data/team-matches? (:home %) team-b)
                          (data/team-matches? (:away %) team-a)))
                (constantly true)))
        results (->> (:matches dataset)
                     (filter pred)
                     (sort-by (fn [m] (or (:date m) "9999"))))]
    (if (pos? limit)
      (take limit results)
      results)))

;; ----------------------------------------------------------------------------
;; Team statistics

(defn- outcome
  "Return :win/:loss/:draw for the team on the `side` (:home or :away) of `m`."
  [m side]
  (let [h (:home-goal m) a (:away-goal m)]
    (cond
      (= h a) :draw
      (and (= side :home) (> h a)) :win
      (and (= side :home) (< h a)) :loss
      (and (= side :away) (> a h)) :win
      :else :loss)))

(defn- record-for-team
  "Aggregate W/D/L and GF/GA for a single side on a single match."
  [m team]
  (cond
    (data/team-matches? (:home m) team)
    {:played 1
     :wins (if (= :win (outcome m :home)) 1 0)
     :losses (if (= :loss (outcome m :home)) 1 0)
     :draws (if (= :draw (outcome m :home)) 1 0)
     :goals-for (:home-goal m)
     :goals-against (:away-goal m)
     :home 1 :away 0}
    (data/team-matches? (:away m) team)
    {:played 1
     :wins (if (= :win (outcome m :away)) 1 0)
     :losses (if (= :loss (outcome m :away)) 1 0)
     :draws (if (= :draw (outcome m :away)) 1 0)
     :goals-for (:away-goal m)
     :goals-against (:home-goal m)
     :home 0 :away 1}
    :else nil))

(defn- sum-records [rs]
  (reduce (fn [acc r]
            (-> acc
                (update :played + (:played r))
                (update :wins + (:wins r))
                (update :losses + (:losses r))
                (update :draws + (:draws r))
                (update :goals-for + (:goals-for r))
                (update :goals-against + (:goals-against r))
                (update :home + (:home r))
                (update :away + (:away r))))
          {:played 0 :wins 0 :losses 0 :draws 0
           :goals-for 0 :goals-against 0 :home 0 :away 0}
          rs))

(defn- with-derived-stats [stats]
  (let [{:keys [played wins draws goals-for goals-against]} stats]
    (assoc stats
           :points  (+ (* 3 wins) draws)
           :win-rate (if (pos? played)
                       (/ (double wins) played)
                       0.0)
           :goal-diff (- goals-for goals-against))))

(defn team-stats
  "Aggregate season/competition stats for `team`.

   Accepts the same competition / season / side / date filters as find-matches.
   Returns: {:team display-name :played :wins :draws :losses
             :goals-for :goals-against :goal-diff :points :win-rate}"
  [dataset {:keys [team side] :as opts}]
  (let [matches (find-matches dataset (dissoc opts :side))
        recs    (->> matches
                     (keep #(record-for-team % team))
                     (filter (case (some-> side str/lower-case keyword)
                               :home #(= 1 (:home %))
                               :away #(= 1 (:away %))
                               (constantly true))))
        agg     (sum-records recs)
        display (some #(when (data/team-matches? (:home %) team) (:home %))
                      matches)
        display (or display
                    (some #(when (data/team-matches? (:away %) team) (:away %))
                          matches)
                    team)]
    (-> agg
        with-derived-stats
        (assoc :team display
               :query team
               :competition (:competition opts)
               :season (:season opts)
               :side (:side opts)))))

;; ----------------------------------------------------------------------------
;; Head-to-head

(defn head-to-head
  "Aggregate head-to-head record between two teams across all matches matching
   the supplied filters."
  [dataset {:keys [team-a team-b] :as opts}]
  (let [ms (find-matches dataset opts)
        ;; For each match decide: A-win / B-win / draw
        agg (reduce
             (fn [acc m]
               (let [h (:home m) a (:away m) hg (:home-goal m) ag (:away-goal m)]
                 (cond
                   (and (data/team-matches? h team-a)
                        (data/team-matches? a team-b))
                   (cond
                     (> hg ag) (-> acc (update :a-wins inc)
                                       (update :a-goals + hg)
                                       (update :b-goals + ag))
                     (< hg ag) (-> acc (update :b-wins inc)
                                       (update :a-goals + hg)
                                       (update :b-goals + ag))
                     :else     (-> acc (update :draws inc)
                                       (update :a-goals + hg)
                                       (update :b-goals + ag)))
                   (and (data/team-matches? h team-b)
                        (data/team-matches? a team-a))
                   (cond
                     (> hg ag) (-> acc (update :b-wins inc)
                                       (update :a-goals + ag)
                                       (update :b-goals + hg))
                     (< hg ag) (-> acc (update :a-wins inc)
                                       (update :a-goals + ag)
                                       (update :b-goals + hg))
                     :else     (-> acc (update :draws inc)
                                       (update :a-goals + ag)
                                       (update :b-goals + hg)))
                   :else acc)))
             {:a-wins 0 :b-wins 0 :draws 0 :a-goals 0 :b-goals 0}
             ms)]
    (assoc agg
           :team-a team-a
           :team-b team-b
           :matches (count ms))))

;; ----------------------------------------------------------------------------
;; Standings

(defn standings
  "Calculate a league table from all matches matching the filters.

   Returns a vector of team rows sorted by points desc, goal-diff desc,
   goals-for desc."
  [dataset opts]
  (let [matches (find-matches dataset opts)
        per-team (reduce
                  (fn [acc m]
                    (let [home (:home m) away (:away m)
                          out-home (outcome m :home)
                          out-away (outcome m :away)
                          add (fn [acc team gf ga out hm-flag]
                                (-> acc
                                    (update-in [team :played] (fnil inc 0))
                                    (update-in [team :wins]
                                               (fnil + 0)
                                               (if (= out :win) 1 0))
                                    (update-in [team :draws]
                                               (fnil + 0)
                                               (if (= out :draw) 1 0))
                                    (update-in [team :losses]
                                               (fnil + 0)
                                               (if (= out :loss) 1 0))
                                    (update-in [team :goals-for] (fnil + 0) gf)
                                    (update-in [team :goals-against]
                                               (fnil + 0) ga)
                                    (update-in [team :home] (fnil + 0) hm-flag)
                                    (update-in [team :away] (fnil + 0)
                                               (- 1 hm-flag))))]
                      (-> acc
                          (add home (:home-goal m) (:away-goal m) out-home 1)
                          (add away (:away-goal m) (:home-goal m) out-away 0))))
                  {}
                  matches)]
    (->> per-team
         (map (fn [[team r]]
                (-> r
                    (update :played #(or % 0))
                    (update :wins #(or % 0))
                    (update :draws #(or % 0))
                    (update :losses #(or % 0))
                    (update :goals-for #(or % 0))
                    (update :goals-against #(or % 0))
                    (update :home #(or % 0))
                    (update :away #(or % 0))
                    with-derived-stats
                    (assoc :team team))))
         (sort-by (fn [r] [(- (:points r))
                           (- (:goal-diff r))
                           (- (:goals-for r))]))
         vec)))

;; ----------------------------------------------------------------------------
;; League-wide stats

(defn biggest-wins
  "Return the `n` matches with the largest absolute goal difference, matching
   the supplied filters. Default n = 10."
  [dataset {:keys [n] :or {n 10} :as opts}]
  (->> (find-matches dataset (dissoc opts :n))
       (sort-by (fn [m] (- (Math/abs (long (- (:home-goal m) (:away-goal m)))))))
       (take n)
       vec))

(defn average-goals
  "Return {:matches N :goals G :avg G/N} for all matches matching filters."
  [dataset opts]
  (let [ms (find-matches dataset opts)
        g  (reduce (fn [acc m]
                     (+ acc (:home-goal m) (:away-goal m)))
                   0 ms)
        n  (count ms)]
    {:matches n
     :goals g
     :avg   (if (pos? n) (/ (double g) n) 0.0)}))

(defn home-win-rate
  "Return {:matches N :home-wins H :rate H/N} for the filtered match set."
  [dataset opts]
  (let [ms (find-matches dataset opts)
        h  (count (filter #(> (:home-goal %) (:away-goal %)) ms))
        n  (count ms)]
    {:matches n
     :home-wins h
     :rate (if (pos? n) (/ (double h) n) 0.0)}))

;; ----------------------------------------------------------------------------
;; Player queries

(defn- str-match? [s q]
  (and s q (str/includes? (data/ascii-fold s) (data/ascii-fold q))))

(defn find-players
  "Search the FIFA player table.

   Options:
     :name        — substring match (accent-insensitive)
     :nationality — substring match
     :club        — substring match
     :position    — exact (case-insensitive) match
     :min-overall — only players with Overall >= this
     :limit       — cap (default 50; pass 0 for unlimited)
     :sort        — :overall (default) or :name"
  [dataset {:keys [name nationality club position min-overall limit sort]
            :or   {limit 50 sort :overall}}]
  (let [pred (every-pred
              (if name        #(str-match? (:name %) name) (constantly true))
              (if nationality #(str-match? (:nationality %) nationality)
                              (constantly true))
              (if club        #(str-match? (:club %) club) (constantly true))
              (if position
                #(= (data/ascii-fold (:position %))
                    (data/ascii-fold position))
                (constantly true))
              (if min-overall
                #(and (:overall %)
                      (>= (:overall %) (long min-overall)))
                (constantly true)))
        sorter (case sort
                 :name    #(or (:name %) "")
                 :overall #(- (or (:overall %) 0)))
        all (->> (:players dataset)
                 (filter pred)
                 (sort-by sorter))]
    (if (pos? limit)
      (vec (take limit all))
      (vec all))))

(defn top-rated-brazilians
  "Convenience: top-rated Brazilian players, optional `limit`."
  ([dataset] (top-rated-brazilians dataset 10))
  ([dataset limit]
   (find-players dataset
                 {:nationality "Brazil" :limit limit :sort :overall})))

(defn players-by-club
  "Group player counts and average overall by club, restricted to players
   whose nationality matches `:nationality` (default Brazil) and optional
   `:club-filter` (substring on club name). Sorted by count descending."
  [dataset {:keys [nationality club-filter limit]
            :or   {nationality "Brazil" limit 10}}]
  (let [ps (find-players dataset
                         (cond-> {:nationality nationality :limit 0}
                           club-filter (assoc :club club-filter)))]
    (->> ps
         (group-by :club)
         (map (fn [[club ps]]
                (let [overalls (keep :overall ps)
                      n        (count ps)]
                  {:club club
                   :players n
                   :avg-overall (if (seq overalls)
                                  (double (/ (reduce + overalls) (count overalls)))
                                  0.0)})))
         (sort-by (juxt #(- (:players %)) #(- (:avg-overall %))))
         (take limit)
         vec)))
