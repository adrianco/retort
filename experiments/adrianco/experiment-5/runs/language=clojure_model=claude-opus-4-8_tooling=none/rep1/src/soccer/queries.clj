(ns soccer.queries
  "=============================================================================
   soccer.queries — Pure query / aggregation functions over the unified data
   -----------------------------------------------------------------------------
   PURPOSE
     Implements every capability category required by the spec, as pure
     functions that take the loaded dataset (`{:matches ... :players ...}`)
     plus an option map and return plain Clojure data. The MCP layer
     (soccer.mcp) and the formatter (soccer.format) build on top of these.

   CAPABILITIES
     Match queries .... search-matches, head-to-head
     Team queries ..... team-stats (overall / by venue / by competition)
     Player queries ... search-players
     Competition ...... standings, season-summary
     Statistics ....... league-stats, biggest-wins

   All functions are side-effect free; the caller supplies the dataset, which
   keeps them trivially testable with fixture data.
   ============================================================================="
  (:require [clojure.string :as str]
            [soccer.normalize :as n]))

;; ---------------------------------------------------------------------------
;; Match filtering
;; ---------------------------------------------------------------------------

(defn- comp-matches? [q comp]
  (or (str/blank? (str q))
      (let [qk (str/lower-case (n/strip-accents (str q)))
            ck (str/lower-case (n/strip-accents (str comp)))]
        (str/includes? ck qk))))

(defn- in-range? [date from to]
  (and (or (str/blank? (str from)) (>= (compare date (n/norm-date from)) 0))
       (or (str/blank? (str to))   (<= (compare date (n/norm-date to)) 0))))

