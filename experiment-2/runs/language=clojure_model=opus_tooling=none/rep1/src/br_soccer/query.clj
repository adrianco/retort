(ns br-soccer.query
  "Query functions over matches and players."
  (:require [br-soccer.data :as d]
            [clojure.string :as str]))

;; ---- Match filters ----

(defn matches-by-team
  "Matches where team is home, away, or either."
  ([team] (matches-by-team team :either))
  ([team side]
   (let [hit? (fn [m]
                (case side
                  :home (d/team-matches? team (:home m))
                  :away (d/team-matches? team (:away m))
                  :either (or (d/team-matches? team (:home m))
                              (d/team-matches? team (:away m)))))]
     (filter hit? (d/all-matches)))))

(defn matches-between [team-a team-b]
  (filter (fn [m]
            (or (and (d/team-matches? team-a (:home m))
                     (d/team-matches? team-b (:away m)))
                (and (d/team-matches? team-b (:home m))
                     (d/team-matches? team-a (:away m)))))
          (d/all-matches)))

(defn matches-by-season [season]
  (let [s (if (string? season) (Long/parseLong (str/trim season)) season)]
    (filter #(= s (:season %)) (d/all-matches))))

(defn matches-by-competition [comp-name]
  (let [q (str/lower-case comp-name)]
    (filter #(str/includes? (str/lower-case (or (:competition %) "")) q)
            (d/all-matches))))

(defn matches-in-date-range [from to]
  (filter (fn [m]
            (let [d (:date m)]
              (and d (>= (compare d from) 0) (<= (compare d to) 0))))
          (d/all-matches)))

;; ---- Stats ----

(defn- result-for [team m]
  (cond
    (nil? (:home-goal m)) :unknown
    (nil? (:away-goal m)) :unknown
    (d/team-matches? team (:home m))
    (cond (> (:home-goal m) (:away-goal m)) :win
          (< (:home-goal m) (:away-goal m)) :loss
          :else :draw)
    (d/team-matches? team (:away m))
    (cond (> (:away-goal m) (:home-goal m)) :win
          (< (:away-goal m) (:home-goal m)) :loss
          :else :draw)
    :else :unknown))

(defn team-stats
  "Compute {:wins :draws :losses :goals-for :goals-against :matches} for a team.
   Optional opts: {:season s :side :home/:away/:either :competition c}."
  ([team] (team-stats team {}))
  ([team {:keys [season side competition] :or {side :either}}]
   (let [ms (->> (d/all-matches)
                 (filter (fn [m]
                           (case side
                             :home (d/team-matches? team (:home m))
                             :away (d/team-matches? team (:away m))
                             :either (or (d/team-matches? team (:home m))
                                         (d/team-matches? team (:away m))))))
                 (filter (fn [m] (or (nil? season) (= season (:season m)))))
                 (filter (fn [m] (or (nil? competition)
                                     (str/includes? (str/lower-case (or (:competition m) ""))
                                                    (str/lower-case competition)))))
                 (filter #(and (:home-goal %) (:away-goal %))))
         reduce-m (fn [acc m]
                    (let [r (result-for team m)
                          home? (d/team-matches? team (:home m))
                          gf (if home? (:home-goal m) (:away-goal m))
                          ga (if home? (:away-goal m) (:home-goal m))]
                      (-> acc
                          (update :matches inc)
                          (update r (fnil inc 0))
                          (update :goals-for + gf)
                          (update :goals-against + ga))))]
     (reduce reduce-m
             {:team team :matches 0 :win 0 :draw 0 :loss 0
              :goals-for 0 :goals-against 0}
             ms))))

(defn head-to-head [team-a team-b]
  (let [ms (filter #(and (:home-goal %) (:away-goal %))
                   (matches-between team-a team-b))
        tally (reduce
               (fn [acc m]
                 (let [r (result-for team-a m)]
                   (update acc r (fnil inc 0))))
               {:win 0 :draw 0 :loss 0}
               ms)]
     {:team-a team-a :team-b team-b
      :matches (count ms)
      :team-a-wins (:win tally)
      :team-b-wins (:loss tally)
      :draws (:draw tally)
      :results ms}))

(defn standings
  "Compute standings for a competition + season. 3 pts win, 1 pt draw."
  [competition season]
  (let [ms (->> (d/all-matches)
                (filter #(= season (:season %)))
                (filter #(str/includes? (str/lower-case (or (:competition %) ""))
                                        (str/lower-case competition)))
                (filter #(and (:home-goal %) (:away-goal %))))
        teams (distinct (mapcat (juxt :home :away) ms))
        stat (fn [team]
               (let [s (reduce
                        (fn [acc m]
                          (let [home? (d/team-matches? team (:home m))
                                away? (d/team-matches? team (:away m))]
                            (if (or home? away?)
                              (let [gf (if home? (:home-goal m) (:away-goal m))
                                    ga (if home? (:away-goal m) (:home-goal m))
                                    r (cond (> gf ga) :win (< gf ga) :loss :else :draw)]
                                (-> acc
                                    (update :matches inc)
                                    (update r (fnil inc 0))
                                    (update :goals-for + gf)
                                    (update :goals-against + ga)))
                              acc)))
                        {:team team :matches 0 :win 0 :draw 0 :loss 0
                         :goals-for 0 :goals-against 0}
                        ms)]
                 (assoc s
                        :points (+ (* 3 (:win s)) (:draw s))
                        :gd (- (:goals-for s) (:goals-against s)))))]
    (->> teams
         (map stat)
         (sort-by (juxt #(- (:points %)) #(- (:gd %)) #(- (:goals-for %))))
         vec)))

(defn biggest-wins
  "Matches sorted by goal margin, descending."
  ([] (biggest-wins 10))
  ([n]
   (->> (d/all-matches)
        (filter #(and (:home-goal %) (:away-goal %)))
        (sort-by #(- (Math/abs (- (:home-goal %) (:away-goal %)))))
        (take n)
        vec)))

(defn avg-goals-per-match
  ([] (avg-goals-per-match nil))
  ([competition]
   (let [ms (->> (d/all-matches)
                 (filter #(and (:home-goal %) (:away-goal %)))
                 (filter #(or (nil? competition)
                              (str/includes? (str/lower-case (or (:competition %) ""))
                                             (str/lower-case competition)))))]
     (if (empty? ms)
       0.0
       (double
        (/ (reduce + (map #(+ (:home-goal %) (:away-goal %)) ms))
           (count ms)))))))

;; ---- Player queries ----

(defn players-by-name [query]
  (let [q (str/lower-case (str/trim query))]
    (filter #(str/includes? (str/lower-case (or (:name %) "")) q)
            (d/all-players))))

(defn players-by-nationality [country]
  (let [q (str/lower-case country)]
    (filter #(= q (str/lower-case (or (:nationality %) "")))
            (d/all-players))))

(defn players-by-club [club]
  (let [q (str/lower-case club)]
    (filter #(str/includes? (str/lower-case (or (:club %) "")) q)
            (d/all-players))))

(defn top-players
  ([] (top-players 10 nil))
  ([n] (top-players n nil))
  ([n {:keys [nationality club position] :as _opts}]
   (->> (d/all-players)
        (filter #(or (nil? nationality)
                     (= (str/lower-case nationality)
                        (str/lower-case (or (:nationality %) "")))))
        (filter #(or (nil? club)
                     (str/includes? (str/lower-case (or (:club %) ""))
                                    (str/lower-case club))))
        (filter #(or (nil? position)
                     (= (str/lower-case position)
                        (str/lower-case (or (:position %) "")))))
        (filter :overall)
        (sort-by #(- (:overall %)))
        (take n)
        vec)))
