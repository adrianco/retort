;; =============================================================================
;; brsoccer.query
;;
;; Context:
;;   Pure query/analytics layer over the knowledge graph from brsoccer.data.
;;   Every function takes the graph plus parameters and returns plain Clojure
;;   data (never strings) so it is trivially testable; the brsoccer.format and
;;   brsoccer.mcp layers turn these results into text / JSON for the LLM.
;;
;;   Covers the five capability groups in the spec:
;;     1. Match queries        -> find-matches
;;     2. Team queries         -> team-record
;;     3. Player queries       -> search-players
;;     4. Competition queries  -> standings
;;     5. Statistical analysis -> head-to-head, biggest-wins, summary-stats
;;
;;   Team lookups are accent/suffix/case-insensitive via brsoccer.normalize and
;;   fall back to substring matching so partial names ("Sao Paulo") still resolve.
;; =============================================================================
(ns brsoccer.query
  (:require [clojure.string :as str]
            [brsoccer.normalize :as n]))

;; ---------------------------------------------------------------------------
;; Team resolution
;; ---------------------------------------------------------------------------

(defn resolve-team
  "Resolve a free-text team name to a canonical team-key present in the graph.
   Tries exact normalized key, then unique substring match. Returns nil if no
   match or if a substring is ambiguous across differently-named teams."
  [graph name]
  (when-let [k (n/team-key name)]
    (let [teams (:teams graph)]
      (cond
        (contains? teams k) k
        :else
        (let [hits (filter #(or (str/includes? % k) (str/includes? k %))
                           (keys teams))]
          (when (seq hits)
            ;; prefer the shortest key (closest to the query) for stability
            (first (sort-by count hits))))))))

(defn team-display
  "Display name for a team key, falling back to the key itself."
  [graph k]
  (get-in graph [:teams k :name] k))

;; ---------------------------------------------------------------------------
;; 1. Match queries
;; ---------------------------------------------------------------------------

