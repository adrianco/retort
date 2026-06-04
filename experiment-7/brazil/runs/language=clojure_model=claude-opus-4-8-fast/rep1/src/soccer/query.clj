;; =============================================================================
;; soccer.query — Query & analytics layer
;; -----------------------------------------------------------------------------
;; Project: brazilian-soccer-mcp
;;
;; Context:
;;   Pure functions over the in-memory database produced by soccer.data.
;;   Implements the five capability groups from the specification:
;;     1. Match queries        (search-matches)
;;     2. Team queries         (team-stats)
;;     3. Player queries       (search-players, players-by-club summaries)
;;     4. Competition queries  (standings)
;;     5. Statistical analysis (head-to-head, competition-stats, biggest-wins)
;;
;;   Every function takes the database map (or the relevant sub-collection) as
;;   its first argument so the layer is trivially testable and free of global
;;   state.  Team matching is accent/suffix-insensitive via soccer.normalize.
;; =============================================================================
(ns soccer.query
  (:require [clojure.string :as str]
            [soccer.normalize :as n]))

;; --- small helpers ----------------------------------------------------------

(defn- scored?
  "True when a match has both goal counts present."
  [m]
  (and (some? (:home-goals m)) (some? (:away-goals m))))

(defn- result-for
  "Outcome (:win/:draw/:loss), goals-for and goals-against for `team` in a
   scored match `m`.  Returns nil if the team did not play or the match is
   unscored."
  [team m]
  (when (scored? m)
    (let [home? (n/same-team? team (:home m))
          away? (n/same-team? team (:away m))]
      (when (or home? away?)
        (let [gf (if home? (:home-goals m) (:away-goals m))
              ga (if home? (:away-goals m) (:home-goals m))]
          {:venue   (if home? :home :away)
           :gf gf :ga ga
           :outcome (cond (> gf ga) :win (< gf ga) :loss :else :draw)})))))

(defn competitions
  "Distinct competition labels present in the database."
  [{:keys [matches]}]
  (sort (distinct (map :competition matches))))

