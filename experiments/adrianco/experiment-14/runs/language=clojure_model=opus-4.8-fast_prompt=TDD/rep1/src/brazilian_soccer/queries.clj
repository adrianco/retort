(ns brazilian-soccer.queries
  "Query engine over the loaded knowledge graph.

  Every function here takes the in-memory db produced by
  `brazilian-soccer.data/load-db` (or, for the statistics helpers, a plain
  sequence of match maps) and returns plain Clojure data. The MCP layer turns
  these results into natural-language answers.

  Team matching always goes through `normalize/team-key`, so callers may pass
  names with or without state suffixes and with or without accents."
  (:require [brazilian-soccer.normalize :as norm]
            [clojure.string :as str]))

(defn- round1 [x]
  (/ (Math/round (* (double x) 10.0)) 10.0))

(defn- plays-in? [team m]
  (let [k (norm/team-key team)]
    (or (= k (norm/team-key (:home-team m)))
        (= k (norm/team-key (:away-team m))))))

;; ---------------------------------------------------------------------------
;; Match queries
;; ---------------------------------------------------------------------------

(defn find-matches
  "Return matches passing every supplied filter in `opts`:

    :team        team plays in the match (home or away)
    :venue       :home or :away — restrict `:team` to that side
    :opponent    other team must be this one (pairs with :team)
    :competition exact competition label
    :season      integer season/year
    :from :to    inclusive LocalDate bounds on :date
    :limit       cap the number of results

  Results are ordered most-recent first."
  [db {:keys [team venue opponent competition season from to limit]}]
  (let [tk (some-> team norm/team-key)]
    (cond->> (:matches db)
      team (filter (fn [m]
                     (case venue
                       :home (= tk (norm/team-key (:home-team m)))
                       :away (= tk (norm/team-key (:away-team m)))
                       (plays-in? team m))))
      opponent (filter #(plays-in? opponent %))
      competition (filter #(= competition (:competition %)))
      season (filter #(= season (:season %)))
      from (filter #(and (:date %) (not (.isBefore (:date %) from))))
      to (filter #(and (:date %) (not (.isAfter (:date %) to))))
      true (sort-by :date #(compare %2 %1))
      true vec
      limit (take limit)
      limit vec)))

(defn head-to-head
  "Head-to-head summary between `team-a` and `team-b`."
  [db team-a team-b]
  (let [ka (norm/team-key team-a)
        ms (find-matches db {:team team-a :opponent team-b})]
    (reduce
     (fn [acc m]
       (let [a-home? (= ka (norm/team-key (:home-team m)))
             a-goals (if a-home? (:home-goal m) (:away-goal m))
             b-goals (if a-home? (:away-goal m) (:home-goal m))]
         (-> acc
             (update :total inc)
             (update :team-a-goals + a-goals)
             (update :team-b-goals + b-goals)
             (update (cond (> a-goals b-goals) :team-a-wins
                           (< a-goals b-goals) :team-b-wins
                           :else :draws)
                     inc))))
     {:team-a team-a :team-b team-b :total 0
      :team-a-wins 0 :team-b-wins 0 :draws 0
      :team-a-goals 0 :team-b-goals 0}
     ms)))

;; ---------------------------------------------------------------------------
;; Team queries
;; ---------------------------------------------------------------------------

(defn team-record
  "Win/draw/loss record, goals and points for `team`, optionally narrowed by
  `:competition`, `:season` and `:venue` (:home/:away)."
  [db team opts]
  (let [k (norm/team-key team)
        ms (find-matches db (assoc opts :team team))
        base {:team team :matches 0 :wins 0 :draws 0 :losses 0
              :goals-for 0 :goals-against 0 :points 0}
        r (reduce
           (fn [acc m]
             (let [home? (= k (norm/team-key (:home-team m)))
                   gf (if home? (:home-goal m) (:away-goal m))
                   ga (if home? (:away-goal m) (:home-goal m))
                   result (cond (> gf ga) :wins (< gf ga) :losses :else :draws)]
               (-> acc
                   (update :matches inc)
                   (update :goals-for + gf)
                   (update :goals-against + ga)
                   (update result inc)
                   (update :points + (case result :wins 3 :draws 1 0)))))
           base ms)]
    (assoc r :win-rate (if (pos? (:matches r))
                         (round1 (* 100.0 (/ (:wins r) (:matches r))))
                         0.0))))

;; ---------------------------------------------------------------------------
;; Competition queries
;; ---------------------------------------------------------------------------

(defn canonical-keyer
  "Build a name->key function for a single competition/season.

  A base name (e.g. \"atletico\") is treated as several clubs only when it
  appears with two or more distinct state suffixes in this set of names
  (Atlético-MG vs Atlético-GO). Otherwise every spelling — bare or suffixed —
  collapses onto the base key, so \"Flamengo\" and \"Flamengo-RJ\" merge."
  [raw-names]
  (let [suffixes (reduce (fn [m raw]
                           (update m (norm/team-key raw)
                                   (fnil conj #{}) (norm/team-suffix raw)))
                         {} raw-names)
        ambiguous? (fn [base] (>= (count (disj (get suffixes base) nil)) 2))]
    (fn [raw]
      (let [base (norm/team-key raw)]
        (if (ambiguous? base) (norm/strict-key raw) base)))))

(defn standings
  "Compute a league table for `competition` in `season`, sorted by points then
  goal difference then goals scored."
  [db competition season]
  (let [ms (find-matches db {:competition competition :season season})
        raws (mapcat (fn [m] [(or (:home-raw m) (:home-team m))
                              (or (:away-raw m) (:away-team m))]) ms)
        key-of (canonical-keyer raws)
        ;; a name is "disambiguated" when its key still carries the suffix
        disambiguated? (fn [raw] (not= (key-of raw) (norm/team-key raw)))
        accented? (fn [s] (not= s (norm/strip-accents s)))
        prefer (fn [a b] ; keep the more informative display name
                 (cond (nil? a) b
                       (and (accented? b) (not (accented? a))) b
                       :else a))
        ;; suffix-bearing display for disambiguated clubs, clean otherwise
        display (fn [raw] (if (disambiguated? raw)
                            (str/trim (str raw))
                            (norm/clean-team raw)))
        blank (fn [team] {:team team :played 0 :wins 0 :draws 0 :losses 0
                          :goals-for 0 :goals-against 0 :points 0})
        tally (fn [table raw gf ga]
                ;; group by the per-season canonical key so spelling variants
                ;; merge but distinct clubs (Atlético-MG vs -GO) stay separate
                (let [k (key-of raw)
                      team (display raw)
                      result (cond (> gf ga) :wins (< gf ga) :losses :else :draws)]
                  (update table k
                          (fn [row]
                            (-> (or row (blank team))
                                (update :team prefer team)
                                (update :played inc)
                                (update :goals-for + gf)
                                (update :goals-against + ga)
                                (update result inc)
                                (update :points + (case result :wins 3 :draws 1 0)))))))
        table (reduce (fn [t m]
                        (-> t
                            (tally (or (:home-raw m) (:home-team m))
                                   (:home-goal m) (:away-goal m))
                            (tally (or (:away-raw m) (:away-team m))
                                   (:away-goal m) (:home-goal m))))
                      {} ms)]
    (->> (vals table)
         (map #(assoc % :goal-difference (- (:goals-for %) (:goals-against %))))
         (sort-by (juxt :points :goal-difference :goals-for) #(compare %2 %1))
         vec)))

;; ---------------------------------------------------------------------------
;; Player queries
;; ---------------------------------------------------------------------------

(defn- contains-key? [haystack needle]
  (and haystack needle
       (str/includes? (norm/team-key haystack) (norm/team-key needle))))

(defn search-players
  "Filter players by `:name`, `:nationality`, `:club`, `:position` (all
  accent/case-insensitive substring matches) and sort by overall rating
  descending. `:limit` caps the result count."
  [db {:keys [name nationality club position limit]}]
  (cond->> (:players db)
    name (filter #(contains-key? (:name %) name))
    nationality (filter #(contains-key? (:nationality %) nationality))
    club (filter #(contains-key? (:club %) club))
    position (filter #(= (norm/team-key (:position %)) (norm/team-key position)))
    true (sort-by #(or (:overall %) 0) >)
    true vec
    limit (take limit)
    limit vec))

;; ---------------------------------------------------------------------------
;; Statistical analysis
;; ---------------------------------------------------------------------------

(defn avg-goals-per-match
  "Average total goals scored per match across `matches`."
  [matches]
  (if (seq matches)
    (round1 (/ (reduce + (map #(+ (:home-goal %) (:away-goal %)) matches))
               (double (count matches))))
    0.0))

(defn home-win-rate
  "Percentage of `matches` won by the home team."
  [matches]
  (if (seq matches)
    (round1 (* 100.0 (/ (count (filter #(> (:home-goal %) (:away-goal %)) matches))
                        (double (count matches)))))
    0.0))

(defn biggest-wins
  "Top `n` matches by goal margin, each annotated with `:margin`."
  [matches n]
  (->> matches
       (map #(assoc % :margin (abs (- (:home-goal %) (:away-goal %)))))
       (sort-by :margin >)
       (take n)
       vec))
