(ns brazilian-soccer.queries
  "=============================================================================
   queries.clj — Query / analytics layer over the knowledge graph
   -----------------------------------------------------------------------------
   Context:
     Implements the capabilities required by the specification:
       1. Match queries       — by team, date range, competition, season
       2. Team queries        — W/D/L records, goals, home/away splits
       3. Player queries      — name / nationality / club / position search
       4. Competition queries — league standings calculated from results
       5. Statistical analysis— head-to-head, averages, biggest wins

     All functions are pure: they take the data (or default to the loaded db)
     plus an options map, and return plain Clojure data. The MCP / formatting
     layers turn that data into text.
   ============================================================================="
  (:require [clojure.string :as str]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.normalize :as norm]))

;; ---------------------------------------------------------------------------
;; Match queries
;; ---------------------------------------------------------------------------

(defn- team-in-match?
  "Does `team` (normalized substring) appear on the given side of a match?
   side ∈ #{:home :away :either}"
  [team side m]
  (let [home? (norm/matches? team (:home-team m))
        away? (norm/matches? team (:away-team m))]
    (case side
      :home  home?
      :away  away?
      (or home? away?))))

(defn search-matches
  "Find matches by criteria. Options (all optional):
     :team        team name, matched on either side
     :side        :home | :away | :either (default :either, applies to :team)
     :opponent    second team name (for head-to-head listings)
     :competition competition name substring (e.g. \"Libertadores\")
     :season      integer season/year
     :date-from   ISO date inclusive lower bound
     :date-to     ISO date inclusive upper bound
     :limit       max number of results (most recent first)
   Returns a seq of match records sorted by date descending."
  ([opts] (search-matches (data/matches) opts))
  ([matches {:keys [team side opponent competition season date-from date-to limit]
             :or   {side :either}}]
   (cond->> matches
     team        (filter #(team-in-match? team side %))
     opponent    (filter #(or (norm/matches? opponent (:home-team %))
                              (norm/matches? opponent (:away-team %))))
     competition (filter #(norm/matches? competition (:competition %)))
     season      (filter #(= season (:season %)))
     date-from   (filter #(and (:date %) (>= (compare (:date %) date-from) 0)))
     date-to     (filter #(and (:date %) (<= (compare (:date %) date-to) 0)))
     true        (sort-by :date #(compare %2 %1))
     limit       (take limit))))

;; ---------------------------------------------------------------------------
;; Team statistics
;; ---------------------------------------------------------------------------

(defn- result-for
  "From the perspective of `team` in match `m`, return the goal pair and
   outcome, or nil when the team is not in the match or scores are missing."
  [team m]
  (let [home? (norm/matches? team (:home-team m))
        away? (norm/matches? team (:away-team m))
        hg (:home-goal m) ag (:away-goal m)]
    (when (and (or home? away?) hg ag)
      (let [gf (if home? hg ag)
            ga (if home? ag hg)]
        {:side     (if home? :home :away)
         :goals-for gf
         :goals-against ga
         :outcome (cond (> gf ga) :win (< gf ga) :loss :else :draw)}))))

(defn team-stats
  "Aggregate W/D/L and goal record for a team.
   Options:
     :team        (required) team name
     :season      restrict to a season
     :competition restrict to a competition (substring)
     :venue       :home | :away | :all (default :all)
   Returns a stats map (zeros when no matches found)."
  ([opts] (team-stats (data/matches) opts))
  ([matches {:keys [team season competition venue] :or {venue :all}}]
   (let [ms (cond->> matches
              true        (filter #(team-in-match? team :either %))
              season      (filter #(= season (:season %)))
              competition (filter #(norm/matches? competition (:competition %))))
         results (keep #(result-for team %) ms)
         results (case venue
                   :home (filter #(= :home (:side %)) results)
                   :away (filter #(= :away (:side %)) results)
                   results)
         tally   (frequencies (map :outcome results))
         w (get tally :win 0) d (get tally :draw 0) l (get tally :loss 0)
         gf (reduce + 0 (map :goals-for results))
         ga (reduce + 0 (map :goals-against results))
         played (+ w d l)]
     {:team team :season season :competition competition :venue venue
      :played played :wins w :draws d :losses l
      :goals-for gf :goals-against ga :goal-diff (- gf ga)
      :points (+ (* 3 w) d)
      :win-rate (if (pos? played) (double (/ w played)) 0.0)})))

(defn head-to-head
  "Head-to-head record between two teams across all (or filtered) matches.
   Options: :team1 :team2 (required), optional :competition :season."
  ([opts] (head-to-head (data/matches) opts))
  ([matches {:keys [team1 team2 competition season]}]
   (let [ms (search-matches matches {:team team1 :opponent team2
                                     :competition competition :season season})
         tallies (reduce
                  (fn [acc m]
                    (let [r (result-for team1 m)]
                      (case (:outcome r)
                        :win  (update acc :team1-wins inc)
                        :loss (update acc :team2-wins inc)
                        :draw (update acc :draws inc)
                        acc)))
                  {:team1-wins 0 :team2-wins 0 :draws 0}
                  ms)]
     (assoc tallies
            :team1 team1 :team2 team2
            :matches (vec ms)
            :total (count ms)))))

;; ---------------------------------------------------------------------------
;; Competition standings (calculated from results)
;; ---------------------------------------------------------------------------

(defn standings
  "Compute a league table for a competition+season from match results.
   Options: :competition (default \"Brasileirão\"), :season (required).
   Returns a seq of team rows sorted by points, then goal difference, then
   goals for, with a :rank assigned."
  ([opts] (standings (data/matches) opts))
  ([matches {:keys [competition season] :or {competition "Brasileirão"}}]
   (let [ms (filter #(and (norm/matches? competition (:competition %))
                          (or (nil? season) (= season (:season %)))
                          (:home-goal %) (:away-goal %))
                    matches)
         init {:played 0 :wins 0 :draws 0 :losses 0 :gf 0 :ga 0 :points 0}
         add  (fn [row gf ga outcome]
                (-> row
                    (update :played inc)
                    (update :gf + gf)
                    (update :ga + ga)
                    (update (case outcome :win :wins :loss :losses :draws) inc)
                    (update :points + (case outcome :win 3 :draw 1 0))))
         table (reduce
                (fn [acc m]
                  (let [{:keys [home-goal away-goal]} m
                        ;; group on the raw (suffix-preserving) name so distinct
                        ;; clubs sharing a base name are not merged; fall back to
                        ;; the display name when no raw is present (synthetic data)
                        home (or (:home-raw m) (:home-team m))
                        away (or (:away-raw m) (:away-team m))
                        ho (cond (> home-goal away-goal) :win
                                 (< home-goal away-goal) :loss :else :draw)
                        ao (cond (> away-goal home-goal) :win
                                 (< away-goal home-goal) :loss :else :draw)]
                    (-> acc
                        (update home #(add (or % (assoc init :team home))
                                           home-goal away-goal ho))
                        (update away #(add (or % (assoc init :team away))
                                           away-goal home-goal ao)))))
                {}
                ms)]
     (->> (vals table)
          (map #(assoc % :goal-diff (- (:gf %) (:ga %))))
          (sort-by (juxt :points :goal-diff :gf) #(compare %2 %1))
          (map-indexed (fn [i row] (assoc row :rank (inc i))))))))

;; ---------------------------------------------------------------------------
;; Statistical analysis
;; ---------------------------------------------------------------------------

(defn competition-stats
  "Aggregate statistics for a competition (and optional season):
     :matches, :total-goals, :avg-goals (per match),
     :home-wins/:away-wins/:draws and :home-win-rate."
  ([opts] (competition-stats (data/matches) opts))
  ([matches {:keys [competition season]}]
   (let [ms (filter #(and (or (nil? competition)
                              (norm/matches? competition (:competition %)))
                          (or (nil? season) (= season (:season %)))
                          (:home-goal %) (:away-goal %))
                    matches)
         n  (count ms)
         total (reduce + 0 (map #(+ (:home-goal %) (:away-goal %)) ms))
         tally (frequencies (map :winner ms))]
     {:competition competition :season season
      :matches n
      :total-goals total
      :avg-goals (if (pos? n) (double (/ total n)) 0.0)
      :home-wins (get tally :home 0)
      :away-wins (get tally :away 0)
      :draws     (get tally :draw 0)
      :home-win-rate (if (pos? n) (double (/ (get tally :home 0) n)) 0.0)})))

(defn biggest-wins
  "Return the matches with the largest goal margin, most lopsided first.
   Options: optional :competition, :season, :limit (default 10)."
  ([opts] (biggest-wins (data/matches) opts))
  ([matches {:keys [competition season limit] :or {limit 10}}]
   (->> matches
        (filter #(and (:home-goal %) (:away-goal %)
                      (or (nil? competition)
                          (norm/matches? competition (:competition %)))
                      (or (nil? season) (= season (:season %)))))
        (map #(assoc % :margin (Math/abs (- (:home-goal %) (:away-goal %)))))
        (sort-by (juxt :margin #(+ (:home-goal %) (:away-goal %)))
                 #(compare %2 %1))
        (take limit))))

(defn top-scoring-teams
  "Teams ordered by total goals scored in a competition/season.
   Options: optional :competition, :season, :limit (default 10)."
  [{:keys [competition limit] :or {limit 10} :as opts}]
  (->> (standings (data/matches) (assoc opts :competition (or competition "Brasileirão")))
       (sort-by :gf >)
       (take limit)))

;; ---------------------------------------------------------------------------
;; Player queries
;; ---------------------------------------------------------------------------

(defn search-players
  "Search the FIFA player database. Options (all optional):
     :name        substring (accent-insensitive) on player name
     :nationality substring on nationality (e.g. \"Brazil\")
     :club        substring on club (e.g. \"Flamengo\")
     :position    exact-ish substring on position (e.g. \"GK\", \"ST\")
     :min-overall minimum overall rating
     :limit       max results (default 25)
   Results are sorted by overall rating descending."
  ([opts] (search-players (data/players) opts))
  ([players {:keys [name nationality club position min-overall limit]
             :or   {limit 25}}]
   (cond->> players
     name        (filter #(norm/matches? name (:name %)))
     nationality (filter #(norm/matches? nationality (:nationality %)))
     club        (filter #(norm/matches? club (:club %)))
     position    (filter #(and (:position %)
                              (= (str/lower-case (str position))
                                 (str/lower-case (str (:position %))))))
     min-overall (filter #(and (:overall %) (>= (:overall %) min-overall)))
     true        (sort-by :overall #(compare %2 %1))
     limit       (take limit))))

(defn players-by-club-summary
  "Group Brazilian (or filtered nationality) players by club with counts and
   average rating. Useful for \"Brazilian players at Brazilian clubs\"."
  ([opts] (players-by-club-summary (data/players) opts))
  ([players {:keys [nationality limit] :or {limit 25}}]
   (->> players
        (filter #(or (nil? nationality) (norm/matches? nationality (:nationality %))))
        (filter :club)
        (group-by :club)
        (map (fn [[club ps]]
               (let [ovr (keep :overall ps)]
                 {:club club
                  :count (count ps)
                  :avg-overall (if (seq ovr)
                                 (double (/ (reduce + ovr) (count ovr)))
                                 0.0)})))
        (sort-by :count #(compare %2 %1))
        (take limit))))