(defn find-matches
  "Filter matches by any combination of:
     :team        team that played (home OR away)
     :opponent    the other team (used with :team)
     :home / :away team constrained to that venue (mutually exclusive w/ :team)
     :competition substring match on competition name
     :season      exact season year (int)
     :from :to    inclusive ISO date bounds
   Returns matches sorted most-recent-first. :limit caps the count."
  [graph {:keys [team opponent home away competition season from to limit]}]
  (let [tk  (some->> team (resolve-team graph))
        ok  (some->> opponent (resolve-team graph))
        hk  (some->> home (resolve-team graph))
        ak  (some->> away (resolve-team graph))
        ck  (some-> competition n/strip-accents str/lower-case)
        base (cond
               tk (get-in graph [:by-team tk])
               (or hk ak) (get-in graph [:by-team (or hk ak)])
               :else (:matches graph))]
    (cond->> base
      tk          (filter #(or (= tk (:home-key %)) (= tk (:away-key %))))
      ok          (filter #(or (= ok (:home-key %)) (= ok (:away-key %))))
      hk          (filter #(= hk (:home-key %)))
      ak          (filter #(= ak (:away-key %)))
      ck          (filter #(str/includes? (-> % :competition n/strip-accents str/lower-case) ck))
      season      (filter #(= season (:season %)))
      from        (filter #(and (:date %) (<= 0 (compare (:date %) from))))
      to          (filter #(and (:date %) (>= 0 (compare to (:date %)))))
      true        (sort-by (juxt :date :season) #(compare %2 %1))
      limit       (take limit))))

;; ---------------------------------------------------------------------------
;; 2 + 5. Team records, head-to-head
;; ---------------------------------------------------------------------------

(defn- accumulate-record
  "Tally W/D/L and goals for `team-key` across the given matches.
   When `venue` is :home or :away only those fixtures are counted."
  [team-key venue matches]
  (reduce
    (fn [acc m]
      (let [home? (= team-key (:home-key m))
            plays? (or home? (= team-key (:away-key m)))
            include? (and plays? (case venue :home home? :away (not home?) true))]
        (if-not include?
          acc
          (let [gf (if home? (:home-goal m) (:away-goal m))
                ga (if home? (:away-goal m) (:home-goal m))
                outcome (cond (> gf ga) :wins (< gf ga) :losses :else :draws)]
            (-> acc
                (update :matches inc)
                (update outcome inc)
                (update :goals-for + gf)
                (update :goals-against + ga))))))
    {:matches 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0}
    matches))

(defn team-record
  "Aggregate record for a team, optionally filtered by season/competition/venue.
   :venue may be :home, :away or nil (all)."
  [graph {:keys [team season competition venue]}]
  (when-let [tk (resolve-team graph team)]
    (let [ms (find-matches graph {:team team :season season :competition competition})
          rec (accumulate-record tk venue ms)
          {:keys [matches wins]} rec]
      (assoc rec
             :team (team-display graph tk)
             :team-key tk
             :season season
             :competition competition
             :venue venue
             :points (+ (* 3 wins) (:draws rec))
             :goal-diff (- (:goals-for rec) (:goals-against rec))
             :win-rate (if (pos? matches) (/ (Math/round (* 1000.0 (/ wins matches))) 10.0) 0.0)))))

(defn head-to-head
  "Head-to-head summary between two teams across all competitions (or filtered)."
  [graph {:keys [team-a team-b season competition]}]
  (let [ka (resolve-team graph team-a)
        kb (resolve-team graph team-b)]
    (when (and ka kb)
      (let [ms (find-matches graph {:team team-a :opponent team-b
                                    :season season :competition competition})
            tally (reduce
                    (fn [acc m]
                      (let [a-home? (= ka (:home-key m))
                            ga (if a-home? (:home-goal m) (:away-goal m))
                            gb (if a-home? (:away-goal m) (:home-goal m))]
                        (-> acc
                            (update :a-goals + ga)
                            (update :b-goals + gb)
                            (update (cond (> ga gb) :a-wins (< ga gb) :b-wins :else :draws) inc))))
                    {:a-wins 0 :b-wins 0 :draws 0 :a-goals 0 :b-goals 0}
                    ms)]
        (assoc tally
               :team-a (team-display graph ka)
               :team-b (team-display graph kb)
               :total (count ms)
               :matches ms)))))

;; ---------------------------------------------------------------------------
;; 3. Player queries
;; ---------------------------------------------------------------------------

(defn search-players
  "Search FIFA players by :name (substring), :nationality (exact, accent-insens.),
   :club (resolved team key), :position (substring) and :min-overall.
   Sorted by :overall desc; :limit caps the result."
  [graph {:keys [name nationality club position min-overall limit]}]
  (let [nm  (some-> name n/strip-accents str/lower-case)
        nat (some-> nationality n/strip-accents str/lower-case)
        ck  (some->> club (resolve-team graph))
        pos (some-> position str/lower-case)]
    (cond->> (:players graph)
      nm          (filter #(and (:name-key %) (str/includes? (:name-key %) nm)))
      nat         (filter #(= nat (:nat-key %)))
      ck          (filter #(= ck (:club-key %)))
      pos         (filter #(and (:position %) (str/includes? (str/lower-case (:position %)) pos)))
      min-overall (filter #(and (:overall %) (>= (:overall %) min-overall)))
      true        (sort-by :overall #(compare %2 %1))
      limit       (take limit))))

(defn players-by-brazilian-club
  "Group Brazilian players by Brazilian club, returning per-club player count and
   average overall. Used for the 'Brazilian players at Brazilian clubs' view."
  [graph]
  (let [team-keys (set (keys (:teams graph)))]
    (->> (search-players graph {:nationality "Brazil"})
         (filter #(contains? team-keys (:club-key %)))
         (group-by :club-key)
         (map (fn [[k players]]
                {:club (team-display graph k)
                 :count (count players)
                 :avg-overall (let [os (keep :overall players)]
                                (when (seq os)
                                  (/ (Math/round (* 10.0 (/ (reduce + os) (count os)))) 10.0)))}))
         (sort-by :count >))))

;; ---------------------------------------------------------------------------
;; 4. Competition standings
;; ---------------------------------------------------------------------------

(defn standings
  "Compute a league table for a competition+season from match results.
   Returns rows sorted by points, then goal-difference, then goals-for."
  [graph {:keys [competition season]}]
  (let [ms (find-matches graph {:competition competition :season season})
        team-keys (distinct (mapcat (juxt :home-key :away-key) ms))]
    (->> team-keys
         (map (fn [tk]
                (let [rec (accumulate-record tk nil ms)]
                  (assoc rec
                         :team (team-display graph tk)
                         :team-key tk
                         :points (+ (* 3 (:wins rec)) (:draws rec))
                         :goal-diff (- (:goals-for rec) (:goals-against rec))))))
         (sort-by (juxt :points :goal-diff :goals-for) #(compare %2 %1))
         (map-indexed (fn [i row] (assoc row :position (inc i)))))))

;; ---------------------------------------------------------------------------
;; 5. Statistical analysis
;; ---------------------------------------------------------------------------

(defn biggest-wins
  "Matches with the largest goal margin, filtered like find-matches.
   Sorted by margin desc."
  [graph {:keys [competition season limit] :or {limit 10}}]
  (->> (find-matches graph {:competition competition :season season})
       (map #(assoc % :margin (Math/abs (- (:home-goal %) (:away-goal %)))))
       (sort-by (juxt :margin #(+ (:home-goal %) (:away-goal %))) #(compare %2 %1))
       (take limit)))

(defn summary-stats
  "Aggregate statistics over a filtered match set: counts, average goals/match,
   and home/away/draw win rates."
  [graph {:keys [competition season]}]
  (let [ms (find-matches graph {:competition competition :season season})
        n  (count ms)
        goals (reduce + 0 (map #(+ (:home-goal %) (:away-goal %)) ms))
        freq (frequencies (map :result ms))
        pct (fn [k] (if (pos? n) (/ (Math/round (* 1000.0 (/ (get freq k 0) n))) 10.0) 0.0))]
    {:competition competition
     :season season
     :matches n
     :total-goals goals
     :avg-goals (if (pos? n) (/ (Math/round (* 100.0 (/ goals n))) 100.0) 0.0)
     :home-wins (get freq :home 0)
     :away-wins (get freq :away 0)
     :draws (get freq :draw 0)
     :home-win-rate (pct :home)
     :away-win-rate (pct :away)
     :draw-rate (pct :draw)}))

(defn best-record
  "Teams ranked by win-rate for a venue (:home/:away/nil) within a filtered set.
   :min-matches guards against tiny samples."
  [graph {:keys [competition season venue min-matches limit] :or {min-matches 5 limit 10}}]
  (let [ms (find-matches graph {:competition competition :season season})
        team-keys (distinct (mapcat (juxt :home-key :away-key) ms))]
    (->> team-keys
         (map (fn [tk]
                (let [rec (accumulate-record tk venue ms)]
                  (assoc rec
                         :team (team-display graph tk)
                         :win-rate (if (pos? (:matches rec))
                                     (/ (Math/round (* 1000.0 (/ (:wins rec) (:matches rec)))) 10.0)
                                     0.0)))))
         (filter #(>= (:matches %) min-matches))
         (sort-by (juxt :win-rate :wins) #(compare %2 %1))
         (take limit))))

(defn list-competitions
  "Distinct competitions with their season coverage and match counts."
  [graph]
  (->> (:matches graph)
       (group-by :competition)
       (map (fn [[c ms]]
              (let [seasons (sort (distinct (keep :season ms)))]
                {:competition c
                 :matches (count ms)
                 :seasons-from (first seasons)
                 :seasons-to (last seasons)})))
       (sort-by :competition)))
