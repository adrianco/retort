(ns soccer.query
  "Query functions over the loaded Brazilian soccer dataset."
  (:require [clojure.string :as str]
            [soccer.data :as data]))

(defn- lower [s] (when s (str/lower-case (str s))))

(defn- name-match?
  "Fuzzy team-name match: normalized substring match in either direction."
  [query team]
  (when (and query team)
    (let [q (lower (data/normalize-team query))
          t (lower (data/normalize-team team))]
      (or (= q t)
          (and (seq q) (seq t)
               (or (str/includes? t q) (str/includes? q t)))))))

(defn winner
  "Return :home, :away, or :draw for a match (or nil if unknown)."
  [{:keys [home-goal away-goal]}]
  (when (and home-goal away-goal)
    (cond (> home-goal away-goal) :home
          (< home-goal away-goal) :away
          :else :draw)))

;; ---------- Match queries ----------

(defn matches-by-team
  "Find matches involving team. :side one of :home :away :either (default)."
  ([matches team] (matches-by-team matches team :either))
  ([matches team side]
   (filter (fn [m]
             (case side
               :home (name-match? team (:home m))
               :away (name-match? team (:away m))
               (or (name-match? team (:home m))
                   (name-match? team (:away m)))))
           matches)))

(defn matches-between
  "Find matches where both team-a and team-b played (either side)."
  [matches team-a team-b]
  (filter (fn [m]
            (or (and (name-match? team-a (:home m)) (name-match? team-b (:away m)))
                (and (name-match? team-b (:home m)) (name-match? team-a (:away m)))))
          matches))

