(ns brazilian-soccer-mcp.query
  "Read-only queries over the records produced by `brazilian-soccer-mcp.data`."
  (:require [clojure.string :as str]
            [brazilian-soccer-mcp.normalize :as n]))

(def competition-labels
  {:brasileirao "Brasileirão"
   :copa-do-brasil "Copa do Brasil"
   :libertadores "Libertadores"
   :serie-b "Série B"
   :serie-c "Série C"})

(defn parse-competition
  "Maps a user-supplied competition name to its keyword, or nil when unknown."
  [s]
  (let [t (n/normalize-text s)]
    (cond
      (str/includes? t "libertadores") :libertadores
      (str/includes? t "copa do brasil") :copa-do-brasil
      (re-find #"serie b" t) :serie-b
      (re-find #"serie c" t) :serie-c
      (re-find #"brasileir|serie a" t) :brasileirao)))

(defn- involves? [tk m]
  (or (n/same-team? tk (:home-key m)) (n/same-team? tk (:away-key m))))

(defn- venue-pred [tk venue]
  (case venue
    :home #(n/same-team? tk (:home-key %))
    :away #(n/same-team? tk (:away-key %))
    #(involves? tk %)))

(defn select-matches
  "All matches satisfying the optional filters, oldest first.
  Options: :team :opponent :venue (:home :away :any) :competition :season :from :to (LocalDate)."
  [{:keys [matches]} {:keys [team opponent venue competition season from to] :or {venue :any}}]
  (let [preds (cond-> []
                team (conj (venue-pred (n/team-key team) venue))
                opponent (conj #(involves? (n/team-key opponent) %))
                competition (conj #(= competition (:competition %)))
                season (conj #(= season (:season %)))
                from (conj #(not (neg? (compare (:date %) from))))
                to (conj #(not (pos? (compare (:date %) to)))))]
    (filter (fn [m] (every? #(% m) preds)) matches)))

(defn search-matches
  "Most recent matches first, capped at :limit (default 20), plus the total count."
  [db {:keys [limit] :or {limit 20} :as opts}]
  (let [ms (reverse (select-matches db opts))]
    {:total (count ms)
     :matches (vec (take limit ms))}))

(defn- pct [part whole]
  (when (pos? whole)
    (/ (Math/round (* 1000.0 (/ part whole))) 10.0)))

(defn- perspective
  "A match seen from one team's side."
  [tk m]
  (let [home? (n/same-team? tk (:home-key m))
        [gf ga opponent] (if home?
                           [(:home-goals m) (:away-goals m) (:away m)]
                           [(:away-goals m) (:home-goals m) (:home m)])]
    {:venue (if home? :home :away)
     :for gf
     :against ga
     :opponent opponent
     :result (cond (> gf ga) :win (< gf ga) :loss :else :draw)
     :match m}))

(defn team-record
  "Wins, draws, losses and goals for one team under the same filters as select-matches."
  [db team opts]
  (let [tk (n/team-key team)
        rows (mapv #(perspective tk %) (select-matches db (assoc opts :team team)))
        results (frequencies (map :result rows))
        played (count rows)]
    {:team (n/display-name team)
     :matches played
     :wins (get results :win 0)
     :draws (get results :draw 0)
     :losses (get results :loss 0)
     :goals-for (reduce + 0 (map :for rows))
     :goals-against (reduce + 0 (map :against rows))
     :win-rate (pct (get results :win 0) played)}))

(defn head-to-head
  "Results between two teams from team a's perspective, most recent first."
  [db a b {:keys [limit] :or {limit 10}}]
  (let [ka (n/team-key a)
        kb (n/team-key b)
        between? (fn [m]
                   (or (and (n/same-team? ka (:home-key m)) (n/same-team? kb (:away-key m)))
                       (and (n/same-team? kb (:home-key m)) (n/same-team? ka (:away-key m)))))
        rows (mapv #(perspective ka %) (filter between? (:matches db)))
        results (frequencies (map :result rows))]
    {:team-a (n/display-name a)
     :team-b (n/display-name b)
     :total (count rows)
     :a-wins (get results :win 0)
     :draws (get results :draw 0)
     :b-wins (get results :loss 0)
     :a-goals (reduce + 0 (map :for rows))
     :b-goals (reduce + 0 (map :against rows))
     :matches (vec (take limit (reverse rows)))}))

(defn- add-entry
  "Folds one team-match result into that team's running table row."
  [row team gf ga]
  (let [res (cond (> gf ga) :wins (< gf ga) :losses :else :draws)
        row (merge {:team (n/display-name team) :played 0 :wins 0 :draws 0
                    :losses 0 :goals-for 0 :goals-against 0}
                   row)]
    (-> row
        (update :played inc)
        (update res inc)
        (update :goals-for + gf)
        (update :goals-against + ga))))

(defn standings
  "League table for one competition and season: 3 points for a win, 1 for a draw.
  Teams are grouped by base name, so Atletico-MG and Atletico-GO would merge."
  [db competition season]
  (let [ms (select-matches db {:competition competition :season season})
        table (reduce (fn [acc m]
                        (-> acc
                            (update (get-in m [:home-key :base]) add-entry
                                    (:home m) (:home-goals m) (:away-goals m))
                            (update (get-in m [:away-key :base]) add-entry
                                    (:away m) (:away-goals m) (:home-goals m))))
                      {}
                      ms)]
    (->> (vals table)
         (map #(assoc % :points (+ (* 3 (:wins %)) (:draws %))
                      :goal-diff (- (:goals-for %) (:goals-against %))))
         (sort-by (juxt (comp - :points) (comp - :goal-diff) (comp - :goals-for) :team))
         (map-indexed #(assoc %2 :position (inc %1)))
         vec)))

(defn- margin [m]
  (abs (- (:home-goals m) (:away-goals m))))

(defn match-stats
  "Goal, home-advantage and biggest-win summary for the filtered matches."
  [db {:keys [top] :or {top 5} :as opts}]
  (let [ms (vec (select-matches db opts))
        total (count ms)
        goals (reduce + 0 (map #(+ (:home-goals %) (:away-goals %)) ms))
        home-wins (count (filter #(> (:home-goals %) (:away-goals %)) ms))
        away-wins (count (filter #(< (:home-goals %) (:away-goals %)) ms))]
    {:matches total
     :goals goals
     :goals-per-match (when (pos? total) (/ (Math/round (* 100.0 (/ goals total))) 100.0))
     :home-win-rate (pct home-wins total)
     :draw-rate (pct (- total home-wins away-wins) total)
     :away-win-rate (pct away-wins total)
     :biggest-wins (->> ms
                        (sort-by (juxt (comp - margin) :date))
                        (take top)
                        vec)}))

(def ^:private position-groups
  {"forward" #{"ST" "CF" "LW" "RW" "LF" "RF"}
   "midfielder" #{"CAM" "CM" "CDM" "LM" "RM" "LAM" "RAM" "LCM" "RCM" "LDM" "RDM"}
   "defender" #{"CB" "LB" "RB" "LWB" "RWB" "LCB" "RCB"}
   "goalkeeper" #{"GK"}})

(defn- position-match? [wanted position]
  (let [codes (position-groups (n/normalize-text wanted)
                               #{(str/upper-case wanted)})]
    (contains? codes (str/upper-case (or position "")))))

(defn search-players
  "Players matching every given filter, highest overall first. Text filters are
  case- and accent-insensitive substring matches; position accepts a group name
  (forward, midfielder, defender, goalkeeper) or a FIFA position code."
  [{:keys [players]} {:keys [name nationality club position min-overall limit] :or {limit 20}}]
  (let [matches? (fn [field wanted]
                   (or (nil? wanted)
                       (str/includes? (n/normalize-text field) (n/normalize-text wanted))))
        hits (->> players
                  (filter (fn [p]
                            (and (matches? (:name p) name)
                                 (matches? (:nationality p) nationality)
                                 (matches? (:club p) club)
                                 (or (nil? position) (position-match? position (:position p)))
                                 (or (nil? min-overall) (>= (or (:overall p) 0) min-overall)))))
                  (sort-by (juxt (comp - #(or (:overall %) 0)) :name)))]
    {:total (count hits)
     :players (vec (take limit hits))}))
