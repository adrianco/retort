;; =============================================================================
;; brazilian-soccer.queries
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   Part of the Brazilian Soccer MCP server (see TASK.md). This namespace holds
;;   the pure query and aggregation logic that answers the five capability
;;   categories required by the spec:
;;     1. Match queries      — search-matches, head-to-head
;;     2. Team queries       — team-stats (home/away/overall, by season & comp)
;;     3. Player queries     — search-players, top-players, players-by-club
;;     4. Competition queries— standings (computed from results)
;;     5. Statistical analysis — competition-stats, biggest-wins
;;
;;   Functions are deliberately pure: they take an explicit collection of match
;;   or player maps (defaulting to the cached datasets in brazilian-soccer.data)
;;   so they are trivially testable with fixtures. Team-name matching is fuzzy
;;   and accent-insensitive via brazilian-soccer.data/team-matches?.
;;
;;   Consumed by brazilian-soccer.mcp, which wraps each function as an MCP tool.
;; =============================================================================
(ns brazilian-soccer.queries
  (:require [brazilian-soccer.data :as data]
            [clojure.string :as str]))

;; -----------------------------------------------------------------------------
;; Match queries
;; -----------------------------------------------------------------------------

(defn- result-of
  "Returns :home, :away or :draw for the winner of a match map."
  [{:keys [home-goal away-goal]}]
  (cond
    (> home-goal away-goal) :home
    (< home-goal away-goal) :away
    :else :draw))

(defn filter-matches
  "Raw filter (no dedup, sort or limit) of matches by the search criteria.
   See `search-matches` for the option keys. Returns a lazy seq."
  [ms {:keys [team home away opponent competition season from to]}]
  (let [comp-key (when competition
                   (-> competition data/strip-accents str/lower-case str/trim))]
    (filter
     (fn [m]
       (and (or (nil? team)
                (data/team-matches? team (:home m))
                (data/team-matches? team (:away m)))
            (or (nil? home) (data/team-matches? home (:home m)))
            (or (nil? away) (data/team-matches? away (:away m)))
            (or (nil? opponent)
                (data/team-matches? opponent (:home m))
                (data/team-matches? opponent (:away m)))
            (or (nil? competition)
                (str/includes?
                 (-> (:competition m) data/strip-accents str/lower-case)
                 comp-key))
            (or (nil? season) (= season (:season m)))
            (or (nil? from) (and (:date m) (>= (compare (:date m) from) 0)))
            (or (nil? to)   (and (:date m) (<= (compare (:date m) to) 0)))))
     ms)))

