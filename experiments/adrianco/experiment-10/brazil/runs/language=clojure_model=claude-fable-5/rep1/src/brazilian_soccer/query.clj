(ns brazilian-soccer.query
  "CONTEXT
  =======
  Query layer for the Brazilian Soccer MCP server.

  Pure functions over the database loaded by brazilian-soccer.data.  Each
  function takes the db map explicitly (so tests can pass a fixture) and
  returns plain Clojure data; formatting into human-readable answers happens
  in brazilian-soccer.tools.

  Provided queries (mirroring the capabilities in TASK.md):
    * search-matches    - filter matches by team(s), competition, season, dates
    * head-to-head      - all meetings between two clubs plus a W/D/L summary
    * team-record       - W/D/L, goals for/against, win rate (optionally by
                          season / competition / home / away)
    * standings         - league table calculated from match results
    * biggest-wins      - largest margins of victory
    * competition-stats - matches, goals/match, home-win/draw/away-win rates
    * search-players    - FIFA player search by name/nationality/club/position
    * top-players       - search-players sorted by Overall rating
    * club-player-summary - player counts and average rating per club
    * competitions / seasons-covered / data summary helpers

  Team arguments are free-form strings; they are canonicalized with
  data/canonical-team and matched against canonical ids (exact first, then
  substring for queries of 4+ characters), so \"Sao Paulo\", \"São Paulo\" and
  \"Sao Paulo-SP\" all hit the same club."
  (:require [brazilian-soccer.data :as data]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; Team matching

(defn team-pred
  "Predicate over canonical team ids for a free-form team query string."
  [team-query]
  (let [q (data/canonical-team team-query)]
    (fn [canon]
      (and canon
           (or (= q canon)
               (and (>= (count q) 4) (str/includes? canon q)))))))

(defn- match-involves? [pred m]
  (or (pred (:home m)) (pred (:away m))))

;; ---------------------------------------------------------------------------
;; Match search

(defn- competition-pred [competition]
  (if (str/blank? (str competition))
    (constantly true)
    (let [q (str/lower-case (data/strip-accents (str competition)))]
      (fn [m]
        (str/includes? (str/lower-case (data/strip-accents (str (:competition m)))) q)))))

(defn search-matches
  "Filter matches.  opts:
    :team        free-form team name (home or away)
    :opponent    second team; both must be involved
    :competition substring, accent-insensitive (\"brasileirao\", \"libertadores\")
    :season      integer year
    :date-from / :date-to  ISO date strings (inclusive)
    :stage       substring of cup/tournament stage (\"final\", \"group stage\")"
  [db {:keys [team opponent competition season date-from date-to stage]}]
  (let [t1   (some-> team team-pred)
        t2   (some-> opponent team-pred)
        comp (competition-pred competition)
        from (some-> date-from data/parse-date)
        to   (some-> date-to data/parse-date)
        sn   (when season (data/parse-long* (str season)))
        stg  (some-> stage str str/lower-case not-empty)]
    (->> (:matches db)
         (filter (fn [m]
                   (and (or (nil? t1) (match-involves? t1 m))
                        (or (nil? t2) (match-involves? t2 m))
                        ;; when both teams given, require they are distinct sides
                        (or (nil? t1) (nil? t2)
                            (or (and (t1 (:home m)) (t2 (:away m)))
                                (and (t1 (:away m)) (t2 (:home m)))))
                        (comp m)
                        (or (nil? sn) (= sn (:season m)))
                        (or (nil? from) (and (:date m) (not (.isBefore ^java.time.LocalDate (:date m) from))))
                        (or (nil? to) (and (:date m) (not (.isAfter ^java.time.LocalDate (:date m) to))))
                        (or (nil? stg)
                            (str/includes? (str/lower-case (str (:stage m) " " (:round m))) stg)))))
         (sort-by #(or (:date %) java.time.LocalDate/MIN))
         vec)))

;; ---------------------------------------------------------------------------
;; Head-to-head

(defn head-to-head
  "All meetings of two clubs with a win/draw summary from team1's perspective."
  [db team1 team2 & [{:keys [competition season]}]]
  (let [p1 (team-pred team1)
        matches (search-matches db {:team team1 :opponent team2
                                    :competition competition :season season})
        scored (filter #(and (:home-goals %) (:away-goals %)) matches)
        result (fn [m]
                 (let [t1-home? (p1 (:home m))
                       [gf ga] (if t1-home?
                                 [(:home-goals m) (:away-goals m)]
                                 [(:away-goals m) (:home-goals m)])]
                   (cond (> gf ga) :win (< gf ga) :loss :else :draw)))
        outcomes (frequencies (map result scored))]
    {:matches matches
     :played (count scored)
     :team1-wins (get outcomes :win 0)
     :team2-wins (get outcomes :loss 0)
     :draws (get outcomes :draw 0)
     :team1-goals (reduce + 0 (map #(if (p1 (:home %)) (:home-goals %) (:away-goals %)) scored))
     :team2-goals (reduce + 0 (map #(if (p1 (:home %)) (:away-goals %) (:home-goals %)) scored))}))

;; ---------------------------------------------------------------------------
;; Team statistics

(defn team-record
  "W/D/L and goal statistics for a club.  opts:
    :season :competition - as in search-matches
    :venue - \"home\", \"away\" or \"all\" (default)"
  [db team {:keys [season competition venue] :as opts}]
  (let [p (team-pred team)
        matches (search-matches db (select-keys opts [:season :competition]))
        venue (or venue "all")
        relevant (filter (fn [m]
                           (case venue
                             "home" (p (:home m))
                             "away" (p (:away m))
                             (match-involves? p m)))
                         matches)
        scored (filter #(and (:home-goals %) (:away-goals %)) relevant)
        per-match (map (fn [m]
                         (let [home? (p (:home m))
                               gf (if home? (:home-goals m) (:away-goals m))
                               ga (if home? (:away-goals m) (:home-goals m))]
                           {:gf gf :ga ga
                            :outcome (cond (> gf ga) :win (< gf ga) :loss :else :draw)}))
                       scored)
        outcomes (frequencies (map :outcome per-match))
        played (count per-match)]
    {:team team
     :venue venue
     :played played
     :wins (get outcomes :win 0)
     :draws (get outcomes :draw 0)
     :losses (get outcomes :loss 0)
     :goals-for (reduce + 0 (map :gf per-match))
     :goals-against (reduce + 0 (map :ga per-match))
     :win-rate (if (pos? played)
                 (double (/ (get outcomes :win 0) played))
                 0.0)}))

;; ---------------------------------------------------------------------------
;; Standings

(defn standings
  "League table for a season calculated from match results (3 pts a win).
  Sorted by points, wins, goal difference, goals scored."
  [db season & [{:keys [competition]}]]
  (let [competition (or competition "Brasileirão Série A")
        matches (search-matches db {:season season :competition competition})
        scored (filter #(and (:home-goals %) (:away-goals %)) matches)
        accumulate
        (fn [acc team gf ga]
          (update acc team
                  (fn [s]
                    (let [s (or s {:played 0 :wins 0 :draws 0 :losses 0
                                   :goals-for 0 :goals-against 0 :points 0})]
                      (-> s
                          (update :played inc)
                          (update :goals-for + gf)
                          (update :goals-against + ga)
                          (update (cond (> gf ga) :wins (= gf ga) :draws :else :losses) inc)
                          (update :points + (cond (> gf ga) 3 (= gf ga) 1 :else 0)))))))
        table (reduce (fn [acc m]
                        (-> acc
                            (accumulate (:home m) (:home-goals m) (:away-goals m))
                            (accumulate (:away m) (:away-goals m) (:home-goals m))))
                      {} scored)]
    (->> table
         (map (fn [[team s]]
                (assoc s :team team
                       :goal-diff (- (:goals-for s) (:goals-against s)))))
         (sort-by (juxt :points :wins :goal-diff :goals-for))
         reverse
         (map-indexed (fn [i s] (assoc s :rank (inc i))))
         vec)))

;; ---------------------------------------------------------------------------
;; Statistical analysis

(defn biggest-wins
  "Matches with the largest victory margins, descending."
  [db {:keys [competition season team limit]}]
  (->> (search-matches db {:competition competition :season season :team team})
       (filter #(and (:home-goals %) (:away-goals %)))
       (map #(assoc % :margin (Math/abs (long (- (:home-goals %) (:away-goals %))))))
       (filter #(pos? (:margin %)))
       (sort-by (juxt :margin #(+ (:home-goals %) (:away-goals %))))
       reverse
       (take (or limit 10))
       vec))

(defn competition-stats
  "Aggregate statistics: matches, goals, averages, home/draw/away rates."
  [db {:keys [competition season]}]
  (let [scored (filter #(and (:home-goals %) (:away-goals %))
                       (search-matches db {:competition competition :season season}))
        n (count scored)
        goals (reduce + 0 (map #(+ (:home-goals %) (:away-goals %)) scored))
        outcome (fn [m] (cond (> (:home-goals m) (:away-goals m)) :home
                              (< (:home-goals m) (:away-goals m)) :away
                              :else :draw))
        outcomes (frequencies (map outcome scored))]
    {:matches n
     :total-goals goals
     :avg-goals (if (pos? n) (double (/ goals n)) 0.0)
     :home-wins (get outcomes :home 0)
     :draws (get outcomes :draw 0)
     :away-wins (get outcomes :away 0)
     :home-win-rate (if (pos? n) (double (/ (get outcomes :home 0) n)) 0.0)
     :draw-rate (if (pos? n) (double (/ (get outcomes :draw 0) n)) 0.0)
     :away-win-rate (if (pos? n) (double (/ (get outcomes :away 0) n)) 0.0)}))

(defn competitions
  "Distinct competitions with match counts and season coverage."
  [db]
  (->> (:matches db)
       (group-by :competition)
       (map (fn [[comp ms]]
              (let [seasons (keep :season ms)]
                {:competition comp
                 :matches (count ms)
                 :first-season (when (seq seasons) (apply min seasons))
                 :last-season (when (seq seasons) (apply max seasons))})))
       (sort-by :matches)
       reverse
       vec))

;; ---------------------------------------------------------------------------
;; Players (FIFA dataset)

(defn search-players
  "Filter FIFA players.  opts:
    :name :nationality :club :position - accent/case-insensitive substrings
    :min-overall - minimum Overall rating
  Sorted by Overall descending."
  [db {:keys [name nationality club position min-overall]}]
  (let [norm #(some-> % str data/strip-accents str/lower-case not-empty)
        qname (norm name)
        qnat (norm nationality)
        qclub (norm club)
        qpos (some-> position str str/upper-case str/trim not-empty)]
    (->> (:players db)
         (filter (fn [p]
                   (and (or (nil? qname) (str/includes? (:norm-name p) qname))
                        (or (nil? qnat) (str/includes? (str/lower-case (data/strip-accents (str (:nationality p)))) qnat))
                        (or (nil? qclub) (str/includes? (:norm-club p) qclub))
                        (or (nil? qpos) (= qpos (some-> (:position p) str/upper-case)))
                        (or (nil? min-overall) (and (:overall p) (>= (:overall p) min-overall))))))
         (sort-by #(or (:overall %) 0))
         reverse
         vec)))

(defn top-players [db opts limit]
  (vec (take (or limit 10) (search-players db opts))))

(defn club-player-summary
  "Player count and average Overall per club, filtered by an optional
  nationality, sorted by count."
  [db {:keys [nationality min-players]}]
  (->> (search-players db {:nationality nationality})
       (filter :club)
       (remove #(str/blank? (str (:club %))))
       (group-by :club)
       (map (fn [[club ps]]
              {:club club
               :players (count ps)
               :avg-overall (double (/ (reduce + 0 (keep :overall ps))
                                       (max 1 (count (keep :overall ps)))))}))
       (filter #(>= (:players %) (or min-players 1)))
       (sort-by (juxt :players :avg-overall))
       reverse
       vec))