(defn matches-by-season [matches season]
  (filter #(= (:season %) season) matches))

(defn matches-by-competition [matches competition]
  (let [q (lower competition)]
    (filter #(some-> (:competition %) lower (str/includes? q)) matches)))

(defn matches-by-date-range
  "Filter matches with :date between start and end (inclusive, ISO strings)."
  [matches start end]
  (filter (fn [{:keys [date]}]
            (and date
                 (or (nil? start) (>= (compare date start) 0))
                 (or (nil? end)   (<= (compare date end)   0))))
          matches))

;; ---------- Team statistics ----------

(defn team-record
  "Compute a team's W/D/L/GF/GA record over a match seq.
   Optional :side :home or :away to restrict; else both."
  ([matches team] (team-record matches team nil))
  ([matches team side]
   (reduce
    (fn [acc m]
      (let [is-home? (name-match? team (:home m))
            is-away? (name-match? team (:away m))]
        (cond
          (and (= side :home) (not is-home?)) acc
          (and (= side :away) (not is-away?)) acc
          (not (or is-home? is-away?)) acc
          :else
          (let [hg (:home-goal m) ag (:away-goal m)]
            (if (or (nil? hg) (nil? ag))
              acc
              (let [gf (if is-home? hg ag)
                    ga (if is-home? ag hg)
                    w (update acc :matches inc)
                    w (update w :gf + gf)
                    w (update w :ga + ga)]
                (cond
                  (> gf ga) (update w :wins inc)
                  (< gf ga) (update w :losses inc)
                  :else     (update w :draws inc))))))))
    {:team (data/normalize-team team) :matches 0 :wins 0 :draws 0 :losses 0 :gf 0 :ga 0}
    matches)))

(defn head-to-head
  "Head-to-head record of team-a vs team-b across matches."
  [matches team-a team-b]
  (let [games (matches-between matches team-a team-b)]
    (reduce
     (fn [acc m]
       (let [a-home? (name-match? team-a (:home m))
             hg (:home-goal m) ag (:away-goal m)]
         (if (or (nil? hg) (nil? ag))
           acc
           (let [a-gf (if a-home? hg ag)
                 b-gf (if a-home? ag hg)
                 acc (-> acc
                         (update :matches inc)
                         (update :a-goals + a-gf)
                         (update :b-goals + b-gf))]
             (cond
               (> a-gf b-gf) (update acc :a-wins inc)
               (< a-gf b-gf) (update acc :b-wins inc)
               :else         (update acc :draws inc))))))
     {:team-a (data/normalize-team team-a)
      :team-b (data/normalize-team team-b)
      :matches 0 :a-wins 0 :b-wins 0 :draws 0 :a-goals 0 :b-goals 0}
     games)))

;; ---------- Competition standings ----------

(defn standings
  "Compute standings for a seq of matches (3/1/0 points)."
  [matches]
  (let [by-team (atom {})
        bump (fn [m team k v]
               (update-in m [team k] (fnil + 0) v))
        add-match
        (fn [acc {:keys [home away home-goal away-goal]}]
          (if (and home away home-goal away-goal)
            (let [acc (-> acc
                          (bump home :played 1)
                          (bump away :played 1)
                          (bump home :gf home-goal) (bump home :ga away-goal)
                          (bump away :gf away-goal) (bump away :ga home-goal))]
              (cond
                (> home-goal away-goal)
                (-> acc (bump home :wins 1) (bump home :points 3)
                    (bump away :losses 1))
                (< home-goal away-goal)
                (-> acc (bump away :wins 1) (bump away :points 3)
                    (bump home :losses 1))
                :else
                (-> acc (bump home :draws 1) (bump home :points 1)
                    (bump away :draws 1) (bump away :points 1))))
            acc))]
    (reset! by-team (reduce add-match {} matches))
    (->> @by-team
         (map (fn [[team stats]]
                (let [s (merge {:played 0 :wins 0 :draws 0 :losses 0
                                :gf 0 :ga 0 :points 0} stats)]
                  (assoc s :team team :gd (- (:gf s) (:ga s))))))
         (sort-by (juxt (comp - :points) (comp - :gd) (comp - :gf) :team))
         vec)))

(defn champion
  "Return the top team in the computed standings."
  [matches]
  (first (standings matches)))

;; ---------- Statistics ----------

(defn avg-goals-per-match [matches]
  (let [ms (filter #(and (:home-goal %) (:away-goal %)) matches)
        n (count ms)]
    (if (zero? n)
      0.0
      (double (/ (reduce + (map #(+ (:home-goal %) (:away-goal %)) ms)) n)))))

(defn home-win-rate [matches]
  (let [ms (filter #(and (:home-goal %) (:away-goal %)) matches)
        n (count ms)
        wins (count (filter #(> (:home-goal %) (:away-goal %)) ms))]
    (if (zero? n) 0.0 (double (/ wins n)))))

(defn biggest-wins
  "Return top n matches sorted by goal margin (descending)."
  ([matches] (biggest-wins matches 10))
  ([matches n]
   (->> matches
        (filter #(and (:home-goal %) (:away-goal %)))
        (sort-by #(- (Math/abs (- (:home-goal %) (:away-goal %)))))
        (take n)
        vec)))

(defn top-scoring-teams
  "Return teams sorted by goals scored across given matches."
  ([matches] (top-scoring-teams matches 10))
  ([matches n]
   (->> (standings matches)
        (sort-by (comp - :gf))
        (take n)
        vec)))

;; ---------- Player queries ----------

(defn players-by-name [players q]
  (let [lq (lower q)]
    (filter #(some-> (:name %) lower (str/includes? lq)) players)))

(defn players-by-nationality [players nat]
  (let [ln (lower nat)]
    (filter #(some-> (:nationality %) lower (= ln)) players)))

(defn players-by-club [players club]
  (let [lc (lower club)]
    (filter #(some-> (:club %) lower (str/includes? lc)) players)))

(defn players-by-position [players pos]
  (let [lp (lower pos)]
    (filter #(some-> (:position %) lower (= lp)) players)))

(defn top-players
  ([players] (top-players players 10))
  ([players n]
   (->> players
        (filter :overall)
        (sort-by (comp - :overall))
        (take n)
        vec)))

(defn avg-rating [players]
  (let [rs (keep :overall players)
        n (count rs)]
    (if (zero? n) 0.0 (double (/ (reduce + rs) n)))))
