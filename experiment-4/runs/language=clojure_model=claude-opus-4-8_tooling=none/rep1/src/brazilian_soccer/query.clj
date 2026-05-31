(ns brazilian-soccer.query
  "=============================================================================
   Brazilian Soccer MCP Server - Query Engine
   =============================================================================

   CONTEXT
     Pure query functions over the in-memory knowledge graph produced by
     brazilian-soccer.data/load-database. Every function takes the db map as
     its first argument and returns plain Clojure data (no formatting / IO),
     which keeps them trivially testable and reusable by the MCP layer.

     These functions implement the five capability areas from the spec:
       1. Match queries        - search-matches, last-match
       2. Team queries         - team-stats, head-to-head, compare-teams
       3. Player queries       - search-players, top-players, club-roster
       4. Competition queries  - standings, season-list
       5. Statistical analysis - competition-stats, biggest-wins, best-record

   TEAM MATCHING
     Team arguments are matched on canonical keys (accent/suffix-insensitive)
     using substring containment, so \"flamengo\" matches \"Flamengo\" and a
     query for \"sao paulo\" matches \"São Paulo\".

   PUBLIC API  (see individual docstrings)
     resolve-team    search-matches   last-match      team-stats
     head-to-head    compare-teams    search-players  top-players
     club-roster     standings        competition-stats
     biggest-wins    best-record      list-competitions  list-seasons
   ============================================================================="
  (:require [clojure.string :as str]
            [brazilian-soccer.normalize :as norm]))

;; ----------------------------------------------------------------------------
;; Team resolution & match outcome helpers
;; ----------------------------------------------------------------------------

