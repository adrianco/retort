(ns brazilian-soccer-mcp.queries
  (:require [clojure.string :as str]
            [brazilian-soccer-mcp.normalization :as norm]
            [brazilian-soccer-mcp.dates :as dates]))

(defn- match-involves-team? [match team]
  (or (norm/team-matches? team (:home-team match))
      (norm/team-matches? team (:away-team match))))

(defn- competition-matches? [match competition]
  (when competition
    (or (= competition (:competition match))
        (str/includes? (str/lower-case (or (:competition match) ""))
                       (str/lower-case competition)))))

(defn find-matches
  "Filter matches by criteria map.
   Keys: :team, :role (:home/:away), :team1, :team2, :season, :competition, :date-from, :date-to"
  [matches {:keys [team role team1 team2 season competition date-from date-to]}]
  (cond->> matches
    team         (filter (fn [m]
                           (case role
                             :home (norm/team-matches? team (:home-team m))
                             :away (norm/team-matches? team (:away-team m))
                             (match-involves-team? m team))))
    (and team1 team2)
                 (filter (fn [m]
                           (or (and (norm/team-matches? team1 (:home-team m))
                                    (norm/team-matches? team2 (:away-team m)))
                               (and (norm/team-matches? team2 (:home-team m))
                                    (norm/team-matches? team1 (:away-team m))))))
    season       (filter #(= season (:season %)))
    competition  (filter #(competition-matches? % competition))
    date-from    (filter #(when-let [d (:date %)]
                            (dates/date-in-range? d date-from nil)))
    date-to      (filter #(when-let [d (:date %)]
                            (dates/date-in-range? d nil date-to)))
    true         vec))

(defn calculate-team-stats
  "Calculates win/draw/loss/goals stats for a team from a collection of matches."
  [matches team-name]
  (let [team-matches (filter #(match-involves-team? % team-name) matches)
        ;; only count matches with known scores
        scored-matches (filter #(and (some? (:home-goal %)) (some? (:away-goal %))) team-matches)
        init {:matches 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0}]
    (reduce (fn [acc m]
              (let [is-home (norm/team-matches? team-name (:home-team m))
                    gf      (int (if is-home (or (:home-goal m) 0) (or (:away-goal m) 0)))
                    ga      (int (if is-home (or (:away-goal m) 0) (or (:home-goal m) 0)))
                    result  (cond
                              (> gf ga) :win
                              (< gf ga) :loss
                              :else     :draw)]
                (-> acc
                    (update :matches inc)
                    (update (case result :win :wins :loss :losses :draw :draws) inc)
                    (update :goals-for + gf)
                    (update :goals-against + ga))))
            init
            scored-matches)))

(defn calculate-standings
  "Calculates league standings from matches. Returns sorted sequence of team maps."
  [matches]
  (let [all-teams (distinct (concat (map :home-team matches) (map :away-team matches)))
        team-stats (for [team (remove nil? all-teams)]
                     (let [stats (calculate-team-stats matches team)
                           pts (+ (* 3 (:wins stats)) (:draws stats))
                           gd  (- (:goals-for stats) (:goals-against stats))]
                       (assoc stats :team team :points pts :goal-diff gd)))]
    (sort-by (juxt (comp - :points) (comp - :goal-diff) (comp - :goals-for))
             team-stats)))

(defn biggest-wins
  "Returns top n matches by goal difference."
  [matches n]
  (->> matches
       (filter #(and (some? (:home-goal %)) (some? (:away-goal %))))
       (sort-by #(Math/abs (int (- (:home-goal %) (:away-goal %)))) >)
       (take n)
       vec))

(defn head-to-head-stats
  "Calculates head-to-head stats between two teams."
  [matches team1 team2]
  (let [h2h (find-matches matches {:team1 team1 :team2 team2})
        init {:total 0 :team1-wins 0 :team2-wins 0 :draws 0
              :team1-goals 0 :team2-goals 0}]
    (reduce (fn [acc m]
              (let [t1-is-home (norm/team-matches? team1 (:home-team m))
                    t1g (if t1-is-home (:home-goal m 0) (:away-goal m 0))
                    t2g (if t1-is-home (:away-goal m 0) (:home-goal m 0))
                    result (cond (> t1g t2g) :team1 (< t1g t2g) :team2 :else :draw)]
                (-> acc
                    (update :total inc)
                    (update (case result :team1 :team1-wins :team2 :team2-wins :draw :draws) inc)
                    (update :team1-goals + t1g)
                    (update :team2-goals + t2g))))
            init h2h)))
