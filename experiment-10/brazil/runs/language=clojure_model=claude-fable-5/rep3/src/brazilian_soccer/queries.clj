(ns brazilian-soccer.queries
  "Query and aggregation functions over the loaded datasets."
  (:require [brazilian-soccer.data :as data]
            [clojure.string :as str])
  (:import [java.time LocalDate]))

;; ---------------------------------------------------------------------------
;; Match filtering

(defn- date-key ^LocalDate [m]
  (or (:date m) LocalDate/MIN))

(defn played?
  "A match with a recorded final score."
  [m]
  (and (:home-goals m) (:away-goals m)))

(defn match-filter
  "Builds a predicate from user-facing criteria. All criteria are optional:
  :team / :opponent  team names (normalized for matching)
  :competition       free-form competition name
  :season            year
  :date-from/:date-to ISO dates (inclusive)"
  [{:keys [team opponent competition season date-from date-to]}]
  (let [tq   (some-> team data/norm-team)
        oq   (some-> opponent data/norm-team)
        comp (some-> competition data/norm-competition)
        from (some-> date-from data/parse-date)
        to   (some-> date-to data/parse-date)]
    (fn [m]
      (and (or (nil? tq)
               (data/team-matches? tq (:home m))
               (data/team-matches? tq (:away m)))
           (or (nil? oq)
               (and (or (nil? tq)
                        ;; with both teams given, require one on each side
                        (and (data/team-matches? tq (:home m))
                             (data/team-matches? oq (:away m)))
                        (and (data/team-matches? tq (:away m))
                             (data/team-matches? oq (:home m))))
                    (or (some? tq)
                        (data/team-matches? oq (:home m))
                        (data/team-matches? oq (:away m)))))
           (or (nil? comp) (= comp (:competition m)))
           (or (nil? season) (= season (:season m)))
           (or (nil? from) (and (:date m) (not (.isBefore ^LocalDate (:date m) from))))
           (or (nil? to) (and (:date m) (not (.isAfter ^LocalDate (:date m) to))))))))

(defn find-matches
  "Returns matches satisfying the criteria, most recent first."
  [db criteria]
  (->> (:matches db)
       (filter (match-filter criteria))
       (sort-by date-key)
       reverse))

;; ---------------------------------------------------------------------------
;; Team statistics

(defn- result-for
  "Returns [:win :draw :loss gf ga] from the perspective of `side`."
  [m side]
  (let [[gf ga] (if (= side :home)
                  [(:home-goals m) (:away-goals m)]
                  [(:away-goals m) (:home-goals m)])]
    [(cond (> gf ga) :win (= gf ga) :draw :else :loss) gf ga]))

(defn team-record
  "Aggregate W/D/L and goals for a team across the given matches.
  `venue` is :home, :away or :all."
  [matches team-query venue]
  (let [tq (data/norm-team team-query)]
    (reduce
     (fn [acc m]
       (let [side (cond
                    (and (not= venue :away) (data/team-matches? tq (:home m))) :home
                    (and (not= venue :home) (data/team-matches? tq (:away m))) :away
                    :else nil)]
         (if (and side (played? m))
           (let [[res gf ga] (result-for m side)]
             (-> acc
                 (update :played inc)
                 (update ({:win :wins :draw :draws :loss :losses} res) inc)
                 (update :gf + gf)
                 (update :ga + ga)))
           acc)))
     {:played 0 :wins 0 :draws 0 :losses 0 :gf 0 :ga 0}
     matches)))

(defn win-rate [{:keys [played wins]}]
  (if (pos? played) (* 100.0 (/ wins played)) 0.0))

(defn team-stats
  "W/D/L record for a team, optionally narrowed by season/competition/venue."
  [db {:keys [team venue] :as criteria}]
  (let [ms (filter (match-filter (dissoc criteria :venue)) (:matches db))]
    (team-record ms team (or venue :all))))

