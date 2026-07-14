(ns brazilian-soccer.queries
  "Context
  =======
  Pure query / analytics functions over the loaded data (see
  `brazilian-soccer.data`). Nothing here does any I/O or formatting - every
  function takes plain data and returns plain Clojure maps/vectors, which makes
  the BDD tests straightforward and keeps the MCP layer thin.

  Capabilities implemented (mirrors the spec's five categories):
    1. Match queries      - find-matches
    2. Team queries       - team-record
    3. Player queries     - search-players, club-nationality-breakdown
    4. Competition queries - standings, list-competitions, list-seasons
    5. Statistical analysis - head-to-head, league-stats, biggest-wins"
  (:require [clojure.string :as str]
            [brazilian-soccer.normalize :as nz]
            [brazilian-soccer.data :as data]))

;; ---------------------------------------------------------------------------
;; Predicates / helpers
;; ---------------------------------------------------------------------------

(defn- key-match?
  "Does the canonical `qkey` refer to the stored team `tkey`?"
  [qkey tkey]
  (and (seq qkey) (seq tkey)
       (or (= qkey tkey)
           (str/includes? tkey qkey)
           (str/includes? qkey tkey))))

(defn- home? [m qkey] (key-match? qkey (:home-key m)))
(defn- away? [m qkey] (key-match? qkey (:away-key m)))

(defn- involves? [m qkey] (or (home? m qkey) (away? m qkey)))

(defn- comp-match?
  "Loose competition match: substring on the accent-stripped lower-cased name."
  [m query]
  (or (str/blank? (str query))
      (str/includes? (nz/match-key (:competition m))
                     (nz/match-key query))))

(defn- in-season? [m season]
  (or (nil? season) (= (:season m) (data/parse-int season))))

(defn- in-range? [m date-from date-to]
  (let [d (:date m)]
    (and (or (str/blank? (str date-from)) (and d (>= (compare d date-from) 0)))
         (or (str/blank? (str date-to))   (and d (<= (compare d date-to) 0))))))

(defn outcome
  "Result of a match from the perspective of the team identified by `qkey`:
  :win, :loss or :draw."
  [m qkey]
  (let [hg (:home-goal m) ag (:away-goal m)]
    (cond
      (= hg ag) :draw
      (home? m qkey) (if (> hg ag) :win :loss)
      :else          (if (> ag hg) :win :loss))))

;; ---------------------------------------------------------------------------
;; 1. Match queries
;; ---------------------------------------------------------------------------

(defn find-matches
  "Return matches filtered by any combination of:
     :team        - team involved (home or away)
     :opponent    - second team (both must be present)
     :competition - substring of competition name
     :season      - exact year
     :date-from / :date-to - inclusive ISO bounds
     :limit       - cap on results (default 50)
  Results are sorted most-recent first."
  [{:keys [team opponent competition season date-from date-to limit]}]
  (let [tkey (nz/match-key team)
        okey (nz/match-key opponent)
        limit (or limit 50)]
    (->> (data/matches)
         (filter (fn [m]
                   (and (or (str/blank? (str team)) (involves? m tkey))
                        (or (str/blank? (str opponent)) (involves? m okey))
                        (comp-match? m competition)
                        (in-season? m season)
                        (in-range? m date-from date-to))))
         (sort-by :date #(compare %2 %1))
         (take limit)
         vec)))

;; ---------------------------------------------------------------------------
;; 2. Team queries
;; ---------------------------------------------------------------------------

(defn- blank-record []
  {:matches 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0})

(defn team-record
  "Win/draw/loss + goals record for a team.
     :team        - required
     :season      - optional year
     :competition - optional substring
     :venue       - :home, :away or :all (default :all)
  Returns a map including :win-rate (0-100, 1 dp) and :display name."
  [{:keys [team season competition venue] :or {venue :all}}]
  (let [tkey (nz/match-key team)
        venue (keyword venue)
        ms (->> (data/matches)
                (filter (fn [m]
                          (and (comp-match? m competition)
                               (in-season? m season)
                               (case venue
                                 :home (home? m tkey)
                                 :away (away? m tkey)
                                 (involves? m tkey))))))
        rec (reduce
             (fn [acc m]
               (let [at-home (home? m tkey)
                     gf (if at-home (:home-goal m) (:away-goal m))
                     ga (if at-home (:away-goal m) (:home-goal m))
                     res (outcome m tkey)]
                 (-> acc
                     (update :matches inc)
                     (update :goals-for + gf)
                     (update :goals-against + ga)
                     (update (case res :win :wins :loss :losses :draws) inc))))
             (blank-record)
             ms)
        n (:matches rec)]
    (assoc rec
           :team team
           :display (or (some #(when (home? % tkey) (:home %)) ms)
                        (some #(when (away? % tkey) (:away %)) ms)
                        team)
           :season (when season (data/parse-int season))
           :competition competition
           :venue venue
           :goal-diff (- (:goals-for rec) (:goals-against rec))
           :win-rate (if (pos? n)
                       (-> (/ (* 100.0 (:wins rec)) n)
                           (* 10) Math/round (/ 10.0))
                       0.0))))

;; ---------------------------------------------------------------------------
;; 5. Head-to-head
;; ---------------------------------------------------------------------------

(defn head-to-head
  "Aggregate record between two teams plus the underlying match list.
  Returns {:team1 :team2 :team1-wins :team2-wins :draws :matches [...]
           :team1-goals :team2-goals}."
  [{:keys [team1 team2 competition season]}]
  (let [k1 (nz/match-key team1)
        k2 (nz/match-key team2)
        ms (->> (data/matches)
                (filter (fn [m]
                          (and (involves? m k1) (involves? m k2)
                               (comp-match? m competition)
                               (in-season? m season))))
                (sort-by :date #(compare %2 %1)))]
    (reduce
     (fn [acc m]
       (let [t1-home (home? m k1)
             t1-g (if t1-home (:home-goal m) (:away-goal m))
             t2-g (if t1-home (:away-goal m) (:home-goal m))]
         (-> acc
             (update :team1-goals + t1-g)
             (update :team2-goals + t2-g)
             (update (cond (> t1-g t2-g) :team1-wins
                           (< t1-g t2-g) :team2-wins
                           :else :draws) inc))))
     {:team1 team1 :team2 team2
      :team1-wins 0 :team2-wins 0 :draws 0
      :team1-goals 0 :team2-goals 0
      :competition competition :season (when season (data/parse-int season))
      :matches (vec ms)}
     ms)))

;; ---------------------------------------------------------------------------
;; 4. Competition queries - standings
;; ---------------------------------------------------------------------------

(defn standings
  "League table computed from match results for a competition + season.
  3 points per win, 1 per draw. Sorted by points, goal difference, goals for.
  Returns a vector of row maps with :position assigned."
  [{:keys [competition season]}]
  (let [ms (->> (data/matches)
                (filter #(and (comp-match? % competition)
                              (in-season? % season))))
        ;; Group by canonical team key (not display name): in the suffix files
        ;; "Atletico-MG"/"-PR"/"-GO" share a display of "Atletico" but are
        ;; distinct clubs. Keep the first display seen as the row label.
        tally (reduce
               (fn [acc m]
                 (let [hg (:home-goal m) ag (:away-goal m)
                       upd (fn [acc tkey team gf ga res]
                             (update acc tkey
                                     (fn [r]
                                       (let [r (or r (assoc (blank-record) :team team))]
                                         (-> r
                                             (update :matches inc)
                                             (update :goals-for + gf)
                                             (update :goals-against + ga)
                                             (update (case res :win :wins
                                                            :loss :losses :draws) inc))))))
                       [hres ares] (cond (> hg ag) [:win :loss]
                                         (< hg ag) [:loss :win]
                                         :else     [:draw :draw])]
                   (-> acc
                       (upd (:home-key m) (:home m) hg ag hres)
                       (upd (:away-key m) (:away m) ag hg ares))))
               {}
               ms)]
    (->> (vals tally)
         (map (fn [r]
                (assoc r
                       :points (+ (* 3 (:wins r)) (:draws r))
                       :goal-diff (- (:goals-for r) (:goals-against r)))))
         (sort-by (juxt :points :goal-diff :goals-for)
                  #(compare %2 %1))
         (map-indexed (fn [i r] (assoc r :position (inc i))))
         vec)))

(defn list-competitions []
  (->> (data/matches) (map :competition) (remove nil?) distinct sort vec))

(defn list-seasons
  ([] (list-seasons nil))
  ([competition]
   (->> (data/matches)
        (filter #(comp-match? % competition))
        (keep :season) distinct sort vec)))

;; ---------------------------------------------------------------------------
;; 5. Statistical analysis
;; ---------------------------------------------------------------------------

(defn league-stats
  "Aggregate statistics for a competition + season slice:
     :matches, :total-goals, :avg-goals (per match),
     :home-wins, :away-wins, :draws, :home-win-rate (0-100)."
  [{:keys [competition season]}]
  (let [ms (->> (data/matches)
                (filter #(and (comp-match? % competition)
                              (in-season? % season))))
        n (count ms)
        goals (reduce + 0 (map #(+ (:home-goal %) (:away-goal %)) ms))
        hw (count (filter #(> (:home-goal %) (:away-goal %)) ms))
        aw (count (filter #(< (:home-goal %) (:away-goal %)) ms))
        dr (- n hw aw)
        rnd (fn [x] (-> x (* 100) Math/round (/ 100.0)))]
    {:competition competition
     :season (when season (data/parse-int season))
     :matches n
     :total-goals goals
     :avg-goals (if (pos? n) (rnd (/ (double goals) n)) 0.0)
     :home-wins hw :away-wins aw :draws dr
     :home-win-rate (if (pos? n) (-> (/ (* 100.0 hw) n) ((fn [x] (-> x (* 10) Math/round (/ 10.0))))) 0.0)}))

(defn biggest-wins
  "Matches sorted by goal margin (largest first)."
  [{:keys [competition season limit] :or {limit 10}}]
  (->> (data/matches)
       (filter #(and (comp-match? % competition) (in-season? % season)))
       (sort-by #(Math/abs (- (:home-goal %) (:away-goal %))) >)
       (take limit)
       vec))

;; ---------------------------------------------------------------------------
;; 3. Player queries
;; ---------------------------------------------------------------------------

(defn search-players
  "Filter / sort FIFA players.
     :name        - substring (accent-insensitive)
     :nationality - substring
     :club        - team key match
     :position    - exact (case-insensitive)
     :min-overall - lower bound on rating
     :limit       - default 25
  Results sorted by Overall descending."
  [{:keys [name nationality club position min-overall limit] :or {limit 25}}]
  (let [nk (nz/match-key name)
        natk (some-> nationality nz/strip-accents str/lower-case)
        ck (nz/match-key club)
        pos (some-> position str/lower-case str/trim)]
    (->> (data/players)
         (filter
          (fn [p]
            (and (or (str/blank? (str name))
                     (str/includes? (nz/match-key (:name p)) nk))
                 (or (str/blank? (str nationality))
                     (str/includes? (str/lower-case (nz/strip-accents (or (:nationality p) "")))
                                    natk))
                 (or (str/blank? (str club))
                     (key-match? ck (:club-key p)))
                 (or (str/blank? (str position))
                     (= pos (some-> (:position p) str/lower-case str/trim)))
                 (or (nil? min-overall)
                     (and (:overall p) (>= (:overall p) (data/parse-int min-overall)))))))
         (sort-by #(or (:overall %) 0) >)
         (take limit)
         vec)))

(defn club-nationality-breakdown
  "For players of a given nationality (default Brazil), group by club and
  report player count and average overall, sorted by count desc."
  [{:keys [nationality limit] :or {nationality "Brazil" limit 20}}]
  (let [natk (str/lower-case (nz/strip-accents nationality))]
    (->> (data/players)
         (filter #(and (:club %)
                       (str/includes? (str/lower-case (nz/strip-accents (or (:nationality %) "")))
                                      natk)))
         (group-by :club)
         (map (fn [[club ps]]
                {:club club
                 :players (count ps)
                 :avg-overall (let [os (keep :overall ps)]
                                (if (seq os)
                                  (-> (/ (reduce + os) (double (count os)))
                                      Math/round long)
                                  0))}))
         (sort-by :players >)
         (take limit)
         vec)))
