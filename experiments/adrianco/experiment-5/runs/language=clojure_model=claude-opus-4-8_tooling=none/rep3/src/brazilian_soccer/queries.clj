;; =============================================================================
;; brazilian-soccer.queries
;; -----------------------------------------------------------------------------
;; Pure query and statistics functions over the normalised match/player data.
;;
;; Every function takes the data collection(s) explicitly so they are trivially
;; testable in isolation (no global state). The MCP tool layer (tools.clj) wires
;; these against the cached `data/db` snapshot.
;;
;; Query families (mirroring the spec's required capabilities):
;;   Matches       : find-matches, matches-between, head-to-head
;;   Teams         : team-record (overall / home / away, by season & competition)
;;   Players       : find-players, players-at-club, top-players
;;   Competition   : standings, champion
;;   Statistics    : avg-goals, biggest-wins, best-record
;; =============================================================================
(ns brazilian-soccer.queries
  (:require [clojure.string :as str]
            [brazilian-soccer.normalize :as norm]))

;; ---------------------------------------------------------------------------
;; Match queries
;; ---------------------------------------------------------------------------

(defn- team-side
  "Which side a query team plays on in a match: :home, :away, or nil."
  [match query]
  (cond
    (norm/matches-team? (:home-key match) query) :home
    (norm/matches-team? (:away-key match) query) :away
    :else nil))

(defn find-matches
  "Filter `matches` by optional criteria map:
     :team        match if team played (home or away)
     :home        match if team played at home
     :away        match if team played away
     :opponent    combined with :team/:home/:away -> matches involving both
     :competition substring (accent-insensitive) of competition label
     :season      integer year
     :from :to    inclusive ISO date bounds (yyyy-MM-dd lexical compare)
   Results are sorted by date descending (most recent first)."
  [matches {:keys [team home away opponent competition season from to]}]
  (let [comp-key (when competition (norm/match-key competition))]
    (->> matches
         (filter
          (fn [m]
            (and
             (or (nil? team)
                 (some? (team-side m team)))
             (or (nil? home)
                 (norm/matches-team? (:home-key m) home))
             (or (nil? away)
                 (norm/matches-team? (:away-key m) away))
             (or (nil? opponent)
                 (norm/matches-team? (:home-key m) opponent)
                 (norm/matches-team? (:away-key m) opponent))
             (or (nil? competition)
                 (when-let [c (norm/match-key (:competition m))]
                   (str/includes? c comp-key)))
             (or (nil? season)
                 (= season (:season m)))
             (or (nil? from) (and (:date m) (>= (compare (:date m) from) 0)))
             (or (nil? to)   (and (:date m) (<= (compare (:date m) to) 0))))))
         (sort-by (juxt :date :competition) #(compare %2 %1)))))

(defn matches-between
  "All matches where `team-a` and `team-b` faced each other (either venue)."
  [matches team-a team-b]
  (->> matches
       (filter (fn [m]
                 (or (and (norm/matches-team? (:home-key m) team-a)
                          (norm/matches-team? (:away-key m) team-b))
                     (and (norm/matches-team? (:home-key m) team-b)
                          (norm/matches-team? (:away-key m) team-a)))))
       (sort-by :date #(compare %2 %1))))

(defn head-to-head
  "Summarise a set of matches from `team-a`'s perspective.
   Returns {:team-a :team-b :played :a-wins :b-wins :draws
            :a-goals :b-goals} counting only matches with a recorded result."
  [matches team-a team-b]
  (reduce
   (fn [acc m]
     (let [a-home? (norm/matches-team? (:home-key m) team-a)
           hg (:home-goal m) ag (:away-goal m)]
       (if (and (some? hg) (some? ag))
         (let [a-goals (if a-home? hg ag)
               b-goals (if a-home? ag hg)]
           (cond-> (-> acc
                       (update :played inc)
                       (update :a-goals + a-goals)
                       (update :b-goals + b-goals))
             (> a-goals b-goals) (update :a-wins inc)
             (< a-goals b-goals) (update :b-wins inc)
             (= a-goals b-goals) (update :draws inc)))
         acc)))
   {:team-a team-a :team-b team-b
    :played 0 :a-wins 0 :b-wins 0 :draws 0 :a-goals 0 :b-goals 0}
   (matches-between matches team-a team-b)))

;; ---------------------------------------------------------------------------
;; Team queries / records
;; ---------------------------------------------------------------------------

(defn team-record
  "Win/draw/loss and goal record for `team` across the supplied matches.
   `venue` is :home, :away, or :all (default). Only matches with a recorded
   result are counted. Returns {:team :venue :played :wins :draws :losses
   :goals-for :goals-against :win-rate :display}."
  ([matches team] (team-record matches team :all))
  ([matches team venue]
   (let [rel (->> matches
                  (filter (fn [m]
                            (let [side (team-side m team)]
                              (and side
                                   (some? (:home-goal m)) (some? (:away-goal m))
                                   (case venue
                                     :home (= side :home)
                                     :away (= side :away)
                                     true)))))
                  vec)
         display (some (fn [m] (case (team-side m team)
                                 :home (:home m) :away (:away m) nil))
                       rel)
         init {:team team :venue venue :display (or display team)
               :played 0 :wins 0 :draws 0 :losses 0
               :goals-for 0 :goals-against 0}
         rec (reduce
              (fn [acc m]
                (let [home? (= :home (team-side m team))
                      gf (if home? (:home-goal m) (:away-goal m))
                      ga (if home? (:away-goal m) (:home-goal m))]
                  (cond-> (-> acc
                              (update :played inc)
                              (update :goals-for + gf)
                              (update :goals-against + ga))
                    (> gf ga) (update :wins inc)
                    (= gf ga) (update :draws inc)
                    (< gf ga) (update :losses inc))))
              init rel)]
     (assoc rec :win-rate (if (pos? (:played rec))
                            (double (/ (:wins rec) (:played rec)))
                            0.0)))))

;; ---------------------------------------------------------------------------
;; Player queries
;; ---------------------------------------------------------------------------

(defn find-players
  "Filter `players` by optional criteria:
     :name        substring of player name (accent-insensitive)
     :nationality substring of nationality
     :club        substring of club name
     :position    exact (case-insensitive) position code, e.g. \"ST\"
     :min-overall integer rating floor
   Sorted by overall rating descending."
  [players {:keys [name nationality club position min-overall]}]
  (let [name-q (when name (norm/match-key name))
        nat-q  (when nationality (norm/match-key nationality))
        club-q (when club (norm/match-key club))
        pos-q  (when position (str/upper-case (str/trim position)))]
    (->> players
         (filter
          (fn [p]
            (and
             (or (nil? name-q)
                 (and (:name-key p) (str/includes? (:name-key p) name-q)))
             (or (nil? nat-q)
                 (and (:nat-key p) (str/includes? (:nat-key p) nat-q)))
             (or (nil? club-q)
                 (and (:club-key p) (str/includes? (:club-key p) club-q)))
             (or (nil? pos-q)
                 (= pos-q (some-> (:position p) str/trim str/upper-case)))
             (or (nil? min-overall)
                 (and (:overall p) (>= (:overall p) min-overall))))))
         (sort-by :overall #(compare %2 %1)))))

(defn players-at-club
  "Players whose club matches `club`, highest-rated first."
  [players club]
  (find-players players {:club club}))

(defn top-players
  "Top `n` players, optionally filtered by nationality, by overall rating."
  ([players n] (top-players players n nil))
  ([players n nationality]
   (take n (find-players players (cond-> {} nationality (assoc :nationality nationality))))))

;; ---------------------------------------------------------------------------
;; Competition queries
;; ---------------------------------------------------------------------------

(defn standings
  "League table computed from `matches` (3 pts win / 1 draw). Each row:
   {:team :played :wins :draws :losses :goals-for :goals-against :gd :points}.
   Sorted by points, then goal difference, then goals-for (all descending).
   Pass already-filtered matches (e.g. one season of one competition).

   Teams are grouped by their canonical identity key (:home-uid/:away-uid) so
   different clubs sharing a base name (Atlético-MG vs Atlético-GO) stay
   separate; the :team label is the display name from the first match seen."
  [matches]
  (let [blank {:played 0 :wins 0 :draws 0 :losses 0
               :goals-for 0 :goals-against 0 :points 0}
        tally (fn [acc id team gf ga]
                (let [row (get acc id (assoc blank :team team))
                      pts (cond (> gf ga) 3 (= gf ga) 1 :else 0)]
                  (assoc acc id
                         (cond-> (-> row
                                     (update :played inc)
                                     (update :goals-for + gf)
                                     (update :goals-against + ga)
                                     (update :points + pts))
                           (> gf ga) (update :wins inc)
                           (= gf ga) (update :draws inc)
                           (< gf ga) (update :losses inc)))))
        table (reduce
               (fn [acc m]
                 (if (and (:home-uid m) (:away-uid m)
                          (some? (:home-goal m)) (some? (:away-goal m)))
                   (-> acc
                       (tally (:home-uid m) (:home m) (:home-goal m) (:away-goal m))
                       (tally (:away-uid m) (:away m) (:away-goal m) (:home-goal m)))
                   acc))
               {} matches)]
    (->> (vals table)
         (map #(assoc % :gd (- (:goals-for %) (:goals-against %))))
         (sort-by (juxt :points :gd :goals-for) #(compare %2 %1))
         vec)))

(defn champion
  "Top row of the computed standings, or nil for an empty table."
  [matches]
  (first (standings matches)))

;; ---------------------------------------------------------------------------
;; Statistical analysis
;; ---------------------------------------------------------------------------

(defn avg-goals
  "Average total goals per match over matches with a recorded result."
  [matches]
  (let [played (filter #(and (some? (:home-goal %)) (some? (:away-goal %))) matches)
        n (count played)]
    (if (pos? n)
      (double (/ (reduce + (map #(+ (:home-goal %) (:away-goal %)) played)) n))
      0.0)))

(defn home-win-rate
  "Fraction of decided+drawn matches won by the home team."
  [matches]
  (let [played (filter :winner matches)
        n (count played)]
    (if (pos? n)
      (double (/ (count (filter #(= :home (:winner %)) played)) n))
      0.0)))

(defn biggest-wins
  "Top `n` matches by goal margin (descending), most lop-sided first."
  [matches n]
  (->> matches
       (filter #(and (some? (:home-goal %)) (some? (:away-goal %))))
       (sort-by (fn [m] [(Math/abs (- (:home-goal m) (:away-goal m)))
                         (+ (:home-goal m) (:away-goal m))])
                #(compare %2 %1))
       (take n)))

(defn all-teams
  "Distinct cleaned team display names appearing in `matches`, sorted."
  [matches]
  (->> matches
       (mapcat (juxt :home :away))
       (remove nil?)
       distinct
       sort))
