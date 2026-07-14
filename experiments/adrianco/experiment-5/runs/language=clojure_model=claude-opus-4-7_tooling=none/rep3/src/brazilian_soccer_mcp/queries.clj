(ns brazilian-soccer-mcp.queries
  "Query layer over the normalized match/player tables.

   Functions are pure: every public fn takes a `db` map produced by
   brazilian-soccer-mcp.data/load-all (or /db), so tests can pass a tiny
   in-memory db without touching disk."
  (:require [brazilian-soccer-mcp.normalize :as norm]
            [clojure.string                 :as str]))

;; ---- helpers -----------------------------------------------------------

(defn- team-in-match? [team m]
  (or (norm/matches? team (:home m))
      (norm/matches? team (:away m))))

(defn- between? [d lo hi]
  (and (or (nil? lo) (>= (compare d lo) 0))
       (or (nil? hi) (<= (compare d hi) 0))))

(defn- pts [winner?]
  (cond (= :win  winner?) 3
        (= :draw winner?) 1
        :else             0))

(defn- match-result-for [team m]
  (let [hg     (:home-goal m)
        ag     (:away-goal m)
        home?  (norm/matches? team (:home m))]
    (cond
      (or (nil? hg) (nil? ag)) nil
      (= hg ag)                :draw
      (and home? (> hg ag))    :win
      (and home? (< hg ag))    :loss
      (and (not home?) (> ag hg)) :win
      (and (not home?) (< ag hg)) :loss
      :else nil)))

;; ---- match queries -----------------------------------------------------