(defn head-to-head
  "Record between two teams plus the match list, most recent first."
  [db team1 team2]
  (let [ms (find-matches db {:team team1 :opponent team2})
        t1 (data/norm-team team1)
        rec (reduce
             (fn [acc m]
               (if-not (played? m)
                 acc
                 (let [side (if (data/team-matches? t1 (:home m)) :home :away)
                       [res] (result-for m side)]
                   (update acc ({:win :team1-wins :draw :draws :loss :team2-wins} res) inc))))
             {:team1-wins 0 :team2-wins 0 :draws 0}
             ms)]
    (assoc rec :matches ms)))

;; ---------------------------------------------------------------------------
;; Standings and competition-wide statistics

(defn- standings-row [display]
  {:display display :played 0 :wins 0 :draws 0 :losses 0 :gf 0 :ga 0 :points 0})

(defn standings
  "League table for a competition season, calculated from match results
  (3 points per win, 1 per draw). Sorted by points, wins, goal difference."
  [db {:keys [season competition]}]
  (let [comp (or (some-> competition data/norm-competition) "Brasileirão Série A")
        ms   (->> (:matches db)
                  (filter #(and (= comp (:competition %))
                                (= season (:season %))
                                (played? %))))
        upd  (fn [table m side]
               (let [k       (get-in m [side :key])
                     [res gf ga] (result-for m side)
                     display (if (= side :home) (:home-display m) (:away-display m))]
                 (update table k
                         (fn [row]
                           (let [row (or row (standings-row display))]
                             (-> row
                                 (update :played inc)
                                 (update ({:win :wins :draw :draws :loss :losses} res) inc)
                                 (update :gf + gf)
                                 (update :ga + ga)
                                 (update :points + ({:win 3 :draw 1 :loss 0} res))))))))
        table (reduce (fn [t m] (-> t (upd m :home) (upd m :away))) {} ms)]
    (->> (vals table)
         (map #(assoc % :gd (- (:gf %) (:ga %))))
         (sort-by (juxt :points :wins :gd :gf))
         reverse
         vec)))

