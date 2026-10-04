(ns brsoccer.query
  "Pure query functions over the database built by `brsoccer.data`.
  Everything here returns plain data; `brsoccer.format` renders it as text."
  (:require [brsoccer.names :as names]
            [clojure.string :as str]))

(defn- invalid [msg & args]
  (throw (ex-info (apply format msg args) {:type :invalid-argument})))

(defn resolve-team
  "Set of team keys a free-text team name refers to. An exact match on the
  canonical key wins; otherwise every team whose key contains the text."
  [db q]
  (let [k (names/team-key q)
        f (names/fold q)]
    (cond
      (str/blank? f) #{}
      (contains? (:teams db) k) #{k}
      :else (into #{} (filter #(str/includes? % f)) (keys (:teams db))))))

(defn- team-or-throw [db q]
  (let [ks (resolve-team db q)]
    (when (empty? ks) (invalid "No team matching \"%s\" in the dataset" q))
    ks))

(defn team-label
  "Display name for a resolved team (several names when the query was ambiguous)."
  [db ks]
  (->> ks (map (:teams db)) sort (str/join " / ")))

(defn- competition-or-throw [q]
  (or (names/competition q)
      (invalid "Unknown competition \"%s\". Known: %s" q (str/join ", " names/competitions))))

(defn- stage-key [s]
  (-> (names/fold s) (str/replace #"[\s-]+" "") (str/replace #"s$" "")))

(defn- venue-key [venue]
  (let [v (names/fold (or venue "either"))]
    (case v
      ("home" "casa" "mandante") :home
      ("away" "fora" "visitante") :away
      ("either" "both" "all" "any" "") :either
      (invalid "venue must be home, away or either (got \"%s\")" venue))))

(defn find-matches
  "Matches satisfying every given criterion, most recent first.

  opts: :team :opponent :venue (home/away/either, relative to :team)
        :competition :season :date-from :date-to :stage :round"
  [db {:keys [team opponent venue competition season date-from date-to stage round]}]
  (let [ts (some->> team (team-or-throw db))
        os (some->> opponent (team-or-throw db))
        venue (venue-key venue)
        comp* (some-> competition competition-or-throw)
        stage (some-> stage stage-key)
        side? (fn [m home-set away-set]
                (and (or (nil? home-set) (home-set (:home m)))
                     (or (nil? away-set) (away-set (:away m)))))]
    (->> (:matches db)
         (filter (fn [m]
                   (and (or (nil? comp*) (= comp* (:competition m)))
                        (or (nil? season) (= season (:season m)))
                        (or (nil? round) (= round (:round m)))
                        (or (nil? stage) (= stage (some-> (:stage m) stage-key)))
                        (or (nil? date-from) (>= (compare (:date m) date-from) 0))
                        (or (nil? date-to) (<= (compare (:date m) date-to) 0))
                        (case (if ts venue :either*)
                          :home (side? m ts os)
                          :away (side? m os ts)
                          :either (or (side? m ts os) (side? m os ts))
                          ;; no :team given: :opponent alone matches either side
                          :either* (or (nil? os) (os (:home m)) (os (:away m)))))))
         (sort-by (juxt :date :home) #(compare %2 %1))
         vec)))

;; ---------------------------------------------------------------------------
;; Records and tables

(def ^:private zero {:played 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0})

(defn- add-result [r gf ga]
  (-> r
      (update :played inc)
      (update (cond (> gf ga) :wins (< gf ga) :losses :else :draws) inc)
      (update :goals-for + gf)
      (update :goals-against + ga)))

(defn- finish [{:keys [played wins draws goals-for goals-against] :as r}]
  (let [points (+ (* 3 wins) draws)]
    (assoc r
           :points points
           :goal-difference (- goals-for goals-against)
           :win-rate (if (pos? played) (* 100.0 (/ wins played)) 0.0)
           :points-per-match (if (pos? played) (double (/ points played)) 0.0))))

(defn record
  "Win/draw/loss record of the team(s) `ks` over `matches`.
  venue :home/:away restricts to games played at home/away."
  ([matches ks] (record matches ks :either))
  ([matches ks venue]
   (finish
    (reduce (fn [r {:keys [home away home-goals away-goals]}]
              (cond
                (and (ks home) (not= venue :away)) (add-result r home-goals away-goals)
                (and (ks away) (not= venue :home)) (add-result r away-goals home-goals)
                :else r))
            zero
            matches))))

(defn table
  "One finished record per team over `matches`, unsorted."
  [db matches venue]
  (->> matches
       (reduce (fn [acc {:keys [home away home-goals away-goals]}]
                 (cond-> acc
                   (not= venue :away) (update home (fnil add-result zero) home-goals away-goals)
                   (not= venue :home) (update away (fnil add-result zero) away-goals home-goals)))
               {})
       (map (fn [[k r]] (assoc (finish r) :team k :name ((:teams db) k))))))

(defn team-stats
  "Record of a team, overall and split by venue and by competition."
  [db {:keys [team venue] :as opts}]
  (let [ks (team-or-throw db team)
        venue (venue-key venue)
        matches (find-matches db (assoc opts :venue (name venue)))]
    {:team (team-label db ks)
     :venue venue
     :season (:season opts)
     :competition (some-> (:competition opts) names/competition)
     :overall (record matches ks venue)
     :home (record matches ks :home)
     :away (record matches ks :away)
     :by-competition (->> (group-by :competition matches)
                          (map (fn [[c ms]] (assoc (record ms ks venue) :competition c)))
                          (sort-by :played >))
     :matches matches}))

(defn head-to-head
  "Every meeting of two teams plus the aggregate record from team-a's side."
  [db {:keys [team-a team-b] :as opts}]
  (let [a (team-or-throw db team-a)
        b (team-or-throw db team-b)
        matches (find-matches db (assoc opts :team team-a :opponent team-b))
        rec (record matches a)]
    {:team-a (team-label db a)
     :team-b (team-label db b)
     :derby (when (and (= 1 (count a)) (= 1 (count b)))
              (names/derby-name (first a) (first b)))
     :played (:played rec)
     :a-wins (:wins rec)
     :b-wins (:losses rec)
     :draws (:draws rec)
     :a-goals (:goals-for rec)
     :b-goals (:goals-against rec)
     :matches matches}))

(defn- league? [competition]
  (contains? #{names/serie-a names/serie-b names/serie-c} competition))

(defn standings
  "League table calculated from match results (3 points per win; ties broken
  by wins, goal difference, goals scored). Points deducted by sporting courts
  are not in the data, so official tables can differ slightly.

  :complete? is true when (almost) every double round-robin game is present;
  only then is a champion named."
  [db {:keys [competition season]}]
  (let [comp* (competition-or-throw (or competition names/serie-a))
        _ (when-not season (invalid "season is required"))
        matches (find-matches db {:competition comp* :season season})
        all-rows (table db matches :either)
        ;; a handful of source rows are filed under the wrong tournament;
        ;; a "team" with one or two games in a full league season is one
        full-season? (some #(>= (:played %) 20) all-rows)
        stray (into #{} (comp (filter #(and full-season? (< (:played %) 3))) (map :team)) all-rows)
        matches (remove #(or (stray (:home %)) (stray (:away %))) matches)
        rows (->> (table db matches :either)
                  (sort-by (juxt :points :wins :goal-difference :goals-for) #(compare %2 %1))
                  (map-indexed (fn [i r] (assoc r :position (inc i))))
                  vec)
        n (count rows)
        complete? (and (= comp* names/serie-a)
                       (> n 1)
                       (>= (count matches) (- (* n (dec n)) 2)))
        relegated (cond (not complete?) 0 (= season 2003) 2 :else 4)]
    {:competition comp*
     :season season
     :league? (league? comp*)
     :complete? complete?
     :matches (count matches)
     :champion (when complete? (:name (first rows)))
     :relegated (mapv :name (take-last relegated rows))
     :rows rows}))

(def metrics
  {"points" :points
   "points_per_match" :points-per-match
   "win_rate" :win-rate
   "wins" :wins
   "losses" :losses
   "goals_for" :goals-for
   "goals_against" :goals-against
   "goal_difference" :goal-difference})

(defn rank-teams
  "Teams ranked by a metric, e.g. best away record or most goals scored.
  Rate metrics ignore teams with fewer than :min-matches games."
  [db {:keys [venue metric min-matches limit] :as opts}]
  (let [venue (venue-key venue)
        metric-name (or metric "points_per_match")
        k (or (metrics metric-name)
              (invalid "metric must be one of: %s" (str/join ", " (sort (keys metrics)))))
        matches (find-matches db (dissoc opts :venue :team :opponent))
        min-matches (or min-matches (if (:season opts) 1 20))]
    {:metric metric-name
     :venue venue
     :competition (some-> (:competition opts) names/competition)
     :season (:season opts)
     :rows (->> (table db matches venue)
                (filter #(>= (:played %) min-matches))
                (sort-by (juxt k :points :goal-difference) #(compare %2 %1))
                (take (or limit 10))
                vec)}))

(defn competition-stats
  "Goal averages and home/away/draw rates over the selected matches."
  [db opts]
  (let [matches (find-matches db opts)
        n (count matches)
        goals (reduce + (map #(+ (:home-goals %) (:away-goals %)) matches))
        share (fn [pred] (if (pos? n) (* 100.0 (/ (count (filter pred matches)) n)) 0.0))]
    {:competition (some-> (:competition opts) names/competition)
     :season (:season opts)
     :matches n
     :goals goals
     :goals-per-match (if (pos? n) (double (/ goals n)) 0.0)
     :home-win-rate (share #(> (:home-goals %) (:away-goals %)))
     :away-win-rate (share #(< (:home-goals %) (:away-goals %)))
     :draw-rate (share #(= (:home-goals %) (:away-goals %)))
     :by-competition (when-not (:competition opts)
                       (->> (group-by :competition matches)
                            (map (fn [[c ms]]
                                   {:competition c
                                    :matches (count ms)
                                    :goals-per-match
                                    (double (/ (reduce + (map #(+ (:home-goals %) (:away-goals %)) ms))
                                               (count ms)))}))
                            (sort-by :matches >)))}))

(defn biggest-wins
  "Matches with the largest winning margin (then most goals, then most recent)."
  [db {:keys [limit] :as opts}]
  (->> (find-matches db opts)
       (sort-by (juxt #(abs (- (:home-goals %) (:away-goals %)))
                      #(+ (:home-goals %) (:away-goals %))
                      :date)
                #(compare %2 %1))
       (take (or limit 10))
       vec))

(defn team-competitions
  "Competitions a team appears in, with seasons and record in each."
  [db {:keys [team]}]
  (let [ks (team-or-throw db team)
        matches (find-matches db {:team team})]
    {:team (team-label db ks)
     :competitions (->> (group-by :competition matches)
                        (map (fn [[c ms]]
                               (assoc (record ms ks)
                                      :competition c
                                      :seasons (vec (sort (distinct (keep :season ms)))))))
                        (sort-by :played >)
                        vec)}))

(defn derbies
  "Matches between traditional rivals, optionally narrowed like find-matches."
  [db opts]
  (->> (find-matches db opts)
       (keep (fn [m]
               (when-let [d (names/derby-name (:home m) (:away m))]
                 (assoc m :derby d))))
       vec))

(defn list-competitions
  "What the dataset holds: matches and season range per competition, row
  counts per source file."
  [db]
  {:files (:files db)
   :teams (count (:teams db))
   :players (count (:players db))
   :competitions (->> (group-by :competition (:matches db))
                      (map (fn [[c ms]]
                             {:competition c
                              :matches (count ms)
                              :first-season (apply min (keep :season ms))
                              :last-season (apply max (keep :season ms))}))
                      (sort-by :matches >)
                      vec)})

;; ---------------------------------------------------------------------------
;; Players

(def position-groups
  {"goalkeeper" #{"GK"}
   "defender" #{"CB" "LCB" "RCB" "LB" "RB" "LWB" "RWB"}
   "midfielder" #{"CM" "LCM" "RCM" "CDM" "LDM" "RDM" "CAM" "LAM" "RAM" "LM" "RM"}
   "forward" #{"ST" "LS" "RS" "CF" "LF" "RF" "LW" "RW"}})

(defn- positions [q]
  (let [f (str/replace (names/fold q) #"s$" "")]
    (or (position-groups f)
        (position-groups ({"keeper" "goalkeeper" "goalie" "goalkeeper"
                           "defence" "defender" "defense" "defender"
                           "midfield" "midfielder" "attacker" "forward"
                           "striker" "forward" "winger" "forward"} f))
        #{(str/upper-case (str/trim q))})))

(defn- club-filter
  "Players of a club: by canonical team key when any club has it (so
  \"Santos\" is not \"Santos Laguna\"), else by substring of the club name."
  [q players]
  (let [k (names/team-key q)
        f (names/fold q)
        exact (filter #(= k (:club-key %)) players)]
    (if (seq exact)
      exact
      (filter #(some-> (:club %) names/fold (str/includes? f)) players))))

(defn search-players
  "FIFA players matching every criterion, best rated first.
  Returns {:total n :players [...]} where :players is cut to :limit."
  [db {:keys [name nationality club position min-overall max-age limit]}]
  (let [tokens (some-> name names/fold (str/split #" "))
        nat (some-> nationality names/fold)
        nat (get {"brazilian" "brazil" "brasil" "brazil" "brasileiro" "brazil"} nat nat)
        pos (some-> position positions)
        found (cond->> (:players db)
                club (club-filter club)
                tokens (filter (fn [p] (let [n (names/fold (:name p))]
                                         (every? #(str/includes? n %) tokens))))
                nat (filter #(= nat (names/fold (:nationality %))))
                pos (filter #(pos (:position %)))
                min-overall (filter #(>= (or (:overall %) 0) min-overall))
                max-age (filter #(<= (or (:age %) 999) max-age)))
        sorted (sort-by (juxt (comp - #(or % 0) :overall) :name) found)]
    {:total (count sorted)
     :players (vec (take (or limit 20) sorted))}))

(defn- brazilian-club-keys
  "Keys of clubs seen in the Brazilian domestic league files."
  [db]
  (into #{}
        (comp (filter #(league? (:competition %)))
              (mapcat (juxt :home :away)))
        (:matches db)))

(defn brazilian-club-squads
  "FIFA squads of the clubs that also appear in the Brazilian league data —
  a join between the player file and the match files."
  [db {:keys [nationality]}]
  (let [clubs (brazilian-club-keys db)
        nat (some-> nationality names/fold)]
    (->> (:players db)
         (filter #(and (clubs (:club-key %))
                       (or (nil? nat) (= nat (names/fold (:nationality %))))))
         (group-by :club)
         (map (fn [[club ps]]
                {:club club
                 :players (count ps)
                 :average-overall (double (/ (reduce + (keep :overall ps)) (count ps)))
                 :best (apply max-key #(or (:overall %) 0) ps)}))
         (sort-by (juxt (comp - :average-overall) :club))
         vec)))

(defn team-profile
  "Cross-file view of a club: match record per competition, latest results
  and its FIFA squad."
  [db {:keys [team limit]}]
  (let [ks (team-or-throw db team)
        matches (find-matches db {:team team})
        squad (->> (:players db)
                   (filter #(ks (:club-key %)))
                   (sort-by (comp - #(or % 0) :overall)))]
    {:team (team-label db ks)
     :overall (record matches ks)
     :competitions (:competitions (team-competitions db {:team team}))
     :recent (vec (take (or limit 5) matches))
     :squad-size (count squad)
     :squad (vec (take (or limit 5) squad))}))