(defn matches-by-team
  "All matches a team played. Options:
     :competition  (substring match, case-insensitive)
     :season       integer
     :role         :home | :away | :either (default :either)
     :from / :to   ISO date string (inclusive)
     :limit        integer"
  ([db team]
   (matches-by-team db team {}))
  ([db team {:keys [competition season role from to limit]
             :or   {role :either}}]
   (cond->> (:matches db)
     true        (filter (fn [m]
                           (case role
                             :home   (norm/matches? team (:home m))
                             :away   (norm/matches? team (:away m))
                             :either (team-in-match? team m))))
     competition (filter (fn [m] (and (:competition m)
                                      (str/includes?
                                       (str/lower-case (:competition m))
                                       (str/lower-case competition)))))
     season      (filter #(= season (:season %)))
     from        (filter #(and (:date %) (between? (:date %) from to)))
     to          (filter #(and (:date %) (between? (:date %) from to)))
     true        vec
     limit       (#(take limit %))
     limit       vec)))

(defn matches-between
  "All matches between team-a and team-b (either side)."
  ([db a b] (matches-between db a b {}))
  ([db a b opts]
   (->> (matches-by-team db a opts)
        (filter #(team-in-match? b %))
        vec)))

(defn head-to-head
  "Aggregate result of every match between a and b."
  ([db a b] (head-to-head db a b {}))
  ([db a b opts]
   (let [ms (matches-between db a b opts)]
     (reduce (fn [acc m]
               (let [r (match-result-for a m)]
                 (-> acc
                     (update :total inc)
                     (update (case r
                               :win  :a-wins
                               :loss :b-wins
                               :draw :draws
                               :unknown) inc))))
             {:team-a a :team-b b :total 0 :a-wins 0 :b-wins 0 :draws 0 :unknown 0
              :matches ms}
             ms))))

;; ---- team stats --------------------------------------------------------

(defn team-stats
  "Aggregate W/D/L, goals for/against, and points for a team."
  ([db team] (team-stats db team {}))
  ([db team opts]
   (let [ms (matches-by-team db team opts)]
     (reduce
      (fn [acc m]
        (let [home?  (norm/matches? team (:home m))
              gf     (if home? (:home-goal m) (:away-goal m))
              ga     (if home? (:away-goal m) (:home-goal m))
              r      (match-result-for team m)]
          (cond-> (update acc :matches inc)
            gf            (update :goals-for     + gf)
            ga            (update :goals-against + ga)
            (= r :win)    (update :wins   inc)
            (= r :draw)   (update :draws  inc)
            (= r :loss)   (update :losses inc)
            (= r :win)    (update :points + 3)
            (= r :draw)   (update :points + 1)
            home?         (update :home-matches inc)
            (not home?)   (update :away-matches inc))))
      {:team team :matches 0 :wins 0 :draws 0 :losses 0
       :goals-for 0 :goals-against 0 :points 0
       :home-matches 0 :away-matches 0}
      ms))))

;; ---- standings ---------------------------------------------------------

(defn standings
  "Calculate a league table from finished matches.
   Options:
     :competition  substring (default 'Brasileirão')
     :season       required"
  ([db season] (standings db season {}))
  ([db season {:keys [competition] :or {competition "Brasileirão"}}]
   (let [ms (->> (:matches db)
                 (filter #(= season (:season %)))
                 (filter (fn [m] (and (:competition m)
                                      (str/includes?
                                       (str/lower-case (:competition m))
                                       (str/lower-case competition))))))
         add-row (fn [acc team home? gf ga]
                   (let [k        (norm/normalize team)
                         existing (get acc k {:team team :matches 0 :wins 0
                                              :draws 0 :losses 0
                                              :goals-for 0 :goals-against 0
                                              :points 0})
                         result   (cond (= gf ga) :draw
                                        (> gf ga) :win
                                        :else     :loss)]
                     (assoc acc k
                            (cond-> existing
                              true          (update :matches inc)
                              true          (update :goals-for + gf)
                              true          (update :goals-against + ga)
                              (= :win result)  (-> (update :wins inc)
                                                   (update :points + 3))
                              (= :draw result) (-> (update :draws inc)
                                                   (update :points + 1))
                              (= :loss result) (update :losses inc)))))
         table (reduce
                (fn [acc m]
                  (let [hg (:home-goal m) ag (:away-goal m)]
                    (if (or (nil? hg) (nil? ag))
                      acc
                      (-> acc
                          (add-row (:home m) true  hg ag)
                          (add-row (:away m) false ag hg)))))
                {} ms)]
     (->> (vals table)
          (map #(assoc % :goal-difference (- (:goals-for %) (:goals-against %))))
          (sort-by (juxt #(- (:points %))
                         #(- (:goal-difference %))
                         #(- (:goals-for %))))
          vec))))

;; ---- statistics --------------------------------------------------------

(defn avg-goals-per-match
  ([db] (avg-goals-per-match db {}))
  ([db {:keys [competition season]}]
   (let [ms (cond->> (:matches db)
              competition (filter (fn [m]
                                    (and (:competition m)
                                         (str/includes?
                                          (str/lower-case (:competition m))
                                          (str/lower-case competition)))))
              season      (filter #(= season (:season %)))
              true        (filter #(and (:home-goal %) (:away-goal %))))
         n  (count ms)]
     (if (zero? n)
       0.0
       (double (/ (reduce + (map #(+ (:home-goal %) (:away-goal %)) ms))
                  n))))))

(defn biggest-wins
  "Matches sorted by absolute goal difference, descending."
  ([db] (biggest-wins db {}))
  ([db {:keys [competition season limit] :or {limit 10}}]
   (->> (:matches db)
        (filter #(and (:home-goal %) (:away-goal %)))
        (filter (fn [m]
                  (and (or (nil? competition)
                           (and (:competition m)
                                (str/includes?
                                 (str/lower-case (:competition m))
                                 (str/lower-case competition))))
                       (or (nil? season) (= season (:season m))))))
        (sort-by #(- (Math/abs (- (:home-goal %) (:away-goal %)))))
        (take limit)
        vec)))

(defn home-win-rate
  ([db] (home-win-rate db {}))
  ([db {:keys [competition season]}]
   (let [ms (cond->> (:matches db)
              competition (filter (fn [m]
                                    (and (:competition m)
                                         (str/includes?
                                          (str/lower-case (:competition m))
                                          (str/lower-case competition)))))
              season      (filter #(= season (:season %)))
              true        (filter #(and (:home-goal %) (:away-goal %))))
         n  (count ms)
         hw (count (filter #(> (:home-goal %) (:away-goal %)) ms))]
     (if (zero? n) 0.0 (double (/ hw n))))))

;; ---- player queries ----------------------------------------------------

(defn- str-contains-ci? [haystack needle]
  (and haystack needle
       (str/includes? (str/lower-case (str haystack))
                      (str/lower-case (str needle)))))

(defn players-by-name
  ([db q] (players-by-name db q {}))
  ([db q {:keys [limit] :or {limit 25}}]
   (->> (:players db)
        (filter #(str-contains-ci? (:name %) q))
        (sort-by #(- (or (:overall %) 0)))
        (take limit)
        vec)))

(defn players-by-nationality
  ([db nat] (players-by-nationality db nat {}))
  ([db nat {:keys [club position min-overall limit]
            :or   {limit 25}}]
   (->> (:players db)
        (filter #(str-contains-ci? (:nationality %) nat))
        (filter #(or (nil? club)        (str-contains-ci? (:club %) club)))
        (filter #(or (nil? position)    (str-contains-ci? (:position %) position)))
        (filter #(or (nil? min-overall) (>= (or (:overall %) 0) min-overall)))
        (sort-by #(- (or (:overall %) 0)))
        (take limit)
        vec)))

(defn players-by-club
  ([db club] (players-by-club db club {}))
  ([db club {:keys [position limit] :or {limit 50}}]
   (->> (:players db)
        (filter #(str-contains-ci? (:club %) club))
        (filter #(or (nil? position) (str-contains-ci? (:position %) position)))
        (sort-by #(- (or (:overall %) 0)))
        (take limit)
        vec)))

;; ---- formatting --------------------------------------------------------

(defn format-match [m]
  (format "%s %s %d-%d %s (%s%s)"
          (or (:date m) "?")
          (or (:home m) "?")
          (or (:home-goal m) 0)
          (or (:away-goal m) 0)
          (or (:away m) "?")
          (or (:competition m) "?")
          (cond
            (:round m) (str " R" (:round m))
            (:stage m) (str " " (:stage m))
            :else      "")))

(defn format-team-stats [s]
  (let [{:keys [team matches wins draws losses goals-for goals-against points]} s
        wr (if (zero? matches) 0.0 (* 100.0 (/ (double wins) matches)))]
    (format "%s — %d matches, %dW %dD %dL, GF %d, GA %d, %d pts, %.1f%% win"
            team matches wins draws losses goals-for goals-against points wr)))