(defn dedupe-matches
  "Collapse the same fixture appearing in two overlapping datasets. Only
   matches that carry a :season are reconciled — keyed on
   [competition season base-home base-away home-goal away-goal] using the
   suffix-stripped base team key (so \"Flamengo-RJ\" == \"Flamengo\"). Matches
   without a season (e.g. the season-less BR-Football rows) are passed through
   untouched, so distinct years there are never accidentally merged. Order is
   preserved; the first occurrence of each fixture is kept."
  [ms]
  (loop [seen #{} out (transient []) [m & more] (seq ms)]
    (if (nil? m)
      (persistent! out)
      (if (nil? (:season m))
        (recur seen (conj! out m) more)
        (let [k [(:competition m) (:season m)
                 (data/base-key (:home m)) (data/base-key (:away m))
                 (:home-goal m) (:away-goal m)]]
          (if (contains? seen k)
            (recur seen out more)
            (recur (conj seen k) (conj! out m) more)))))))

(defn search-matches
  "Filter matches by any combination of criteria, de-duplicating fixtures that
   appear across overlapping datasets. Options map keys (all optional):
     :team        — team involved as home OR away
     :home        — team as home only
     :away        — team as away only
     :opponent    — together with :team, narrows to matches between them
     :competition — substring match on competition name (accent-insensitive)
     :season      — integer year
     :from / :to  — ISO date bounds (inclusive)
     :limit       — cap result count (default 100)
   Returns matches sorted by date descending (most recent first)."
  ([opts] (search-matches (data/all-matches) opts))
  ([ms {:keys [limit] :or {limit 100} :as opts}]
   (->> (filter-matches ms opts)
        dedupe-matches
        (sort-by :date #(compare %2 %1))
        (take limit)
        vec)))

(defn head-to-head
  "All matches between team-a and team-b plus an aggregated record.
   Returns {:team-a :team-b :matches :record {:a-wins :b-wins :draws
            :a-goals :b-goals :total}}."
  ([team-a team-b] (head-to-head (data/all-matches) team-a team-b))
  ([ms team-a team-b]
   (let [ms (search-matches ms {:team team-a :opponent team-b :limit Long/MAX_VALUE})
         init {:a-wins 0 :b-wins 0 :draws 0 :a-goals 0 :b-goals 0 :total 0}
         rec  (reduce
               (fn [acc m]
                 (let [a-home? (data/team-matches? team-a (:home m))
                       a-goal  (if a-home? (:home-goal m) (:away-goal m))
                       b-goal  (if a-home? (:away-goal m) (:home-goal m))]
                   (-> acc
                       (update :total inc)
                       (update :a-goals + a-goal)
                       (update :b-goals + b-goal)
                       (update (cond (> a-goal b-goal) :a-wins
                                     (< a-goal b-goal) :b-wins
                                     :else :draws) inc))))
               init ms)]
     {:team-a team-a :team-b team-b :matches ms :record rec})))

;; -----------------------------------------------------------------------------
;; Team queries
;; -----------------------------------------------------------------------------

(defn team-stats
  "Win/draw/loss and goal record for a team. Options:
     :competition :season :from :to — restrict the match set
     :venue — :home, :away or :all (default :all)
   Returns {:team :matches :wins :draws :losses :goals-for :goals-against
            :goal-diff :points :win-rate}."
  ([team opts] (team-stats (data/all-matches) team opts))
  ([ms team {:keys [venue] :or {venue :all} :as opts}]
   (let [candidate (search-matches ms (assoc (dissoc opts :venue)
                                             :team team :limit Long/MAX_VALUE))
         relevant
         (filter (fn [m]
                   (case venue
                     :home (data/team-matches? team (:home m))
                     :away (data/team-matches? team (:away m))
                     true))
                 candidate)
         init {:matches 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0}
         agg (reduce
              (fn [acc m]
                (let [home? (data/team-matches? team (:home m))
                      gf    (if home? (:home-goal m) (:away-goal m))
                      ga    (if home? (:away-goal m) (:home-goal m))]
                  (-> acc
                      (update :matches inc)
                      (update :goals-for + gf)
                      (update :goals-against + ga)
                      (update (cond (> gf ga) :wins
                                    (< gf ga) :losses
                                    :else :draws) inc))))
              init relevant)
         points (+ (* 3 (:wins agg)) (:draws agg))]
     (assoc agg
            :team team
            :venue venue
            :goal-diff (- (:goals-for agg) (:goals-against agg))
            :points points
            :win-rate (if (pos? (:matches agg))
                        (/ (Math/round (* 1000.0 (/ (:wins agg) (:matches agg)))) 10.0)
                        0.0)))))

;; -----------------------------------------------------------------------------
;; Competition queries — standings computed from match results
;; -----------------------------------------------------------------------------

;; Several datasets overlap (e.g. the 2003-2019 historical Brasileirão and the
;; 2012-2023 Brasileirão file both cover 2012-2019). To compute a clean, single
;; league table we pick ONE source per competition+season rather than merging
;; near-duplicate rows that differ subtly between files.
(def ^:private source-priority
  {"Brasileirao_Matches.csv" 0
   "novo_campeonato_brasileiro.csv" 1
   "Libertadores_Matches.csv" 0
   "Brazilian_Cup_Matches.csv" 0
   "BR-Football-Dataset.csv" 2})

(defn- pick-source
  "From a set of matches, choose the single best source: most matches wins,
   ties broken by source-priority (lower = preferred). Returns those matches."
  [ms]
  (if (empty? ms)
    ms
    (let [by-source (group-by :source ms)
          best (->> by-source
                    (sort-by (fn [[src rows]]
                               [(- (count rows)) (get source-priority src 9)]))
                    first
                    key)]
      (get by-source best))))

(defn- representative-name
  "Most frequent display name among matches for a given team-key (prefers the
   accented spelling when counts tie by favouring non-ASCII)."
  [names]
  (->> (frequencies names)
       (sort-by (fn [[nm n]] [(- n) (if (re-find #"[^\x00-\x7f]" nm) 0 1)]))
       ffirst))

(defn standings
  "Compute a league table for a competition + season from match results.
   Uses a single canonical source and groups by normalised team key so that
   accent/suffix variants are merged. Returns rows sorted by points, goal
   difference, goals for, then name:
     {:team :played :wins :draws :losses :goals-for :goals-against
      :goal-diff :points}."
  ([competition season] (standings (data/all-matches) competition season))
  ([ms competition season]
   (let [ms (pick-source
             (filter-matches ms {:competition competition :season season}))
         ;; collect display names per team-key for nice labels
         names (reduce (fn [acc m]
                         (-> acc
                             (update (:home-key m) (fnil conj []) (:home m))
                             (update (:away-key m) (fnil conj []) (:away m))))
                       {} ms)
         blank {:played 0 :wins 0 :draws 0 :losses 0
                :goals-for 0 :goals-against 0}
         bump  (fn [row gf ga]
                 (-> row
                     (update :played inc)
                     (update :goals-for + gf)
                     (update :goals-against + ga)
                     (update (cond (> gf ga) :wins
                                   (< gf ga) :losses
                                   :else :draws) inc)))
         table
         (reduce
          (fn [acc {:keys [home-key away-key home-goal away-goal]}]
            (-> acc
                (update home-key (fnil bump blank) home-goal away-goal)
                (update away-key (fnil bump blank) away-goal home-goal)))
          {} ms)]
     (->> table
          (map (fn [[tk row]]
                 (assoc row
                        :team (representative-name (get names tk))
                        :goal-diff (- (:goals-for row) (:goals-against row))
                        :points (+ (* 3 (:wins row)) (:draws row)))))
          (sort-by (juxt (comp - :points) (comp - :goal-diff)
                         (comp - :goals-for) :team))
          vec))))

;; -----------------------------------------------------------------------------
;; Statistical analysis
;; -----------------------------------------------------------------------------

(defn competition-stats
  "Aggregate stats over a filtered match set (same filter opts as
   search-matches, minus :limit). Returns {:matches :total-goals
   :avg-goals-per-match :home-wins :away-wins :draws :home-win-rate
   :away-win-rate :draw-rate}."
  ([opts] (competition-stats (data/all-matches) opts))
  ([ms opts]
   (let [ms (search-matches ms (assoc opts :limit Long/MAX_VALUE))
         n  (count ms)
         total-goals (reduce (fn [s m] (+ s (:home-goal m) (:away-goal m))) 0 ms)
         {:keys [home away draw]}
         (reduce (fn [acc m] (update acc (result-of m) (fnil inc 0)))
                 {:home 0 :away 0 :draw 0} ms)
         pct (fn [x] (if (pos? n) (/ (Math/round (* 1000.0 (/ x n))) 10.0) 0.0))]
     {:matches n
      :total-goals total-goals
      :avg-goals-per-match (if (pos? n)
                             (/ (Math/round (* 100.0 (/ total-goals n))) 100.0)
                             0.0)
      :home-wins home :away-wins away :draws draw
      :home-win-rate (pct home)
      :away-win-rate (pct away)
      :draw-rate (pct draw)})))

(defn biggest-wins
  "Matches sorted by goal margin (descending). Accepts search-matches opts.
   Returns up to :limit (default 10) matches each annotated with :margin."
  ([opts] (biggest-wins (data/all-matches) opts))
  ([ms {:keys [limit] :or {limit 10} :as opts}]
   (->> (search-matches ms (assoc opts :limit Long/MAX_VALUE))
        (map #(assoc % :margin (abs (- (:home-goal %) (:away-goal %)))))
        (sort-by :margin >)
        (take limit)
        vec)))

;; -----------------------------------------------------------------------------
;; Player queries
;; -----------------------------------------------------------------------------

(defn- contains-ci?
  "Accent-insensitive, case-insensitive substring test."
  [haystack needle]
  (str/includes? (-> (str haystack) data/strip-accents str/lower-case)
                 (-> (str needle) data/strip-accents str/lower-case)))

(defn search-players
  "Filter FIFA players. Options (all optional):
     :name :nationality :club :position — substring (accent/case-insensitive)
     :min-overall — integer floor on the Overall rating
     :limit — cap (default 50)
   Returns players sorted by Overall rating descending."
  ([opts] (search-players (data/all-players) opts))
  ([ps {:keys [name nationality club position min-overall limit]
        :or {limit 50}}]
   (->> ps
        (filter (fn [p]
                  (and (or (nil? name) (contains-ci? (:name p) name))
                       (or (nil? nationality) (contains-ci? (:nationality p) nationality))
                       (or (nil? club) (contains-ci? (:club p) club))
                       (or (nil? position) (contains-ci? (:position p) position))
                       (or (nil? min-overall) (>= (or (:overall p) 0) min-overall)))))
        (sort-by :overall #(compare %2 %1))
        (take limit)
        vec)))

(defn top-players
  "Highest-rated players, optionally filtered by nationality/club/position.
   Convenience wrapper around search-players."
  ([opts] (top-players (data/all-players) opts))
  ([ps opts] (search-players ps (merge {:limit 10} opts))))