(defn seasons
  "Distinct seasons present in the database (optionally for one competition)."
  ([db] (seasons db nil))
  ([{:keys [matches]} competition]
   (->> matches
        (filter #(or (nil? competition) (= competition (:competition %))))
        (keep :season) distinct sort)))

;; --- 1. Match queries -------------------------------------------------------

(defn search-matches
  "Find matches by any combination of criteria.

   opts:
     :team        team plays (home OR away)
     :opponent    used with :team -> matches between the two teams
     :home        team plays at home
     :away        team plays away
     :competition exact competition label (e.g. \"Copa do Brasil\")
     :season      integer year
     :date-from   inclusive lower bound (java.time.LocalDate or yyyy-MM-dd str)
     :date-to     inclusive upper bound
     :limit       cap the number of results (after sorting, newest first)

   Returns a seq of match records sorted by date descending (nil dates last)."
  [{:keys [matches]} {:keys [team opponent home away competition season
                             date-from date-to limit]}]
  (let [df (if (string? date-from) (n/parse-date date-from) date-from)
        dt (if (string? date-to)   (n/parse-date date-to)   date-to)
        pred
        (fn [m]
          (and (or (nil? competition) (= competition (:competition m)))
               (or (nil? season) (= season (:season m)))
               (or (nil? team)
                   (n/same-team? team (:home m))
                   (n/same-team? team (:away m)))
               (or (nil? opponent)
                   (n/same-team? opponent (:home m))
                   (n/same-team? opponent (:away m)))
               ;; when both team & opponent given, ensure they are the two sides
               (or (nil? opponent) (nil? team)
                   (and (or (n/same-team? team (:home m))
                            (n/same-team? team (:away m)))
                        (or (n/same-team? opponent (:home m))
                            (n/same-team? opponent (:away m)))
                        (not (n/same-team? team opponent))))
               (or (nil? home) (n/same-team? home (:home m)))
               (or (nil? away) (n/same-team? away (:away m)))
               (or (nil? df) (and (:date m) (not (.isBefore (:date m) df))))
               (or (nil? dt) (and (:date m) (not (.isAfter (:date m) dt))))))
        results (->> matches
                     (filter pred)
                     (sort-by :date
                              #(cond (and (nil? %1) (nil? %2)) 0
                                     (nil? %1) 1
                                     (nil? %2) -1
                                     :else (compare %2 %1))))]
    (if limit (take limit results) results)))

;; --- 2. Team queries --------------------------------------------------------

(defn team-stats
  "Win/draw/loss + goals record for `team`, optionally restricted by season,
   competition and venue (:home / :away / :all, default :all).

   Returns:
     {:team :season :competition :venue
      :matches :wins :draws :losses :goals-for :goals-against :goal-diff
      :points :win-rate}"
  [{:keys [matches]} team {:keys [season competition venue] :or {venue :all}}]
  (let [rs (->> matches
                (filter #(or (nil? season) (= season (:season %))))
                (filter #(or (nil? competition) (= competition (:competition %))))
                (keep #(result-for team %))
                (filter #(or (= venue :all) (= venue (:venue %)))))
        n*  (count rs)
        w   (count (filter #(= :win (:outcome %)) rs))
        d   (count (filter #(= :draw (:outcome %)) rs))
        l   (count (filter #(= :loss (:outcome %)) rs))
        gf  (reduce + 0 (map :gf rs))
        ga  (reduce + 0 (map :ga rs))]
    {:team          (n/canonical-name team)
     :season        season
     :competition   competition
     :venue         venue
     :matches       n*
     :wins          w
     :draws         d
     :losses        l
     :goals-for     gf
     :goals-against ga
     :goal-diff     (- gf ga)
     :points        (+ (* 3 w) d)
     :win-rate      (if (pos? n*) (double (/ w n*)) 0.0)}))

;; --- 5a. Head-to-head -------------------------------------------------------

(defn head-to-head
  "Aggregate record between `team-a` and `team-b` across all competitions
   (optionally filtered by competition/season).

   Returns:
     {:team-a :team-b :matches
      :a-wins :b-wins :draws
      :a-goals :b-goals :match-list}"
  [db team-a team-b & [{:keys [competition season]}]]
  (let [ms (search-matches db {:team team-a :opponent team-b
                               :competition competition :season season})
        scored (filter scored? ms)]
    (reduce
     (fn [acc m]
       (let [r (result-for team-a m)]
         (-> acc
             (update :a-goals + (:gf r))
             (update :b-goals + (:ga r))
             (update (case (:outcome r) :win :a-wins :loss :b-wins :draw :draws)
                     inc))))
     {:team-a (n/canonical-name team-a)
      :team-b (n/canonical-name team-b)
      :matches (count scored)
      :a-wins 0 :b-wins 0 :draws 0 :a-goals 0 :b-goals 0
      :match-list ms}
     scored)))

;; --- 4. Competition standings ----------------------------------------------

(defn standings
  "Compute a league table for a competition/season from match results.
   League points: 3 for a win, 1 for a draw.  Sorted by points, then goal
   difference, then goals for.  Best for round-robin leagues (Brasileirão)."
  [{:keys [matches]} competition season]
  ;; The same Brasileirão season can appear in more than one source (e.g.
  ;; novo_campeonato + Brasileirao_Matches), and the BR-Football dataset uses
  ;; inconsistent team spellings.  To get a clean round-robin table we pick the
  ;; single source with the most matches for this competition/season and
  ;; compute purely from it.  Teams are grouped by accent-insensitive key so
  ;; spelling variants within a source still collapse to one row.
  (let [candidates (->> matches
                        (filter #(and (= competition (:competition %))
                                      (= season (:season %))
                                      (not= "BR-Football-Dataset.csv" (:source %))
                                      (scored? %))))
        ms (if (seq candidates)
             (->> (group-by :source candidates)
                  (apply max-key (comp count val))
                  val)
             [])
        ;; representative display name per match-key (most frequent spelling)
        team-key (fn [t] (n/match-key t))
        names (mapcat (juxt :home :away) ms)
        display (->> names
                     (group-by team-key)
                     (into {} (map (fn [[k vs]]
                                     [k (->> (frequencies vs)
                                             (apply max-key val) key)]))))
        keys* (distinct (map team-key names))]
    (->> keys*
         (map (fn [k]
                (let [rs (keep (fn [m]
                                 (let [home? (= k (team-key (:home m)))
                                       away? (= k (team-key (:away m)))]
                                   (when (or home? away?)
                                     (let [gf (if home? (:home-goals m) (:away-goals m))
                                           ga (if home? (:away-goals m) (:home-goals m))]
                                       {:gf gf :ga ga
                                        :outcome (cond (> gf ga) :win
                                                       (< gf ga) :loss :else :draw)}))))
                               ms)
                      w (count (filter #(= :win (:outcome %)) rs))
                      d (count (filter #(= :draw (:outcome %)) rs))
                      l (count (filter #(= :loss (:outcome %)) rs))
                      gf (reduce + 0 (map :gf rs))
                      ga (reduce + 0 (map :ga rs))]
                  {:team (display k)
                   :played (count rs) :wins w :draws d :losses l
                   :goals-for gf :goals-against ga :goal-diff (- gf ga)
                   :points (+ (* 3 w) d)})))
         (sort-by (juxt :points :goal-diff :goals-for))
         reverse
         (map-indexed (fn [i row] (assoc row :position (inc i))))
         vec)))

;; --- 5b. Aggregate competition statistics ----------------------------------

(defn competition-stats
  "Aggregate stats for a competition/season (or the whole dataset when both
   are nil): goals-per-match, home/away/draw win rates, totals."
  [{:keys [matches]} {:keys [competition season]}]
  (let [ms (->> matches
                (filter #(or (nil? competition) (= competition (:competition %))))
                (filter #(or (nil? season) (= season (:season %))))
                (filter scored?))
        n*  (count ms)
        hw  (count (filter #(> (:home-goals %) (:away-goals %)) ms))
        aw  (count (filter #(< (:home-goals %) (:away-goals %)) ms))
        dr  (- n* hw aw)
        goals (reduce + 0 (mapcat (juxt :home-goals :away-goals) ms))]
    {:competition competition
     :season season
     :matches n*
     :total-goals goals
     :goals-per-match (if (pos? n*) (/ (double goals) n*) 0.0)
     :home-wins hw :away-wins aw :draws dr
     :home-win-rate (if (pos? n*) (/ (double hw) n*) 0.0)
     :away-win-rate (if (pos? n*) (/ (double aw) n*) 0.0)
     :draw-rate (if (pos? n*) (/ (double dr) n*) 0.0)}))

(defn biggest-wins
  "Return the matches with the largest goal margin (optionally filtered by
   competition/season), sorted by margin descending."
  [{:keys [matches]} {:keys [competition season limit] :or {limit 10}}]
  (->> matches
       (filter #(or (nil? competition) (= competition (:competition %))))
       (filter #(or (nil? season) (= season (:season %))))
       (filter scored?)
       (map #(assoc % :margin (abs (- (:home-goals %) (:away-goals %)))))
       (sort-by :margin >)
       (take limit)))

;; --- 3. Player queries ------------------------------------------------------

(defn search-players
  "Search the FIFA player dataset.

   opts:
     :name        substring match on player name (accent-insensitive)
     :nationality exact-ish match (accent-insensitive substring)
     :club        substring match on club (accent-insensitive)
     :position    exact position code (e.g. \"GK\", \"LW\")
     :min-overall minimum FIFA overall rating
     :sort-by     :overall (default) or :potential or :age
     :limit       cap results (default 50)

   Returns a seq of player records sorted by the chosen field descending."
  [{:keys [players]} {:keys [name nationality club position min-overall
                             sort-field limit] :or {sort-field :overall limit 50}}]
  (let [contains-ci? (fn [hay needle]
                       (or (nil? needle)
                           (and hay
                                (str/includes?
                                 (str/lower-case (n/strip-accents hay))
                                 (str/lower-case (n/strip-accents needle))))))
        sort-key (case sort-field :potential :potential :age :age :overall)
        results
        (->> players
             (filter #(contains-ci? (:name %) name))
             (filter #(contains-ci? (:nationality %) nationality))
             (filter #(contains-ci? (:club %) club))
             (filter #(or (nil? position)
                          (and (:position %)
                               (= (str/lower-case (:position %))
                                  (str/lower-case position)))))
             (filter #(or (nil? min-overall)
                          (and (:overall %) (>= (:overall %) min-overall))))
             (sort-by sort-key (fn [a b] (compare (or b 0) (or a 0)))))]
    (take limit results)))

(defn players-by-club-summary
  "For Brazilian (or any nationality) players, group by club and report the
   player count and average overall rating.  Used to answer questions like
   'Brazilian players at Brazilian clubs'."
  [{:keys [players]} {:keys [nationality limit] :or {limit 20}}]
  (let [match-nat? (fn [p] (or (nil? nationality)
                               (= (str/lower-case (n/strip-accents (or (:nationality p) "")))
                                  (str/lower-case (n/strip-accents nationality)))))]
    (->> players
         (filter match-nat?)
         (filter :club)
         (group-by :club)
         (map (fn [[club ps]]
                (let [rs (keep :overall ps)]
                  {:club club
                   :players (count ps)
                   :avg-overall (if (seq rs)
                                  (/ (double (reduce + rs)) (count rs))
                                  0.0)})))
         (sort-by :players >)
         (take limit))))