(defn- key-matches?
  "True when query key q is contained in (or equals) team key k.
   Substring containment lets short queries (\"santos\") match cleaned names
   while still being accent/suffix-insensitive via canonical keys."
  [q k]
  (and (seq q) (seq k)
       (or (= q k) (str/includes? k q))))

(defn resolve-team
  "Return the best-matching Team node for a free-text name, or nil.
   Prefers an exact canonical-key match, else the shortest-name substring
   match (the shortest name is usually the 'plain' club name)."
  [db name]
  (let [q (norm/canonical-key name)
        teams (vals (:teams db))]
    (or (first (filter #(= q (:key %)) teams))
        (->> teams
             (filter #(key-matches? q (:key %)))
             (sort-by (comp count :name))
             first))))

(defn- outcome
  "Outcome of a match from the perspective of the team with key team-key:
   :win :loss :draw, or nil when goals are missing."
  [match team-key]
  (let [{:keys [home-key away-key home-goal away-goal]} match]
    (when (and home-goal away-goal)
      (let [home? (key-matches? team-key home-key)
            gf (if home? home-goal away-goal)
            ga (if home? away-goal home-goal)]
        (cond (> gf ga) :win (< gf ga) :loss :else :draw)))))

;; ----------------------------------------------------------------------------
;; Match queries
;; ----------------------------------------------------------------------------

(defn- involves?
  "Does match involve the given canonical key on the given side?
   side ∈ #{:home :away :either}."
  [match q side]
  (case side
    :home   (key-matches? q (:home-key match))
    :away   (key-matches? q (:away-key match))
    (or (key-matches? q (:home-key match))
        (key-matches? q (:away-key match)))))

(defn search-matches
  "Find matches by any combination of criteria. Options map:
     :team        team name (matched on :side, default :either)
     :side        :home | :away | :either
     :opponent    second team name (both teams must be present)
     :competition substring of competition label (accent-insensitive)
     :season      integer year
     :date-from   ISO \"YYYY-MM-DD\" inclusive lower bound
     :date-to     ISO \"YYYY-MM-DD\" inclusive upper bound
     :limit       max results (default 50)
   Results are sorted by date descending (most recent first)."
  [db {:keys [team side opponent competition season date-from date-to limit]
       :or {side :either limit 50}}]
  (let [tq  (when team (norm/canonical-key team))
        oq  (when opponent (norm/canonical-key opponent))
        cq  (when competition (norm/normalize-text competition))]
    (->> (:matches db)
         (filter
          (fn [m]
            (and (or (nil? tq) (involves? m tq side))
                 (or (nil? oq) (involves? m oq :either))
                 (or (nil? cq) (str/includes? (norm/normalize-text (:competition m)) cq))
                 (or (nil? season) (= season (:season m)))
                 (or (nil? date-from) (and (:date m) (>= (compare (:date m) date-from) 0)))
                 (or (nil? date-to)   (and (:date m) (<= (compare (:date m) date-to) 0))))))
         (sort-by :date #(compare %2 %1))
         (take limit)
         vec)))

(defn last-match
  "Most recent match between two teams (or nil)."
  [db team1 team2]
  (first (search-matches db {:team team1 :opponent team2 :limit 1})))

;; ----------------------------------------------------------------------------
;; Team queries / statistics
;; ----------------------------------------------------------------------------

(defn- tally
  "Aggregate W/D/L, goals-for/against over a seq of matches for team-key."
  [matches team-key]
  (reduce
   (fn [acc m]
     (let [{:keys [home-key home-goal away-goal]} m]
       (if (and home-goal away-goal)
         (let [home? (key-matches? team-key home-key)
               gf (if home? home-goal away-goal)
               ga (if home? away-goal home-goal)
               res (outcome m team-key)]
           (-> acc
               (update :matches inc)
               (update :goals-for + gf)
               (update :goals-against + ga)
               (update res inc)))
         acc)))
   {:matches 0 :win 0 :draw 0 :loss 0 :goals-for 0 :goals-against 0}
   matches))

(defn- win-rate [{:keys [matches win]}]
  (if (pos? matches) (* 100.0 (/ win matches)) 0.0))

(defn team-stats
  "Compute W/D/L, goals and win-rate for a team. Options:
     :season       integer year filter
     :competition  competition substring filter
     :venue        :home | :away | :all   (default :all)
   Returns nil if the team cannot be resolved."
  [db team {:keys [season competition venue] :or {venue :all}}]
  (when-let [t (resolve-team db team)]
    (let [side (case venue :home :home :away :away :either)
          matches (search-matches db (cond-> {:team (:name t) :side side :limit Long/MAX_VALUE}
                                       season (assoc :season season)
                                       competition (assoc :competition competition)))
          base (tally matches (:key t))]
      (assoc base
             :team (:name t)
             :venue venue
             :season season
             :competition competition
             :win-rate (win-rate base)
             :goal-difference (- (:goals-for base) (:goals-against base))))))

(defn head-to-head
  "Head-to-head summary between two teams across all competitions.
   Returns {:team1 :team2 :total :team1-wins :team2-wins :draws :matches [...]}."
  [db team1 team2]
  (let [t1 (resolve-team db team1)
        t2 (resolve-team db team2)]
    (when (and t1 t2)
      (let [ms (search-matches db {:team (:name t1) :opponent (:name t2)
                                   :limit Long/MAX_VALUE})
            counts (reduce (fn [acc m]
                             (case (outcome m (:key t1))
                               :win  (update acc :team1-wins inc)
                               :loss (update acc :team2-wins inc)
                               :draw (update acc :draws inc)
                               acc))
                           {:team1-wins 0 :team2-wins 0 :draws 0}
                           ms)]
        (assoc counts
               :team1 (:name t1)
               :team2 (:name t2)
               :total (count ms)
               :matches ms)))))

(defn compare-teams
  "Side-by-side team-stats for two teams plus their head-to-head.
   Options are passed through to team-stats (e.g. :season)."
  [db team1 team2 opts]
  {:team1 (team-stats db team1 opts)
   :team2 (team-stats db team2 opts)
   :head-to-head (head-to-head db team1 team2)})

;; ----------------------------------------------------------------------------
;; Player queries
;; ----------------------------------------------------------------------------

(defn resolve-club-keys
  "Determine which player-club keys a club query should match.
   Uses exact-match-first semantics: if any club key equals the query exactly
   we return only those, otherwise we fall back to substring containment. This
   stops a query for \"Santos\" (Santos FC, key \"santos\") from also dragging in
   \"Santos Laguna\" (a different club, key \"santos laguna\")."
  [db club]
  (let [cq (norm/canonical-key club)
        keys (into #{} (keep :club-key (:players db)))
        exact (filter #(= % cq) keys)]
    (set (if (seq exact) exact (filter #(key-matches? cq %) keys)))))

(defn search-players
  "Search FIFA player records. Options:
     :name         substring of player name (accent-insensitive)
     :nationality  substring of nationality
     :club         club name (exact-match-first, see resolve-club-keys)
     :position     exact-ish position match (e.g. \"ST\", \"GK\")
     :min-overall  minimum FIFA overall rating
     :limit        max results (default 25)
   Results sorted by overall rating descending."
  [db {:keys [name nationality club position min-overall limit]
       :or {limit 25}}]
  (let [nq  (when name (norm/normalize-text name))
        natq (when nationality (norm/normalize-text nationality))
        club-keys (when club (resolve-club-keys db club))
        pq  (when position (norm/normalize-text position))]
    (->> (:players db)
         (filter
          (fn [p]
            (and (or (nil? nq)   (str/includes? (:name-key p) nq))
                 (or (nil? natq) (str/includes? (:nat-key p) natq))
                 (or (nil? club-keys) (contains? club-keys (:club-key p)))
                 (or (nil? pq)   (= pq (norm/normalize-text (:position p))))
                 (or (nil? min-overall) (and (:overall p) (>= (:overall p) min-overall))))))
         (sort-by :overall #(compare %2 %1))
         (take limit)
         vec)))

(defn top-players
  "Highest-rated players, optionally filtered by nationality (e.g. \"Brazil\")."
  [db {:keys [nationality limit] :or {limit 10}}]
  (search-players db {:nationality nationality :limit limit}))

(defn club-roster
  "All players whose club matches the given name, sorted by overall desc,
   plus the average overall rating. Returns {:club :count :avg-overall :players}."
  [db club]
  (let [players (search-players db {:club club :limit Long/MAX_VALUE})
        overalls (keep :overall players)]
    {:club club
     :count (count players)
     :avg-overall (when (seq overalls)
                    (/ (double (reduce + overalls)) (count overalls)))
     :players players}))

;; ----------------------------------------------------------------------------
;; Competition queries
;; ----------------------------------------------------------------------------

(defn list-competitions
  "Distinct competition labels present in the data, sorted."
  [db]
  (->> (:matches db) (map :competition) distinct sort vec))

(defn list-seasons
  "Distinct seasons for a competition substring (or all competitions), sorted."
  ([db] (list-seasons db nil))
  ([db competition]
   (let [cq (when competition (norm/normalize-text competition))]
     (->> (:matches db)
          (filter #(or (nil? cq) (str/includes? (norm/normalize-text (:competition %)) cq)))
          (keep :season)
          distinct sort vec))))

(defn standings
  "League table for a competition + season, computed from match results.
   3 points for a win, 1 for a draw. Returns a vector of rows sorted by
   points, then goal-difference, then goals-for (all descending):
     {:rank :team :played :win :draw :loss :goals-for :goals-against
      :goal-difference :points}"
  [db {:keys [competition season]}]
  (let [matches (search-matches db (cond-> {:limit Long/MAX_VALUE}
                                     competition (assoc :competition competition)
                                     season (assoc :season season)))
        ;; collect every team key->display-name appearing in the filtered set
        teams (reduce (fn [acc m]
                        (-> acc
                            (assoc (:home-key m) (:home m))
                            (assoc (:away-key m) (:away m))))
                      {} matches)
        rows (->> teams
                  (map (fn [[k name]]
                         (let [t (tally (filter #(or (= k (:home-key %)) (= k (:away-key %))) matches) k)]
                           (assoc t
                                  :team name
                                  :played (:matches t)
                                  :goal-difference (- (:goals-for t) (:goals-against t))
                                  :points (+ (* 3 (:win t)) (:draw t))))))
                  (sort-by (juxt :points :goal-difference :goals-for)
                           #(compare %2 %1)))]
    (map-indexed (fn [i row] (assoc row :rank (inc i))) rows)))

(defn champion
  "The top of the standings for a competition+season (the calculated winner)."
  [db opts]
  (first (standings db opts)))

;; ----------------------------------------------------------------------------
;; Statistical analysis
;; ----------------------------------------------------------------------------

(defn competition-stats
  "Aggregate statistics for a set of matches (filtered by competition/season):
     {:matches N :total-goals G :avg-goals-per-match :home-wins :away-wins
      :draws :home-win-rate :biggest-win}."
  [db {:keys [competition season]}]
  (let [matches (->> (search-matches db (cond-> {:limit Long/MAX_VALUE}
                                          competition (assoc :competition competition)
                                          season (assoc :season season)))
                     (filter #(and (:home-goal %) (:away-goal %))))
        n (count matches)
        total-goals (reduce (fn [acc m] (+ acc (:home-goal m) (:away-goal m))) 0 matches)
        home-wins (count (filter #(> (:home-goal %) (:away-goal %)) matches))
        away-wins (count (filter #(< (:home-goal %) (:away-goal %)) matches))
        draws (- n home-wins away-wins)]
    {:competition competition
     :season season
     :matches n
     :total-goals total-goals
     :avg-goals-per-match (if (pos? n) (/ (double total-goals) n) 0.0)
     :home-wins home-wins
     :away-wins away-wins
     :draws draws
     :home-win-rate (if (pos? n) (* 100.0 (/ home-wins n)) 0.0)
     :away-win-rate (if (pos? n) (* 100.0 (/ away-wins n)) 0.0)
     :draw-rate (if (pos? n) (* 100.0 (/ draws n)) 0.0)}))

(defn biggest-wins
  "Matches with the largest goal margin, filtered by competition/season.
   Options also accept :limit (default 10)."
  [db {:keys [competition season limit] :or {limit 10}}]
  (->> (search-matches db (cond-> {:limit Long/MAX_VALUE}
                            competition (assoc :competition competition)
                            season (assoc :season season)))
       (filter #(and (:home-goal %) (:away-goal %)))
       (sort-by (fn [m] (Math/abs (- (:home-goal m) (:away-goal m)))) >)
       (take limit)
       vec))

(defn best-record
  "Rank teams by win-rate (min :min-matches games) within a competition/season.
   Options: :competition :season :venue (:home/:away/:all) :min-matches :limit."
  [db {:keys [competition season venue min-matches limit]
       :or {venue :all min-matches 5 limit 10}}]
  (let [matches (search-matches db (cond-> {:limit Long/MAX_VALUE}
                                     competition (assoc :competition competition)
                                     season (assoc :season season)))
        team-names (reduce (fn [acc m]
                             (-> acc (assoc (:home-key m) (:home m))
                                 (assoc (:away-key m) (:away m))))
                           {} matches)]
    (->> team-names
         (keep (fn [[_k name]]
                 (let [s (team-stats db name (cond-> {:venue venue}
                                               season (assoc :season season)
                                               competition (assoc :competition competition)))]
                   (when (and s (>= (:matches s) min-matches)) s))))
         ;; The same club can appear under suffixed/unsuffixed keys across
         ;; competitions (e.g. \"Flamengo\" vs \"Flamengo-RJ\"); team-stats
         ;; resolves both to one team, so collapse the duplicate rows.
         (distinct)
         (sort-by :win-rate >)
         (take limit)
         vec)))