(defn search-matches
  "Return matches filtered by any combination of:
     :team       team name (home OR away)
     :team2      second team — together with :team restricts to head-to-head
     :home / :away  restrict :team to a specific venue role
     :competition  substring match against the competition label
     :season       integer season/year
     :date-from / :date-to   ISO (or BR) date bounds, inclusive
   Results are sorted most-recent first. :limit caps the count (default 50)."
  [{:keys [matches]} {:keys [team team2 competition season date-from date-to
                             home away limit]
                      :or {limit 50}}]
  (cond->> matches
    season       (filter #(= season (:season %)))
    competition  (filter #(comp-matches? competition (:competition %)))
    (or date-from date-to) (filter #(and (:date %) (in-range? (:date %) date-from date-to)))
    (and team home)        (filter #(n/team-matches? team (:home %)))
    (and team away)        (filter #(n/team-matches? team (:away %)))
    (and team (not home) (not away))
    (filter #(or (n/team-matches? team (:home %))
                 (n/team-matches? team (:away %))))
    team2        (filter #(or (and (n/team-matches? team (:home %))
                                   (n/team-matches? team2 (:away %)))
                              (and (n/team-matches? team2 (:home %))
                                   (n/team-matches? team (:away %)))))
    true         (sort-by :date #(compare %2 %1))
    limit        (take limit)
    true         vec))

;; ---------------------------------------------------------------------------
;; Result helpers
;; ---------------------------------------------------------------------------

(defn- outcome
  "Classify a goals-for / goals-against pair as :win/:draw/:loss."
  [gf ga]
  {:gf gf :ga ga :result (cond (> gf ga) :win (< gf ga) :loss :else :draw)})

(defn- team-result
  "From the perspective of team query `team`, return {:venue :result :gf :ga}
   for match `m`, or nil if `team` did not play in it. Uses loose name matching
   so a bare query (\"Flamengo\") matches a suffixed name (\"Flamengo-RJ\")."
  [team m]
  (cond
    (n/team-matches? team (:home m)) (assoc (outcome (:home-goal m) (:away-goal m)) :venue :home)
    (n/team-matches? team (:away m)) (assoc (outcome (:away-goal m) (:home-goal m)) :venue :away)
    :else nil))

(defn- tally [results]
  (reduce (fn [acc {:keys [result gf ga]}]
            (-> acc
                (update :played inc)
                (update (case result :win :wins :loss :losses :draw :draws) inc)
                (update :gf + gf)
                (update :ga + ga)
                (update :points + (case result :win 3 :draw 1 :loss 0))))
          {:played 0 :wins 0 :draws 0 :losses 0 :gf 0 :ga 0 :points 0}
          results))

(defn- with-derived [t]
  (let [{:keys [played wins gf ga]} t]
    (assoc t
           :gd (- gf ga)
           :win-rate (if (pos? played) (double (/ wins played)) 0.0))))

;; ---------------------------------------------------------------------------
;; Team queries
;; ---------------------------------------------------------------------------

(defn team-stats
  "Aggregate W/D/L, goals for/against, points and win-rate for `team`,
   optionally restricted by :season, :competition and :venue (:home/:away).
   Returns a map including the resolved display :team name and the matches."
  [db {:keys [team season competition venue] :as opts}]
  (let [ms (search-matches db (assoc opts :limit nil))
        results (->> ms
                     (keep (fn [m] (when-let [r (team-result team m)]
                                     (when (or (nil? venue) (= venue (:venue r)))
                                       r)))))
        display (or (some #(cond (n/team-matches? team (:home %)) (:home %)
                                 (n/team-matches? team (:away %)) (:away %)) ms)
                    team)]
    (merge {:team display :season season :competition competition :venue venue}
           (with-derived (tally results)))))

(defn head-to-head
  "Head-to-head summary between two teams: each side's wins, draws, and the
   chronological list of meetings, from team1's perspective."
  [db {:keys [team1 team2] :as opts}]
  (let [ms (search-matches db (assoc opts :team team1 :team2 team2 :limit nil))
        agg (reduce (fn [acc m]
                      (case (:result (team-result team1 m))
                        :win  (update acc :team1-wins inc)
                        :loss (update acc :team2-wins inc)
                        :draw (update acc :draws inc)
                        acc))
                    {:team1-wins 0 :team2-wins 0 :draws 0}
                    ms)]
    (merge {:team1 (or (some #(when (n/team-matches? team1 (:home %)) (:home %)) ms)
                       (some #(when (n/team-matches? team1 (:away %)) (:away %)) ms)
                       team1)
            :team2 (or (some #(when (n/team-matches? team2 (:home %)) (:home %)) ms)
                       (some #(when (n/team-matches? team2 (:away %)) (:away %)) ms)
                       team2)
            :meetings (count ms)
            :matches (vec ms)}
           agg)))

;; ---------------------------------------------------------------------------
;; Competition queries
;; ---------------------------------------------------------------------------

(defn standings
  "Compute a league table for a competition+season from match results.
   Returns a sorted vector of rows {:team :played :wins :draws :losses
   :gf :ga :gd :points}, ranked by points, then goal difference, then GF."
  [db {:keys [competition season]}]
  (let [ms (search-matches db {:competition competition :season season :limit nil})
        ;; accumulate per normalized team key, remembering a display name
        acc (reduce
             (fn [acc m]
               (-> acc
                   (update-in [(:home-key m) :results] (fnil conj [])
                              (outcome (:home-goal m) (:away-goal m)))
                   (assoc-in  [(:home-key m) :name] (:home m))
                   (update-in [(:away-key m) :results] (fnil conj [])
                              (outcome (:away-goal m) (:home-goal m)))
                   (assoc-in  [(:away-key m) :name] (:away m))))
             {}
             ms)]
    (->> acc
         (map (fn [[_ {:keys [name results]}]]
                (assoc (with-derived (tally results)) :team name)))
         (sort-by (juxt (comp - :points) (comp - :gd) (comp - :gf)))
         vec)))

(defn season-summary
  "Compare two or more seasons of a competition: matches, goals, averages."
  [db {:keys [competition seasons]}]
  (for [s seasons]
    (let [ms (search-matches db {:competition competition :season s :limit nil})
          goals (reduce + 0 (map #(+ (:home-goal %) (:away-goal %)) ms))
          n (count ms)]
      {:season s
       :matches n
       :goals goals
       :avg-goals (if (pos? n) (double (/ goals n)) 0.0)
       :home-wins (count (filter #(> (:home-goal %) (:away-goal %)) ms))})))

;; ---------------------------------------------------------------------------
;; Statistical analysis
;; ---------------------------------------------------------------------------

(defn league-stats
  "Aggregate statistics for a competition (optionally a season):
   match count, total/average goals, home-win-rate, draw-rate, away-win-rate."
  [db {:keys [competition season]}]
  (let [ms (search-matches db {:competition competition :season season :limit nil})
        n (count ms)
        goals (reduce + 0 (map #(+ (:home-goal %) (:away-goal %)) ms))
        hw (count (filter #(> (:home-goal %) (:away-goal %)) ms))
        aw (count (filter #(< (:home-goal %) (:away-goal %)) ms))
        dr (- n hw aw)]
    {:competition (or competition "all competitions")
     :season season
     :matches n
     :goals goals
     :avg-goals (if (pos? n) (double (/ goals n)) 0.0)
     :home-win-rate (if (pos? n) (double (/ hw n)) 0.0)
     :away-win-rate (if (pos? n) (double (/ aw n)) 0.0)
     :draw-rate (if (pos? n) (double (/ dr n)) 0.0)}))

(defn biggest-wins
  "Matches with the largest goal margin, optionally filtered by competition
   and season. Sorted by margin descending. :limit defaults to 10."
  [db {:keys [competition season limit] :or {limit 10}}]
  (->> (search-matches db {:competition competition :season season :limit nil})
       (map #(assoc % :margin (abs (- (:home-goal %) (:away-goal %)))))
       (sort-by :margin >)
       (take limit)
       vec))

;; ---------------------------------------------------------------------------
;; Player queries
;; ---------------------------------------------------------------------------

(defn- contains-ci? [haystack needle]
  (and (seq (str needle))
       (str/includes? (str/lower-case (n/strip-accents (str haystack)))
                      (str/lower-case (n/strip-accents (str needle))))))

(defn search-players
  "Search the FIFA player dataset by any combination of:
     :name        substring (accent-insensitive)
     :nationality substring (e.g. \"Brazil\")
     :club        substring (e.g. \"Flamengo\")
     :position    exact-ish position tag (e.g. \"GK\", \"ST\")
     :min-overall minimum FIFA overall rating
   Results are sorted by overall rating descending. :limit defaults to 25."
  [{:keys [players]} {:keys [name nationality club position min-overall limit]
                      :or {limit 25}}]
  (cond->> players
    name         (filter #(contains-ci? (:name %) name))
    nationality  (filter #(contains-ci? (:nationality %) nationality))
    club         (filter #(contains-ci? (:club %) club))
    position     (filter #(= (str/upper-case position) (str/upper-case (:position %))))
    min-overall  (filter #(>= (or (:overall %) 0) min-overall))
    true         (sort-by #(or (:overall %) 0) >)
    limit        (take limit)
    true         vec))
