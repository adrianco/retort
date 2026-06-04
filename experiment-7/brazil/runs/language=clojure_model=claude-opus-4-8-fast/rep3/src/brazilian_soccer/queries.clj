;; =============================================================================
;; brazilian-soccer.queries
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   The analytical core. Pure functions that take the knowledge graph plus a
;;   parameter map and return plain Clojure data (maps/vectors). They contain NO
;;   formatting and NO I/O so they are trivially unit-testable; the MCP server
;;   (mcp_server.clj) and the formatter (format.clj) sit on top of them.
;;
;;   Capability coverage (see TASK.md "Required Capabilities"):
;;     1. Match queries       -> find-matches, head-to-head
;;     2. Team queries        -> team-stats, head-to-head
;;     3. Player queries      -> find-players, top-players
;;     4. Competition queries -> standings, league-stats
;;     5. Statistical analysis-> league-stats, biggest-wins, head-to-head
;;
;; TEAM MATCHING
;;   A user-supplied team string matches a match's side when their
;;   normalize/team-key are equal, OR when the normalised query is a substring of
;;   the normalised side name (so "Atletico" finds every Atlético, "Flamengo"
;;   finds "Flamengo-RJ"). See `team-matches?`.
;; =============================================================================
(ns brazilian-soccer.queries
  (:require [brazilian-soccer.normalize :as n]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; Matching predicates
;; ---------------------------------------------------------------------------

(defn team-matches?
  "Does `side-key`/`side-name` correspond to the user query `q`?"
  [q side-key side-name]
  (when (and q side-key)
    (let [qk (n/team-key q)
          qn (n/norm-text q)]
      (or (= qk side-key)
          (and qn (str/includes? (or (n/norm-text side-name) "") qn))))))

(defn- match-side
  "Returns :home, :away or nil for which side of match `m` the team `q` is on."
  [m q]
  (cond
    (team-matches? q (:home-key m) (:home m)) :home
    (team-matches? q (:away-key m) (:away m)) :away
    :else nil))

(defn- result-for
  "Outcome (:win/:loss/:draw) and goals for/against for `side` of match `m`.
   nil when scores are unknown."
  [m side]
  (let [hg (:home-goals m) ag (:away-goals m)]
    (when (and hg ag)
      (let [[gf ga] (if (= side :home) [hg ag] [ag hg])]
        {:gf gf :ga ga
         :outcome (cond (> gf ga) :win (< gf ga) :loss :else :draw)}))))

;; ---------------------------------------------------------------------------
;; 1. Match queries
;; ---------------------------------------------------------------------------

(defn find-matches
  "Search matches. Params (all optional):
     :team        - matches where this team is home OR away
     :opponent    - restrict to matches against this team
     :home        - require :team to be the home side (true)
     :away        - require :team to be the away side (true)
     :competition - substring match on competition name
     :season      - exact season (int or string)
     :date-from / :date-to - ISO date bounds (inclusive)
     :limit       - cap results (default 50)
   Results are sorted by date descending (unknown dates last)."
  [graph {:keys [team opponent home away competition season date-from date-to limit]}]
  (let [season (when season (n/->int (str season)))
        comp-q (some-> competition n/norm-text)
        candidates (if team
                     (get-in graph [:by-team (n/team-key team)]
                             (filter #(match-side % team) (:matches graph)))
                     (:matches graph))]
    (->> candidates
         (filter (fn [m]
                   (let [side (when team (match-side m team))]
                     (and (or (not team) side)
                          (or (not home) (= side :home))
                          (or (not away) (= side :away))
                          (or (not opponent)
                              (if team
                                (let [other-key  (if (= side :home) (:away-key m) (:home-key m))
                                      other-name (if (= side :home) (:away m) (:home m))]
                                  (team-matches? opponent other-key other-name))
                                (or (team-matches? opponent (:home-key m) (:home m))
                                    (team-matches? opponent (:away-key m) (:away m)))))
                          (or (not comp-q)
                              (str/includes? (n/norm-text (:competition m)) comp-q))
                          (or (not season) (= season (:season m)))
                          (or (not date-from) (and (:date m) (>= (compare (:date m) date-from) 0)))
                          (or (not date-to) (and (:date m) (<= (compare (:date m) date-to) 0)))))))
         (sort-by :date #(compare %2 %1))
         (take (or limit 50))
         vec)))

(defn head-to-head
  "Aggregate the rivalry between `team-a` and `team-b`:
     {:team-a :team-b :total :a-wins :b-wins :draws
      :a-goals :b-goals :matches [...]}"
  [graph team-a team-b]
  (let [ms (find-matches graph {:team team-a :opponent team-b :limit Integer/MAX_VALUE})]
    (reduce
     (fn [acc m]
       (let [side (match-side m team-a)
             r (result-for m side)]
         (cond-> (-> acc
                     (update :total inc)
                     (update :matches conj m))
           r (-> (update :a-goals + (:gf r))
                 (update :b-goals + (:ga r))
                 (update (case (:outcome r) :win :a-wins :loss :b-wins :draw :draws) inc)))))
     {:team-a (n/display-name team-a) :team-b (n/display-name team-b)
      :total 0 :a-wins 0 :b-wins 0 :draws 0 :a-goals 0 :b-goals 0 :matches []}
     ms)))

;; ---------------------------------------------------------------------------
;; 2. Team queries
;; ---------------------------------------------------------------------------

(defn team-stats
  "Win/loss/draw record and goals for a team. Params:
     :team (required) :season :competition :home (true) :away (true)
   Returns nil if the team is unknown / no matches."
  [graph {:keys [team] :as params}]
  (let [ms (find-matches graph (assoc params :limit Integer/MAX_VALUE))]
    (when (seq ms)
      (reduce
       (fn [acc m]
         (let [side (match-side m team)
               r (result-for m side)]
           (cond-> (update acc :matches inc)
             r (-> (update (case (:outcome r) :win :wins :loss :losses :draw :draws) inc)
                   (update :goals-for + (:gf r))
                   (update :goals-against + (:ga r))))))
       {:team (or (:name (get-in graph [:teams (n/team-key team)]))
                  (n/display-name team))
        :season (:season params) :competition (:competition params)
        :matches 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0}
       ms))))

;; ---------------------------------------------------------------------------
;; 3. Player queries
;; ---------------------------------------------------------------------------

(defn find-players
  "Search FIFA players. Params (all optional):
     :name        - substring match on player name
     :nationality - substring match on nationality (e.g. \"Brazil\")
     :club        - substring match on club
     :position    - exact-ish match on position code (e.g. \"GK\", \"LW\")
     :min-overall - minimum overall rating
     :limit       - cap (default 25)
   Sorted by overall rating descending."
  [graph {:keys [name nationality club position min-overall limit]}]
  (let [nm (some-> name n/norm-text)
        nat (some-> nationality n/norm-text)
        cl (some-> club n/norm-text)
        pos (some-> position n/norm-text)
        min-ov (n/->int (str (or min-overall "")))]
    (->> (:players graph)
         (filter (fn [p]
                   (and (or (not nm)  (and (:name-key p) (str/includes? (:name-key p) nm)))
                        (or (not nat) (and (:nationality-key p) (str/includes? (:nationality-key p) nat)))
                        (or (not cl)  (and (:club-key p) (str/includes? (:club-key p) cl)))
                        (or (not pos) (and (:position p) (= pos (n/norm-text (:position p)))))
                        (or (not min-ov) (and (:overall p) (>= (:overall p) min-ov))))))
         (sort-by :overall #(compare %2 %1))
         (take (or limit 25))
         vec)))

(defn top-players
  "Highest-rated players, optionally filtered by nationality/club."
  [graph params]
  (find-players graph (merge {:limit 10} params)))

;; ---------------------------------------------------------------------------
;; 4. Competition queries
;; ---------------------------------------------------------------------------

(defn- primary-source-matches
  "For a league competition+season, pick a single source to avoid double
   counting across overlapping datasets. Priority: brasileirao > novo >
   br-football. Falls back to all matches if those sources are absent."
  [graph competition season]
  (let [comp-q (n/norm-text competition)
        season (n/->int (str season))
        in-comp (->> (:matches graph)
                     (filter #(and (str/includes? (n/norm-text (:competition %)) comp-q)
                                   (= season (:season %)))))]
    (some (fn [src]
            (let [sub (filter #(contains? (:sources %) src) in-comp)]
              (when (seq sub) sub)))
          [:brasileirao :novo :br-football :cup :libertadores])))

(defn standings
  "League table for a competition+season, computed from match results.
   Returns a vector of rows sorted by points (then goal diff, then goals for):
     {:rank :team :played :wins :draws :losses :gf :ga :gd :points}"
  [graph competition season]
  (let [ms (primary-source-matches graph competition season)]
    (when (seq ms)
      (let [tally
            (reduce
             (fn [acc m]
               (let [hg (:home-goals m) ag (:away-goals m)]
                 (if (and hg ag)
                   (let [bump (fn [acc team-key team-name gf ga]
                                (let [out (cond (> gf ga) :wins (< gf ga) :losses :else :draws)]
                                  (-> acc
                                      (update-in [team-key :team] #(or % team-name))
                                      (update-in [team-key :played] (fnil inc 0))
                                      (update-in [team-key out] (fnil inc 0))
                                      (update-in [team-key :gf] (fnil + 0) gf)
                                      (update-in [team-key :ga] (fnil + 0) ga))))]
                     (-> acc
                         (bump (:home-key m) (:home m) hg ag)
                         (bump (:away-key m) (:away m) ag hg)))
                   acc)))
             {}
             ms)]
        (->> (vals tally)
             (map (fn [r]
                    (let [r (merge {:wins 0 :draws 0 :losses 0 :gf 0 :ga 0 :played 0} r)]
                      (assoc r
                             :gd (- (:gf r) (:ga r))
                             :points (+ (* 3 (:wins r)) (:draws r))))))
             (sort-by (juxt :points :gd :gf) #(compare %2 %1))
             (map-indexed (fn [i r] (assoc r :rank (inc i))))
             vec)))))

;; ---------------------------------------------------------------------------
;; 5. Statistical analysis
;; ---------------------------------------------------------------------------

(defn league-stats
  "Aggregate statistics over a set of matches. Params:
     :competition (substring) :season
   Returns {:matches :scored-matches :total-goals :avg-goals
            :home-wins :away-wins :draws :home-win-rate :away-win-rate :draw-rate}."
  [graph {:keys [competition season]}]
  (let [comp-q (some-> competition n/norm-text)
        season (when season (n/->int (str season)))
        ms (->> (:matches graph)
                (filter (fn [m]
                          (and (or (not comp-q) (str/includes? (n/norm-text (:competition m)) comp-q))
                               (or (not season) (= season (:season m)))))))
        scored (filter #(and (:home-goals %) (:away-goals %)) ms)
        n-scored (count scored)
        total-goals (reduce + 0 (map #(+ (:home-goals %) (:away-goals %)) scored))
        hw (count (filter #(> (:home-goals %) (:away-goals %)) scored))
        aw (count (filter #(< (:home-goals %) (:away-goals %)) scored))
        dr (- n-scored hw aw)
        rate (fn [x] (if (pos? n-scored) (double (/ x n-scored)) 0.0))]
    {:matches (count ms)
     :scored-matches n-scored
     :total-goals total-goals
     :avg-goals (if (pos? n-scored) (double (/ total-goals n-scored)) 0.0)
     :home-wins hw :away-wins aw :draws dr
     :home-win-rate (rate hw) :away-win-rate (rate aw) :draw-rate (rate dr)}))

(defn biggest-wins
  "Matches with the largest goal margin. Params:
     :competition (substring) :season :team (optional) :limit (default 10)."
  [graph {:keys [competition season team limit]}]
  (let [comp-q (some-> competition n/norm-text)
        season (when season (n/->int (str season)))]
    (->> (:matches graph)
         (filter (fn [m]
                   (and (:home-goals m) (:away-goals m)
                        (or (not comp-q) (str/includes? (n/norm-text (:competition m)) comp-q))
                        (or (not season) (= season (:season m)))
                        (or (not team) (match-side m team)))))
         (map #(assoc % :margin (abs (- (:home-goals %) (:away-goals %)))))
         (sort-by (juxt :margin #(+ (:home-goals %) (:away-goals %))) #(compare %2 %1))
         (take (or limit 10))
         vec)))

(defn list-competitions
  "All competitions known to the graph with their season coverage."
  [graph]
  (->> (:competitions graph)
       (map (fn [[name info]]
              {:competition name
               :seasons (sort (remove nil? (:seasons info)))
               :teams (count (:teams info))
               :matches (:match-count info)}))
       (sort-by :competition)
       vec))
