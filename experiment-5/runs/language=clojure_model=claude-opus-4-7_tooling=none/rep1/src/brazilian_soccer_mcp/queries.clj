(ns brazilian-soccer-mcp.queries
  "Pure query functions over the normalized dataset returned by
  `brazilian-soccer-mcp.data/load-dataset`.

  Every function takes the dataset map as its first argument so that
  the MCP layer and the tests can share the same query surface."
  (:require [brazilian-soccer-mcp.data :as data]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; Match queries
;; ---------------------------------------------------------------------------

(defn- match-involves? [m team-key]
  (or (data/team-key-matches? team-key (:home-key m))
      (data/team-key-matches? team-key (:away-key m))))

(defn- match-of-teams? [m a b]
  (or (and (data/team-key-matches? a (:home-key m))
           (data/team-key-matches? b (:away-key m)))
      (and (data/team-key-matches? b (:home-key m))
           (data/team-key-matches? a (:away-key m)))))

(defn filter-matches
  "General-purpose match filter.
   Options (any may be omitted):
     :team         team name (matches home or away)
     :home         restrict to home team
     :away         restrict to away team
     :team-a/:team-b  head-to-head (either side)
     :season       integer
     :season-from / :season-to  inclusive range
     :competition  substring match on competition name (case-insensitive)
     :date-from    \"YYYY-MM-DD\" inclusive
     :date-to      \"YYYY-MM-DD\" inclusive
     :stage        substring match on stage
     :round        exact match on round (string)
     :limit        cap result count"
  [{:keys [matches]} {:keys [team home away team-a team-b season season-from season-to
                              competition date-from date-to stage round limit]
                       :as _opts}]
  (let [tk     (some-> team data/normalize-team)
        hk     (some-> home data/normalize-team)
        ak     (some-> away data/normalize-team)
        a-k    (some-> team-a data/normalize-team)
        b-k    (some-> team-b data/normalize-team)
        comp-l (some-> competition str/lower-case)
        stg-l  (some-> stage str/lower-case)]
    (cond->> matches
      tk          (filter #(match-involves? % tk))
      hk          (filter #(data/team-key-matches? hk (:home-key %)))
      ak          (filter #(data/team-key-matches? ak (:away-key %)))
      (and a-k b-k) (filter #(match-of-teams? % a-k b-k))
      season      (filter #(= (:season %) season))
      season-from (filter #(and (:season %) (>= (:season %) season-from)))
      season-to   (filter #(and (:season %) (<= (:season %) season-to)))
      comp-l      (filter #(some-> % :competition str/lower-case (str/includes? comp-l)))
      stg-l       (filter #(some-> % :stage str/lower-case (str/includes? stg-l)))
      round       (filter #(= (str round) (:round %)))
      date-from   (filter #(and (:date %) (>= (compare (:date %) date-from) 0)))
      date-to     (filter #(and (:date %) (<= (compare (:date %) date-to) 0)))
      true        (sort-by (juxt :date :competition))
      limit       (take limit)
      true        vec)))

(defn head-to-head
  "Return matches between two teams plus an aggregate win/draw/loss breakdown
   from the perspective of team-a."
  [dataset team-a team-b]
  (let [ms     (filter-matches dataset {:team-a team-a :team-b team-b})
        a-key  (data/normalize-team team-a)
        agg    (reduce
                 (fn [acc m]
                   (let [a-home? (data/team-key-matches? a-key (:home-key m))
                         a-goal  (if a-home? (:home-goal m) (:away-goal m))
                         b-goal  (if a-home? (:away-goal m) (:home-goal m))]
                     (cond
                       (or (nil? a-goal) (nil? b-goal)) acc
                       (> a-goal b-goal) (update acc :a-wins inc)
                       (< a-goal b-goal) (update acc :b-wins inc)
                       :else             (update acc :draws inc))))
                 {:a-wins 0 :b-wins 0 :draws 0}
                 ms)]
    {:team-a   team-a
     :team-b   team-b
     :matches  ms
     :total    (count ms)
     :aggregate agg}))

;; ---------------------------------------------------------------------------
;; Team statistics
;; ---------------------------------------------------------------------------

(defn- match->team-result
  "Return :win/:loss/:draw for the given team in a match, or nil if unknown."
  [m team-key]
  (let [hg (:home-goal m) ag (:away-goal m)]
    (when (and hg ag)
      (cond
        (data/team-key-matches? team-key (:home-key m))
        (cond (> hg ag) :win (< hg ag) :loss :else :draw)
        (data/team-key-matches? team-key (:away-key m))
        (cond (> ag hg) :win (< ag hg) :loss :else :draw)
        :else nil))))

(defn- match->team-goals [m team-key]
  (cond
    (data/team-key-matches? team-key (:home-key m)) [(:home-goal m) (:away-goal m)]
    (data/team-key-matches? team-key (:away-key m)) [(:away-goal m) (:home-goal m)]
    :else                                            [nil nil]))

(defn team-stats
  "Aggregate W/D/L/GF/GA/points for a team over a filtered set of matches.
   `opts` is forwarded to `filter-matches` (the :team option is set
   automatically)."
  [dataset team & [opts]]
  (let [team-key (data/normalize-team team)
        ms      (filter-matches dataset (merge (or opts {}) {:team team}))
        init    {:matches (count ms) :wins 0 :draws 0 :losses 0
                 :goals-for 0 :goals-against 0 :home {:matches 0 :wins 0 :draws 0 :losses 0}
                 :away {:matches 0 :wins 0 :draws 0 :losses 0}}]
    (assoc
      (reduce
        (fn [acc m]
          (let [res (match->team-result m team-key)
                [gf ga] (match->team-goals m team-key)
                side (cond (data/team-key-matches? team-key (:home-key m)) :home
                           (data/team-key-matches? team-key (:away-key m)) :away)
                acc  (cond-> acc
                       gf (update :goals-for + gf)
                       ga (update :goals-against + ga))
                acc  (case res
                       :win  (-> acc (update :wins inc)
                                 (update-in [side :wins] inc)
                                 (update-in [side :matches] inc))
                       :loss (-> acc (update :losses inc)
                                 (update-in [side :losses] inc)
                                 (update-in [side :matches] inc))
                       :draw (-> acc (update :draws inc)
                                 (update-in [side :draws] inc)
                                 (update-in [side :matches] inc))
                       acc)]
            acc))
        init
        ms)
      :team team
      :team-key team-key
      :sample-matches (take 5 ms))))

(defn- with-points [{:keys [wins draws] :as s}]
  (assoc s :points (+ (* 3 wins) draws)))

(defn standings
  "Compute a league table for a given season (and competition).
   Sorts by points desc, then goal difference, then goals for.
   Teams are grouped by normalized team key so display-name variants
   (\"Flamengo\" vs \"Flamengo-RJ\") collapse to a single row."
  [dataset {:keys [season competition] :or {competition "Brasileirão"}}]
  (let [ms     (filter-matches dataset {:season season :competition competition})
        ;; Pick a stable display name per team-key: the longest-seen variant
        ;; tends to be the most informative (e.g. "Flamengo-RJ" over "Flamengo").
        display (reduce
                  (fn [acc m]
                    (reduce
                      (fn [acc [k n]]
                        (if (and k n)
                          (let [cur (get acc k)]
                            (if (or (nil? cur) (> (count n) (count cur)))
                              (assoc acc k n)
                              acc))
                          acc))
                      acc
                      [[(:home-key m) (:home m)]
                       [(:away-key m) (:away m)]]))
                  {}
                  ms)
        team-keys (keys display)
        rows   (mapv (fn [k]
                       (let [display-name (get display k)
                             s  (team-stats {:matches ms} display-name {})
                             gd (- (:goals-for s) (:goals-against s))]
                         (-> s
                             with-points
                             (assoc :team display-name :gd gd)
                             (dissoc :sample-matches))))
                     team-keys)]
    (vec
      (sort-by (fn [r] [(- (:points r)) (- (:gd r)) (- (:goals-for r))]) rows))))

;; ---------------------------------------------------------------------------
;; Statistical roll-ups
;; ---------------------------------------------------------------------------

(defn average-goals [dataset opts]
  (let [ms (filter-matches dataset opts)
        gs (keep (fn [m] (when (and (:home-goal m) (:away-goal m))
                           (+ (:home-goal m) (:away-goal m)))) ms)
        n  (count gs)]
    {:matches n
     :total-goals (reduce + 0 gs)
     :avg-goals   (if (zero? n) 0.0 (double (/ (reduce + 0 gs) n)))}))

(defn home-win-rate [dataset opts]
  (let [ms (filter-matches dataset opts)
        ms (filter :result ms)
        n  (count ms)
        h  (count (filter #(= :home (:result %)) ms))
        a  (count (filter #(= :away (:result %)) ms))
        d  (count (filter #(= :draw (:result %)) ms))]
    {:matches n
     :home-wins h :away-wins a :draws d
     :home-win-rate (if (zero? n) 0.0 (double (/ h n)))
     :away-win-rate (if (zero? n) 0.0 (double (/ a n)))
     :draw-rate     (if (zero? n) 0.0 (double (/ d n)))}))

(defn biggest-wins
  "Top-N matches by goal margin (defaults to 10)."
  [dataset {:keys [limit] :or {limit 10} :as opts}]
  (let [ms (filter-matches dataset (dissoc opts :limit))]
    (->> ms
         (filter #(and (:home-goal %) (:away-goal %)))
         (sort-by (fn [m] (- (Math/abs (- (:home-goal m) (:away-goal m))))))
         (take limit)
         vec)))

;; ---------------------------------------------------------------------------
;; Player queries
;; ---------------------------------------------------------------------------

(defn- str-includes-ci? [hay needle]
  (and hay needle
       (str/includes? (str/lower-case hay) (str/lower-case needle))))

(defn search-players
  "Search and filter FIFA players.
   Options:
     :name         substring match (case-insensitive)
     :nationality  exact match (case-insensitive)
     :club         substring match (case-insensitive, on club display name)
     :position     exact match (case-insensitive)
     :min-overall  integer
     :sort         :overall (default) | :potential | :age
     :limit        defaults to 50"
  [{:keys [players]}
   {:keys [name nationality club position min-overall sort limit]
    :or   {sort :overall limit 50}}]
  (let [filt (cond->> players
               name        (filter #(str-includes-ci? (:name %) name))
               nationality (filter #(and (:nationality %)
                                         (= (str/lower-case (:nationality %))
                                            (str/lower-case nationality))))
               club        (filter #(str-includes-ci? (:club %) club))
               position    (filter #(and (:position %)
                                         (= (str/lower-case (:position %))
                                            (str/lower-case position))))
               min-overall (filter #(and (:overall %) (>= (:overall %) min-overall))))
        key  (case sort
               :potential (fn [p] (- (or (:potential p) 0)))
               :age       (fn [p] (or (:age p) 0))
               (fn [p] (- (or (:overall p) 0))))]
    (vec (take limit (sort-by key filt)))))

(defn brazilians-by-club [dataset]
  (->> (search-players dataset {:nationality "Brazil" :limit 100000})
       (group-by :club)
       (map (fn [[club ps]]
              {:club     (or club "(no club)")
               :count    (count ps)
               :avg-rating (if (seq ps)
                             (double (/ (reduce + 0 (keep :overall ps))
                                        (count ps)))
                             0.0)}))
       (sort-by (fn [r] [(- (:count r)) (- (:avg-rating r))]))
       vec))

;; ---------------------------------------------------------------------------
;; Pretty-printers used by the MCP tool layer
;; ---------------------------------------------------------------------------

(defn format-match [m]
  (let [score (when (and (:home-goal m) (:away-goal m))
                (str (:home-goal m) "-" (:away-goal m)))
        round (when (:round m) (str " Round " (:round m)))
        stage (when (:stage m) (str " (" (:stage m) ")"))]
    (str (or (:date m) "?")
         ": "
         (:home m) " " (or score "?-?") " " (:away m)
         " [" (:competition m) (or round "") (or stage "") "]")))

(defn format-matches [ms]
  (if (seq ms)
    (str/join "\n" (map format-match ms))
    "No matches found."))

(defn format-team-stats [s]
  (let [{:keys [team matches wins draws losses goals-for goals-against home away]} s
        win-rate (if (zero? matches) 0.0 (* 100.0 (/ wins matches)))]
    (str/join "\n"
      [(str team " summary:")
       (format "  Matches: %d" matches)
       (format "  W/D/L:   %d / %d / %d" wins draws losses)
       (format "  Goals:   %d for, %d against (diff %+d)"
               goals-for goals-against (- goals-for goals-against))
       (format "  Win rate: %.1f%%" win-rate)
       (format "  Home:    %d matches, %d wins, %d draws, %d losses"
               (:matches home) (:wins home) (:draws home) (:losses home))
       (format "  Away:    %d matches, %d wins, %d draws, %d losses"
               (:matches away) (:wins away) (:draws away) (:losses away))])))

(defn format-standings [rows]
  (let [hdr (format "%-4s %-30s %4s %4s %4s %4s %4s %4s %4s"
                    "#" "Team" "P" "W" "D" "L" "GF" "GA" "Pts")]
    (str/join "\n"
      (cons hdr
        (map-indexed
          (fn [i r]
            (format "%-4d %-30s %4d %4d %4d %4d %4d %4d %4d"
                    (inc i)
                    (let [t (:team r)] (if (> (count t) 30) (subs t 0 30) t))
                    (:matches r) (:wins r) (:draws r) (:losses r)
                    (:goals-for r) (:goals-against r) (:points r)))
          rows)))))

(defn format-player [p]
  (format "%s — Overall %s, %s, Club: %s, Nat: %s, Age: %s"
          (or (:name p) "?")
          (or (:overall p) "?")
          (or (:position p) "?")
          (or (:club p) "?")
          (or (:nationality p) "?")
          (or (:age p) "?")))

(defn format-players [ps]
  (if (seq ps)
    (str/join "\n" (map-indexed (fn [i p] (str (inc i) ". " (format-player p))) ps))
    "No players found."))
