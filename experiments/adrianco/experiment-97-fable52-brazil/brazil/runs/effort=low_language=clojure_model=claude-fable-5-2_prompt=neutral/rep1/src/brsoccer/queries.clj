(ns brsoccer.queries
  "Pure query functions over the database built by brsoccer.data.
  Everything here returns data; text rendering lives in brsoccer.tools."
  (:require [brsoccer.data :as data]
            [brsoccer.teams :as teams]
            [clojure.string :as str]))

(defn fail [msg & {:as info}]
  (throw (ex-info msg (assoc info :user-error true))))

;; ---------------------------------------------------------------- resolution

(defn resolve-team
  "Canonical team key for a user-supplied name, or nil. Tries an exact
  normalised match, then a lenient parse (\"atletico mg\"), then falls back to
  the most-played team whose name contains the query."
  [db q]
  (when-not (str/blank? (str q))
    (let [teams-map (:teams db)
          k-of      #(teams/team-key (:index db) %)
          strict    (k-of (teams/parse q))
          lenient   (k-of (teams/parse q nil true))
          needle    (:base (teams/parse q))]
      (cond
        (teams-map strict)  strict
        (teams-map lenient) lenient
        :else (some->> (vals teams-map)
                       (filter #(or (str/includes? (:key %) needle)
                                    (str/includes? (:name-fold %) (teams/fold q))))
                       seq
                       (apply max-key :matches)
                       :key)))))

(defn team!
  [db q]
  (or (resolve-team db q)
      (fail (str "Unknown team: \"" q "\". Use list_teams to search team names."))))

(defn team-name [db k] (get-in db [:teams k :name] k))

