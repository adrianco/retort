(ns brazilian-soccer.queries
  "Pure query functions over the loaded match and player records.
  Team and competition arguments are free text and are resolved with
  brazilian-soccer.names, so 'Palmeiras-SP' and 'palmeiras' are equivalent."
  (:require [brazilian-soccer.names :as names]
            [clojure.string :as str]))

(defn- team-keys [matches]
  (into #{} (mapcat (juxt :home-key :away-key)) matches))

(defn resolve-team
  "Returns the team key for a free-text name. Exact key match wins; otherwise the
  key containing the text with the most matches is used. Nil when nothing matches."
  [matches text]
  (let [k (names/team-key text)]
    (when k
      (let [keys (team-keys matches)]
        (cond
          (contains? keys k) k
          :else (let [candidates (filter #(str/includes? % k) keys)]
                  (when (seq candidates)
                    (apply max-key
                           (fn [c] (count (filter #(or (= c (:home-key %)) (= c (:away-key %))) matches)))
                           candidates))))))))

(defn- venue-ok? [tk venue m]
  (case venue
    :home (= tk (:home-key m))
    :away (= tk (:away-key m))
    (nil :any) true))

(defn filter-matches
  "Filters matches. Options (all optional):
  :team :opponent (free text), :competition (free text), :season (int),
  :from :to (ISO dates, inclusive), :venue (:home :away :any, requires :team)."
  [matches {:keys [team opponent competition season from to venue]}]
  (let [tk (when team (resolve-team matches team))
        ok (when opponent (resolve-team matches opponent))
        ck (when competition (names/competition-key competition))]
    (filter (fn [m]
              (and (or (nil? team) (and tk (or (= tk (:home-key m)) (= tk (:away-key m)))))
                   (or (nil? opponent) (and ok (or (= ok (:home-key m)) (= ok (:away-key m)))))
                   (or (nil? competition) (= ck (names/competition-key (:competition m))))
                   (or (nil? season) (= season (:season m)))
                   (or (nil? from) (not (neg? (compare (:date m) from))))
                   (or (nil? to) (not (pos? (compare (:date m) to))))
                   (or (nil? team) (venue-ok? tk (or venue :any) m))))
            matches)))

(defn perspective
  "Describes a match from one team's point of view."
  [team-key m]
  (let [home? (= team-key (:home-key m))
        [gf ga] (if home?
                  [(:home-goals m) (:away-goals m)]
                  [(:away-goals m) (:home-goals m)])]
    {:match m
     :venue (if home? :home :away)
     :opponent (if home? (:away m) (:home m))
     :gf gf
     :ga ga
     :result (cond (> gf ga) :win (< gf ga) :loss :else :draw)}))

(defn record
  "Aggregates perspectives into played/wins/draws/losses/goals and win rate."
  [perspectives]
  (let [n (count perspectives)
        by #(count (filter (fn [p] (= % (:result p))) perspectives))
        w (by :win)]
    {:played n
     :wins w
     :draws (by :draw)
     :losses (by :loss)
     :goals-for (reduce + 0 (map :gf perspectives))
     :goals-against (reduce + 0 (map :ga perspectives))
     :win-rate (if (pos? n) (/ (double w) n) 0.0)}))

(defn sort-recent [matches]
  (sort-by :date #(compare %2 %1) matches))

(defn search-matches
  "Matches matching the filters, most recent first."
  [matches opts]
  (sort-recent (filter-matches matches opts)))

(defn team-record
  "Win/draw/loss and goal record for a team under the same filters as search-matches."
  [matches {:keys [team] :as opts}]
  (let [tk (resolve-team matches team)]
    {:team-key tk
     :record (record (map #(perspective tk %) (filter-matches matches opts)))}))

(defn head-to-head
  "All meetings between two teams, from team-a's perspective."
  [matches a b]
  (let [ak (resolve-team matches a)
        bk (resolve-team matches b)
        ms (sort-recent (filter-matches matches {:team a :opponent b}))]
    {:team-a-key ak
     :team-b-key bk
     :record (record (map #(perspective ak %) ms))
     :matches ms}))

(defn standings
  "League table for a season and competition, points 3/1/0, ordered by points,
  goal difference, goals for and name."
  [matches {:keys [season competition] :or {competition "Brasileirão"}}]
  (let [ms (filter-matches matches {:season season :competition competition})
        names-by-key (reduce (fn [acc m]
                               (-> acc
                                   (update (:home-key m) #(or % (:home m)))
                                   (update (:away-key m) #(or % (:away m)))))
                             {} ms)
        blank {:w 0 :d 0 :l 0 :gf 0 :ga 0}
        table (reduce
               (fn [t m]
                 (let [hg (:home-goals m) ag (:away-goals m)
                       result (cond (> hg ag) [:w :l] (< hg ag) [:l :w] :else [:d :d])]
                   (-> t
                       (update (:home-key m) #(-> (or % blank)
                                                  (update (first result) inc)
                                                  (update :gf + hg)
                                                  (update :ga + ag)))
                       (update (:away-key m) #(-> (or % blank)
                                                  (update (second result) inc)
                                                  (update :gf + ag)
                                                  (update :ga + hg))))))
               {} ms)]
    (->> table
         (map (fn [[k {:keys [w d l gf ga]}]]
                {:team (names-by-key k)
                 :played (+ w d l)
                 :wins w :draws d :losses l
                 :goals-for gf :goals-against ga
                 :goal-difference (- gf ga)
                 :points (+ (* 3 w) d)}))
         (sort-by (juxt (comp - :points) (comp - :goal-difference)
                        (comp - :goals-for) :team))
         vec)))

(defn league-stats
  "Aggregate statistics over the filtered matches."
  [matches opts]
  (let [ms (filter-matches matches opts)
        n (count ms)
        results (frequencies (map (fn [m] (cond (> (:home-goals m) (:away-goals m)) :home
                                                 (< (:home-goals m) (:away-goals m)) :away
                                                 :else :draw))
                                  ms))
        goals (reduce + 0 (map #(+ (:home-goals %) (:away-goals %)) ms))
        margin (fn [m] (Math/abs (long (- (:home-goals m) (:away-goals m)))))
        biggest (->> ms
                     sort-recent
                     (sort-by margin >)
                     (filter #(pos? (margin %)))
                     (take 5))]
    {:matches n
     :total-goals goals
     :goals-per-match (if (pos? n) (/ (double goals) n) 0.0)
     :home-win-rate (if (pos? n) (/ (double (get results :home 0)) n) 0.0)
     :away-win-rate (if (pos? n) (/ (double (get results :away 0)) n) 0.0)
     :draw-rate (if (pos? n) (/ (double (get results :draw 0)) n) 0.0)
     :biggest-wins biggest}))

(defn search-players
  "Player search by name, nationality, club, position and minimum overall rating,
  highest rated first."
  [players {:keys [name nationality club position min-overall limit]}]
  (let [has-text? (fn [field q]
                    (and q field (str/includes? (names/normalize-text field) (names/normalize-text q))))]
    (->> players
         (filter #(or (nil? name) (has-text? (:name %) name)))
         (filter #(or (nil? nationality) (has-text? (:nationality %) nationality)))
         (filter #(or (nil? club) (has-text? (:club %) club)))
         (filter #(or (nil? position) (= (str/upper-case position) (:position %))))
         (filter #(or (nil? min-overall) (>= (or (:overall %) 0) min-overall)))
         (sort-by (comp - #(or (:overall %) 0)))
         (take (or limit 20))
         vec)))

(defn brazilian-club-summary
  "Brazilian-national players grouped by club: count and average overall rating."
  [players]
  (->> players
       (filter #(= "brazil" (names/normalize-text (:nationality %))))
       (remove #(nil? (:club %)))
       (group-by :club)
       (map (fn [[club ps]]
              {:club club
               :players (count ps)
               :average-overall (/ (double (reduce + 0 (keep :overall ps))) (count ps))}))
       (sort-by (juxt (comp - :players) :club))
       vec))