(defn competition-summary
  "Totals, goal averages and home/draw/away split for a set of criteria."
  [db criteria]
  (let [ms (filter played? (filter (match-filter criteria) (:matches db)))
        n  (count ms)
        goals (reduce + 0 (map #(+ (:home-goals %) (:away-goals %)) ms))
        home-wins (count (filter #(> (:home-goals %) (:away-goals %)) ms))
        away-wins (count (filter #(< (:home-goals %) (:away-goals %)) ms))
        draws (- n home-wins away-wins)]
    {:matches n
     :goals goals
     :avg-goals (if (pos? n) (/ (double goals) n) 0.0)
     :home-wins home-wins :away-wins away-wins :draws draws
     :home-win-rate (if (pos? n) (* 100.0 (/ home-wins n)) 0.0)
     :draw-rate     (if (pos? n) (* 100.0 (/ draws n)) 0.0)
     :away-win-rate (if (pos? n) (* 100.0 (/ away-wins n)) 0.0)}))

(defn biggest-wins
  "Matches with the largest goal margin, optionally filtered."
  [db criteria limit]
  (->> (:matches db)
       (filter (match-filter criteria))
       (filter played?)
       (sort-by (fn [m] [(- (abs (- (:home-goals m) (:away-goals m))))
                         (- (+ (:home-goals m) (:away-goals m)))]))
       (take limit)))

(defn best-records
  "Teams ranked by win rate at the given venue (:home/:away/:all),
  requiring at least `min-matches` played."
  [db criteria venue min-matches limit]
  (let [ms (filter played? (filter (match-filter criteria) (:matches db)))
        upd (fn [table m side]
              (let [k (get-in m [side :key])
                    display (if (= side :home) (:home-display m) (:away-display m))
                    [res gf ga] (result-for m side)]
                (update table k
                        (fn [row]
                          (let [row (or row (standings-row display))]
                            (-> row
                                (update :played inc)
                                (update ({:win :wins :draw :draws :loss :losses} res) inc)
                                (update :gf + gf)
                                (update :ga + ga)))))))
        table (reduce (fn [t m]
                        (cond-> t
                          (not= venue :away) (upd m :home)
                          (not= venue :home) (upd m :away)))
                      {} ms)]
    (->> (vals table)
         (filter #(>= (:played %) min-matches))
         (map #(assoc % :win-rate (win-rate %)))
         (sort-by (juxt :win-rate :wins))
         reverse
         (take limit)
         vec)))

(defn competitions-overview
  "Per-competition coverage: seasons present and number of matches."
  [db]
  (->> (:matches db)
       (group-by :competition)
       (map (fn [[comp ms]]
              {:competition comp
               :matches (count ms)
               :seasons (->> ms (keep :season) distinct sort vec)}))
       (sort-by :competition)))

;; ---------------------------------------------------------------------------
;; Extended (corners/shots) statistics from the BR-Football dataset

(defn extended-stats
  "Average corners/shots/attacks for a team from the BR-Football dataset,
  plus the matching rows (most recent first)."
  [db {:keys [team] :as criteria}]
  (let [tq (data/norm-team team)
        ms (->> (:extended db)
                (filter (match-filter criteria))
                (sort-by date-key)
                reverse)
        side-of #(if (data/team-matches? tq (:home %)) :home :away)
        nums (for [m ms
                   :let [side (side-of m)
                         s (:stats m)]]
               (if (= side :home)
                 {:corners-for (:home-corners s) :corners-against (:away-corners s)
                  :shots-for (:home-shots s)     :shots-against (:away-shots s)
                  :attacks-for (:home-attacks s) :attacks-against (:away-attacks s)}
                 {:corners-for (:away-corners s) :corners-against (:home-corners s)
                  :shots-for (:away-shots s)     :shots-against (:home-shots s)
                  :attacks-for (:away-attacks s) :attacks-against (:home-attacks s)}))
        avg (fn [k]
              (let [vs (keep k nums)]
                (when (seq vs) (/ (double (reduce + vs)) (count vs)))))]
    {:matches ms
     :averages {:corners-for (avg :corners-for) :corners-against (avg :corners-against)
                :shots-for (avg :shots-for)     :shots-against (avg :shots-against)
                :attacks-for (avg :attacks-for) :attacks-against (avg :attacks-against)}}))

;; ---------------------------------------------------------------------------
;; Player queries (FIFA dataset)

(defn search-players
  "Filters the FIFA player list. All criteria optional:
  :name (substring), :nationality (exact, accent-insensitive),
  :club (substring), :position (exact), :min-overall, :max-age.
  Sorted by overall rating descending."
  [db {:keys [name nationality club position min-overall max-age]}]
  (let [nq   (some-> name data/strip-accents str/lower-case)
        natq (some-> nationality data/strip-accents str/lower-case)
        cq   (some-> club data/strip-accents str/lower-case)
        posq (some-> position str/upper-case str/trim)]
    (->> (:players db)
         (filter (fn [p]
                   (and (or (nil? nq) (str/includes? (:name-norm p) nq))
                        (or (nil? natq)
                            (= natq (some-> (:nationality p) data/strip-accents str/lower-case)))
                        (or (nil? cq) (some-> (:club-norm p) (str/includes? cq)))
                        (or (nil? posq) (= posq (:position p)))
                        (or (nil? min-overall) (and (:overall p) (>= (:overall p) min-overall)))
                        (or (nil? max-age) (and (:age p) (<= (:age p) max-age))))))
         (sort-by :overall)
         reverse)))

(defn find-player
  "Best match for a player name: exact normalized match first, then the
  highest-rated substring match."
  [db name]
  (let [nq (-> name data/strip-accents str/lower-case)
        candidates (search-players db {:name name})]
    (or (first (filter #(= nq (:name-norm %)) candidates))
        (first candidates))))
