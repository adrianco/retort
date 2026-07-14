(ns brazilian-soccer-mcp.tools
  "MCP tool implementations for Brazilian Soccer queries."
  (:require [brazilian-soccer-mcp.data :as data]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; Helpers
;; ---------------------------------------------------------------------------

(defn- involves-team?
  "True if query string matches either team in match."
  [query match]
  (or (data/team-matches? query (:home-team match))
      (data/team-matches? query (:away-team match))))

(defn- match-result
  "Returns :home-win :away-win or :draw."
  [match]
  (let [hg (:home-goals match)
        ag (:away-goals match)]
    (when (and (number? hg) (number? ag))
      (cond (> hg ag) :home-win
            (< hg ag) :away-win
            :else :draw))))

(defn- format-date [d]
  (if d (str d) "Unknown date"))

(defn- format-match [m]
  (str (format-date (:date m)) ": "
       (:home-team m) " " (:home-goals m)
       " - " (:away-goals m) " "
       (:away-team m)
       " [" (:competition m) "]"
       (when (:round m) (str " Round " (:round m)))
       (when (:stage m) (str " " (:stage m)))))

;; ---------------------------------------------------------------------------
;; 1. Match queries
;; ---------------------------------------------------------------------------

(defn find-matches-by-teams
  "Find all matches involving both team-a and team-b."
  [{:keys [team-a team-b limit] :or {limit 50}}]
  (let [db      (data/db)
        matches (->> (:all-matches db)
                     (filter #(and (involves-team? team-a %)
                                   (involves-team? team-b %)))
                     (filter #(and (:home-goals %) (:away-goals %)))
                     (sort-by :date (fn [a b]
                                     (if (and a b) (compare b a) (if a -1 1))))
                     (take limit))
        a-wins  (count (filter #(let [r (match-result %)]
                                  (or (and (= r :home-win) (data/team-matches? team-a (:home-team %)))
                                      (and (= r :away-win) (data/team-matches? team-a (:away-team %))))) matches))
        b-wins  (count (filter #(let [r (match-result %)]
                                  (or (and (= r :home-win) (data/team-matches? team-b (:home-team %)))
                                      (and (= r :away-win) (data/team-matches? team-b (:away-team %))))) matches))
        draws   (count (filter #(= :draw (match-result %)) matches))]
    {:total-found (count matches)
     :head-to-head {:team-a team-a :a-wins a-wins
                    :team-b team-b :b-wins b-wins
                    :draws draws}
     :matches (map format-match matches)}))

(defn find-matches-by-team
  "Find all matches for a single team."
  [{:keys [team competition season limit] :or {limit 50}}]
  (let [db      (data/db)
        matches (->> (:all-matches db)
                     (filter #(involves-team? team %))
                     (filter #(if competition
                                (str/includes? (str/lower-case (str (:competition %)))
                                               (str/lower-case competition))
                                true))
                     (filter #(if season (= (:season %) season) true))
                     (filter #(and (:home-goals %) (:away-goals %)))
                     (sort-by :date (fn [a b]
                                     (if (and a b) (compare b a) (if a -1 1))))
                     (take limit))]
    {:total-found (count matches)
     :matches (map format-match matches)}))

(defn find-matches-by-date-range
  "Find matches in date range (ISO strings)."
  [{:keys [from-date to-date competition limit] :or {limit 50}}]
  (let [db      (data/db)
        from    (when from-date (data/parse-date from-date))
        to      (when to-date (data/parse-date to-date))
        matches (->> (:all-matches db)
                     (filter #(let [d (:date %)]
                                (and d
                                     (or (nil? from) (not (.isBefore d from)))
                                     (or (nil? to) (not (.isAfter d to))))))
                     (filter #(if competition
                                (str/includes? (str/lower-case (str (:competition %)))
                                               (str/lower-case competition))
                                true))
                     (filter #(and (:home-goals %) (:away-goals %)))
                     (sort-by :date (fn [a b]
                                     (if (and a b) (compare a b) (if a -1 1))))
                     (take limit))]
    {:total-found (count matches)
     :matches (map format-match matches)}))

(defn find-matches-by-season
  "Find all matches for a given season."
  [{:keys [season competition limit] :or {limit 100}}]
  (let [db      (data/db)
        matches (->> (:all-matches db)
                     (filter #(= (:season %) season))
                     (filter #(if competition
                                (str/includes? (str/lower-case (str (:competition %)))
                                               (str/lower-case competition))
                                true))
                     (filter #(and (:home-goals %) (:away-goals %)))
                     (sort-by :date (fn [a b]
                                     (if (and a b) (compare a b) (if a -1 1))))
                     (take limit))]
    {:total-found (count matches)
     :season season
     :matches (map format-match matches)}))

;; ---------------------------------------------------------------------------
;; 2. Team queries
;; ---------------------------------------------------------------------------

(defn- team-record
  "Calculate W/D/L/GF/GA for a team from a seq of matches."
  [team matches]
  (reduce (fn [acc m]
            (let [home? (data/team-matches? team (:home-team m))
                  away? (data/team-matches? team (:away-team m))
                  hg    (:home-goals m)
                  ag    (:away-goals m)]
              (if (and (or home? away?) (number? hg) (number? ag))
                (let [gf    (if home? hg ag)
                      ga    (if home? ag hg)
                      res   (match-result m)
                      win?  (or (and home? (= res :home-win))
                                (and away? (= res :away-win)))
                      loss? (or (and home? (= res :away-win))
                                (and away? (= res :home-win)))
                      draw? (= res :draw)]
                  (-> acc
                      (update :matches inc)
                      (update :wins + (if win? 1 0))
                      (update :draws + (if draw? 1 0))
                      (update :losses + (if loss? 1 0))
                      (update :goals-for + gf)
                      (update :goals-against + ga)))
                acc)))
          {:matches 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0}
          matches))

(defn get-team-stats
  "Return win/draw/loss/goals stats for a team."
  [{:keys [team season competition]}]
  (let [db      (data/db)
        matches (->> (:all-matches db)
                     (filter #(involves-team? team %))
                     (filter #(if season (= (:season %) season) true))
                     (filter #(if competition
                                (str/includes? (str/lower-case (str (:competition %)))
                                               (str/lower-case competition))
                                true))
                     (filter #(and (:home-goals %) (:away-goals %))))
        home-m  (filter #(data/team-matches? team (:home-team %)) matches)
        away-m  (filter #(data/team-matches? team (:away-team %)) matches)
        overall (team-record team matches)
        home    (team-record team home-m)
        away    (team-record team away-m)
        pts     (+ (* 3 (:wins overall)) (:draws overall))
        win-pct (when (pos? (:matches overall))
                  (double (/ (* 100 (:wins overall)) (:matches overall))))]
    {:team team
     :season season
     :competition competition
     :overall (assoc overall :points pts :win-pct (when win-pct (format "%.1f%%" win-pct)))
     :home-record home
     :away-record away}))

(defn compare-teams-head-to-head
  "Detailed head-to-head comparison of two teams."
  [{:keys [team-a team-b season]}]
  (let [result (find-matches-by-teams {:team-a team-a :team-b team-b :limit 200})
        h2h    (:head-to-head result)]
    {:team-a team-a
     :team-b team-b
     :total-matches (:total-found result)
     :head-to-head h2h
     :matches (:matches result)}))

;; ---------------------------------------------------------------------------
;; 3. Player queries
;; ---------------------------------------------------------------------------

(defn find-players
  "Search FIFA player data.  At least one of name/nationality/club must be provided."
  [{:keys [name nationality club limit] :or {limit 30}}]
  (let [db      (data/db)
        players (->> (:fifa db)
                     (filter #(if name
                                (str/includes? (str/lower-case (str (:name %)))
                                               (str/lower-case name))
                                true))
                     (filter #(if nationality
                                (str/includes? (str/lower-case (str (:nationality %)))
                                               (str/lower-case nationality))
                                true))
                     (filter #(if club
                                (str/includes? (str/lower-case (str (:club %)))
                                               (str/lower-case club))
                                true))
                     (sort-by #(- (or (:overall %) 0)))
                     (take limit))]
    {:total-found (count players)
     :players (map (fn [p]
                     (str (:name p)
                          " | Overall: " (:overall p)
                          " | Pos: " (:position p)
                          " | Club: " (:club p)
                          " | Nationality: " (:nationality p)
                          " | Age: " (:age p)))
                   players)}))

(defn top-players-at-club
  "Return top-rated players at a given club."
  [{:keys [club limit] :or {limit 20}}]
  (find-players {:club club :limit limit}))

(defn find-brazilian-players
  "Find all Brazilian players, optionally filtered by club."
  [{:keys [club limit] :or {limit 50}}]
  (find-players {:nationality "Brazil" :club club :limit limit}))

;; ---------------------------------------------------------------------------
;; 4. Competition / standings queries
;; ---------------------------------------------------------------------------

(defn calculate-standings
  "Calculate league standings from match results for a season/competition."
  [{:keys [season competition] :or {competition "Brasileirao Serie A"}}]
  (let [db      (data/db)
        matches (->> (:all-matches db)
                     (filter #(if season (= (:season %) season) true))
                     (filter #(str/includes? (str/lower-case (str (:competition %)))
                                             (str/lower-case competition)))
                     (filter #(and (:home-goals %) (:away-goals %))))
        teams   (->> matches
                     (mapcat #(list (:home-team-norm %) (:away-team-norm %)))
                     (remove nil?)
                     distinct)
        records (for [t teams]
                  (let [r (team-record t matches)
                        pts (+ (* 3 (:wins r)) (:draws r))
                        gd  (- (:goals-for r) (:goals-against r))]
                    (assoc r :team t :points pts :goal-diff gd)))
        sorted  (sort-by (juxt (comp - :points) (comp - :goal-diff) (comp - :goals-for)) records)]
    {:season season
     :competition competition
     :standings (map-indexed
                 (fn [i r]
                   (str (inc i) ". " (:team r)
                        " - Pts: " (:points r)
                        " (" (:wins r) "W " (:draws r) "D " (:losses r) "L)"
                        " GF:" (:goals-for r) " GA:" (:goals-against r)
                        " GD:" (:goal-diff r)))
                 sorted)}))

(defn get-season-winner
  "Return the team with the most points in a season."
  [{:keys [season competition] :or {competition "Brasileirao Serie A"}}]
  (let [{:keys [standings]} (calculate-standings {:season season :competition competition})]
    {:season season
     :competition competition
     :winner (first standings)}))

;; ---------------------------------------------------------------------------
;; 5. Statistical analysis
;; ---------------------------------------------------------------------------

(defn goals-per-match-avg
  "Average goals per match, optionally filtered by competition/season."
  [{:keys [competition season]}]
  (let [db      (data/db)
        matches (->> (:all-matches db)
                     (filter #(if competition
                                (str/includes? (str/lower-case (str (:competition %)))
                                               (str/lower-case competition))
                                true))
                     (filter #(if season (= (:season %) season) true))
                     (filter #(and (:home-goals %) (:away-goals %))))
        total   (reduce (fn [acc m] (+ acc (:home-goals m) (:away-goals m))) 0 matches)
        n       (count matches)]
    {:competition competition
     :season season
     :total-matches n
     :total-goals total
     :avg-goals-per-match (when (pos? n) (format "%.2f" (double (/ total n))))}))

(defn biggest-wins
  "Return matches with the largest goal difference."
  [{:keys [competition season limit] :or {limit 10}}]
  (let [db      (data/db)
        matches (->> (:all-matches db)
                     (filter #(if competition
                                (str/includes? (str/lower-case (str (:competition %)))
                                               (str/lower-case competition))
                                true))
                     (filter #(if season (= (:season %) season) true))
                     (filter #(and (:home-goals %) (:away-goals %)))
                     (map #(assoc % :goal-diff (Math/abs (- (:home-goals %) (:away-goals %)))))
                     (sort-by (comp - :goal-diff))
                     (take limit))]
    {:matches (map format-match matches)}))

(defn home-vs-away-stats
  "Overall home win/draw/away win percentages."
  [{:keys [competition season]}]
  (let [db      (data/db)
        matches (->> (:all-matches db)
                     (filter #(if competition
                                (str/includes? (str/lower-case (str (:competition %)))
                                               (str/lower-case competition))
                                true))
                     (filter #(if season (= (:season %) season) true))
                     (filter #(and (:home-goals %) (:away-goals %))))
        n       (count matches)
        hw      (count (filter #(= :home-win (match-result %)) matches))
        aw      (count (filter #(= :away-win (match-result %)) matches))
        d       (count (filter #(= :draw (match-result %)) matches))
        pct     #(when (pos? n) (format "%.1f%%" (double (/ (* 100 %) n))))]
    {:total-matches n
     :home-wins hw :home-win-pct (pct hw)
     :away-wins aw :away-win-pct (pct aw)
     :draws d :draw-pct (pct d)}))

(defn best-home-records
  "Teams with the best home win percentages (min 5 home games)."
  [{:keys [competition season limit] :or {limit 10}}]
  (let [db      (data/db)
        matches (->> (:all-matches db)
                     (filter #(if competition
                                (str/includes? (str/lower-case (str (:competition %)))
                                               (str/lower-case competition))
                                true))
                     (filter #(if season (= (:season %) season) true))
                     (filter #(and (:home-goals %) (:away-goals %))))
        teams   (->> matches (map :home-team-norm) (remove nil?) distinct)
        records (for [t teams
                      :let [home-m (filter #(= t (:home-team-norm %)) matches)
                            n      (count home-m)
                            wins   (count (filter #(= :home-win (match-result %)) home-m))]
                      :when (>= n 5)]
                  {:team t :home-games n :home-wins wins
                   :win-pct (double (/ wins n))})
        sorted  (sort-by (comp - :win-pct) records)]
    {:teams (map #(str (:team %) " - " (:home-wins %) "/" (:home-games %)
                       " (" (format "%.1f%%" (* 100 (:win-pct %))) ")") (take limit sorted))}))

(defn top-scoring-teams
  "Teams ranked by total goals scored."
  [{:keys [competition season limit] :or {limit 10}}]
  (let [db      (data/db)
        matches (->> (:all-matches db)
                     (filter #(if competition
                                (str/includes? (str/lower-case (str (:competition %)))
                                               (str/lower-case competition))
                                true))
                     (filter #(if season (= (:season %) season) true))
                     (filter #(and (:home-goals %) (:away-goals %))))
        teams   (->> matches (mapcat #(list (:home-team-norm %) (:away-team-norm %))) (remove nil?) distinct)
        goals   (for [t teams
                      :let [hg (reduce + 0 (->> (filter #(= t (:home-team-norm %)) matches)
                                                (map #(or (:home-goals %) 0))))
                            ag (reduce + 0 (->> (filter #(= t (:away-team-norm %)) matches)
                                                (map #(or (:away-goals %) 0))))
                            total (+ hg ag)]]
                  {:team t :goals total})
        sorted  (sort-by (comp - :goals) goals)]
    {:teams (map #(str (:team %) " - " (:goals %) " goals") (take limit sorted))}))