(defn resolve-competition
  [q]
  (when-not (str/blank? (str q))
    (let [f (teams/fold q)]
      (cond
        (str/includes? f "libertadores")                       :libertadores
        (re-find #"copa do brasil|brazilian cup|\bcup\b|\bcopa\b" f) :copa-do-brasil
        (re-find #"^b$|serie b|second division" f)                    :serie-b
        (re-find #"^c$|serie c|third division" f)                     :serie-c
        (re-find #"^a$|serie a|brasileir|campeonato|brazilian league|first division" f) :serie-a
        :else (fail (str "Unknown competition: \"" q "\". Use one of: Brasileirão (Serie A), "
                         "Serie B, Serie C, Copa do Brasil, Libertadores."))))))

(defn parse-season [x]
  (when (some? x)
    (or (when (integer? x) x)
        (data/parse-int x)
        (fail (str "Invalid season: \"" x "\". Expected a year such as 2019.")))))

(defn parse-date! [x]
  (when-not (str/blank? (str x))
    (or (data/parse-date x)
        (fail (str "Invalid date: \"" x "\". Use YYYY-MM-DD or DD/MM/YYYY.")))))

;; -------------------------------------------------------------------- matches

(defn find-matches
  "Filter matches. Keys: :team :opponent (canonical keys), :venue (:home/:away,
  relative to :team), :competition, :season, :from, :to (ISO dates), :stage,
  :round. Result is newest first."
  [db {:keys [team opponent venue competition season from to stage round]}]
  (let [involves? (fn [m k] (or (= k (:home m)) (= k (:away m))))
        preds (cond-> []
                competition (conj #(= competition (:competition %)))
                season      (conj #(= season (:season %)))
                team        (conj (case venue
                                    :home #(= team (:home %))
                                    :away #(= team (:away %))
                                    #(involves? % team)))
                opponent    (conj #(involves? % opponent))
                from        (conj #(and (:date %) (<= (compare from (:date %)) 0)))
                to          (conj #(and (:date %) (>= (compare to (:date %)) 0)))
                stage       (conj #(= stage (:stage %)))
                round       (conj #(= round (:round %))))]
    (->> (:matches db)
         (filter (if (seq preds) (apply every-pred preds) (constantly true)))
         (sort-by #(or (:date %) "") #(compare %2 %1)))))

;; -------------------------------------------------------------------- records

(def ^:private zero {:p 0 :w 0 :d 0 :l 0 :gf 0 :ga 0})

(defn- add-result [r gf ga]
  (-> r
      (update :p inc)
      (update (cond (> gf ga) :w (< gf ga) :l :else :d) inc)
      (update :gf + gf)
      (update :ga + ga)))

(defn finalize [{:keys [p w d gf ga] :as r}]
  (assoc r
         :pts (+ (* 3 w) d)
         :gd (- gf ga)
         :win-rate (if (pos? p) (/ (* 100.0 w) p) 0.0)
         :ppg (if (pos? p) (/ (+ (* 3.0 w) d) p) 0.0)))

(defn table
  "Per-team records over `matches`. `venue` :home or :away counts only that
  side's games; anything else counts both."
  [matches venue]
  (->> matches
       (reduce (fn [t {:keys [home away hg ag]}]
                 (cond-> t
                   (not= venue :away) (update home #(add-result (or % zero) hg ag))
                   (not= venue :home) (update away #(add-result (or % zero) ag hg))))
               {})
       (map (fn [[k r]] (finalize (assoc r :team k))))))

(defn record
  "One team's record over `matches` (which may include other teams' games)."
  [matches team venue]
  (let [mine (filter #(or (= team (:home %)) (= team (:away %))) matches)]
    (or (first (filter #(= team (:team %)) (table mine venue)))
        (finalize (assoc zero :team team)))))

(defn standings
  "League table: points, then wins, goal difference, goals scored."
  [db competition season]
  (->> (table (find-matches db {:competition competition :season season}) :all)
       (sort-by (juxt (comp - :pts) (comp - :w) (comp - :gd) (comp - :gf) :team))
       vec))

(defn relegation-slots
  "Série A relegated 2 clubs in 2003 and 4 from 2004 on."
  [competition season]
  (case competition
    :serie-a (if (= season 2003) 2 4)
    :serie-b 4
    0))

(defn head-to-head [db a b opts]
  (let [ms (find-matches db (assoc opts :team a :opponent b))
        r  (record ms a :all)]
    {:matches ms :a-wins (:w r) :b-wins (:l r) :draws (:d r) :a-goals (:gf r) :b-goals (:ga r)}))

(defn summary [matches]
  (let [n     (count matches)
        goals (reduce + (map #(+ (:hg %) (:ag %)) matches))
        hw    (count (filter #(> (:hg %) (:ag %)) matches))
        aw    (count (filter #(< (:hg %) (:ag %)) matches))
        pct   #(if (pos? n) (/ (* 100.0 %) n) 0.0)]
    {:matches n :goals goals :avg-goals (if (pos? n) (/ (double goals) n) 0.0)
     :home-wins hw :away-wins aw :draws (- n hw aw)
     :home-win-rate (pct hw) :away-win-rate (pct aw) :draw-rate (pct (- n hw aw))
     :home-goals (reduce + (map :hg matches)) :away-goals (reduce + (map :ag matches))}))

(defn biggest-wins [matches]
  (sort-by (juxt #(- (abs (- (:hg %) (:ag %)))) #(- (+ (:hg %) (:ag %))) #(or (:date %) ""))
           (remove #(= (:hg %) (:ag %)) matches)))

(def ranking-metrics
  {"win_rate"        [:win-rate >]
   "points"          [:pts >]
   "points_per_game" [:ppg >]
   "wins"            [:w >]
   "goals_for"       [:gf >]
   "goals_against"   [:ga <]
   "goal_difference" [:gd >]
   "losses"          [:l >]})

(defn rankings [matches venue metric min-matches]
  (let [[k cmp] (ranking-metrics metric)
        sign    (if (= cmp >) -1 1)]
    (->> (table matches venue)
         (filter #(>= (:p %) min-matches))
         (sort-by (juxt #(* sign (k %)) (comp - :p) :team)))))

(defn derby-name [m] (teams/derby-index #{(:home m) (:away m)}))

(defn ties
  "Group knockout matches into ties (same two clubs) with aggregate scores."
  [matches]
  (->> (group-by #(hash-set (:home %) (:away %)) matches)
       vals
       (map (fn [ms]
              (let [legs (sort-by #(or (:date %) "") ms)
                    a    (:home (first legs))
                    b    (:away (first legs))
                    r    (record legs a :all)]
                {:legs legs :a a :b b :a-goals (:gf r) :b-goals (:ga r)
                 :winner (cond (> (:gf r) (:ga r)) a (< (:gf r) (:ga r)) b)})))
       (sort-by #(or (:date (first (:legs %))) ""))))

;; -------------------------------------------------------------------- players

(def position-groups
  {"forward"    #{"ST" "CF" "LF" "RF" "LS" "RS" "LW" "RW"}
   "midfielder" #{"CM" "CAM" "CDM" "LM" "RM" "LCM" "RCM" "LDM" "RDM" "LAM" "RAM"}
   "defender"   #{"CB" "LB" "RB" "LCB" "RCB" "LWB" "RWB"}
   "goalkeeper" #{"GK"}})

(defn- positions-for [q]
  (let [f (teams/fold q)
        f (cond (re-find #"^(forward|striker|attacker|atacante)s?$" f) "forward"
                (re-find #"^(midfielder|midfield|meia|meio-campo)s?$" f) "midfielder"
                (re-find #"^(defender|defence|defense|zagueiro|back)s?$" f) "defender"
                (re-find #"^(goalkeeper|keeper|goleiro|goalie)s?$" f) "goalkeeper"
                :else f)]
    (or (position-groups f)
        (let [code (str/upper-case f)]
          (if (some #(% code) (vals position-groups))
            #{code}
            (fail (str "Unknown position: \"" q "\". Use a FIFA code (ST, CAM, GK...) or "
                       "forward/midfielder/defender/goalkeeper.")))))))

(defn- name-tokens [q] (remove str/blank? (str/split (teams/fold q) #"[\s.]+")))

(defn find-players
  "Keys: :name :nationality :club :position :min-overall :max-age :sort.
  Returns {:players [...] :approximate? bool}; approximate means no player
  matched every word of the name, so partial matches are returned instead."
  [db {:keys [name nationality club position min-overall max-age sort]}]
  (let [club-fold (some-> club teams/fold)
        club-key  (when club (resolve-team db club))
        club-key  (when (and club-key (some #(= club-key (:club-key %)) (:players db))) club-key)
        nat       (some-> nationality teams/fold)
        nat       (get {"brazilian" "brazil" "brasil" "brazil" "brasileiro" "brazil"
                        "argentinian" "argentina" "argentine" "argentina"} nat nat)
        pos       (when-not (str/blank? (str position)) (positions-for position))
        base      (cond->> (:players db)
                    nat         (filter #(= nat (teams/fold (:nationality %))))
                    club        (filter #(and (:club %)
                                              (if club-key
                                                (= club-key (:club-key %))
                                                (str/includes? (teams/fold (:club %)) club-fold))))
                    pos         (filter #(pos (:position %)))
                    min-overall (filter #(>= (or (:overall %) 0) min-overall))
                    max-age     (filter #(<= (or (:age %) 999) max-age)))
        tokens    (when name (name-tokens name))
        exact     (if (seq tokens)
                    (filter (fn [p] (every? #(str/includes? (:name-fold p) %) tokens)) base)
                    base)
        partial   (when (and (seq tokens) (empty? exact))
                    (let [long (filter #(>= (count %) 4) tokens)]
                      (filter (fn [p] (some #(str/includes? (:name-fold p) %) long)) base)))
        order     (case sort
                    "potential" (juxt #(- (or (:potential %) 0)) :name)
                    "age"       (juxt #(or (:age %) 999) :name)
                    "name"      :name-fold
                    (juxt #(- (or (:overall %) 0)) #(- (or (:potential %) 0)) :name))]
    {:players (sort-by order (if (seq exact) exact partial))
     :approximate? (boolean (and (empty? exact) (seq partial)))}))

(defn club-summary
  "Player counts and average rating per Brazilian club in the FIFA data."
  [db nationality]
  (let [nat (some-> nationality teams/fold)]
    (->> (:players db)
         (filter :club-key)
         (filter #(or (nil? nat) (= nat (teams/fold (:nationality %)))))
         (group-by :club)
         (map (fn [[club ps]]
                {:club club :count (count ps)
                 :avg (/ (double (reduce + (map :overall ps))) (count ps))
                 :best (apply max-key :overall ps)}))
         (sort-by (juxt (comp - :avg) :club)))))
