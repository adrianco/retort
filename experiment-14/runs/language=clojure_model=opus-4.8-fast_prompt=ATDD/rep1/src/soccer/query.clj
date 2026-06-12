(ns soccer.query
  "Domain query and analysis functions over the normalized dataset.

   Each public function answers one category of question from the spec and
   returns a human-readable, domain-language answer string (the text an MCP
   client surfaces to the user).  Implementation details (CSV columns, name
   suffixes) never leak into the answers."
  (:require [clojure.string :as str]
            [soccer.data :as data]))

;; ---------------------------------------------------------------------------
;; Shared predicates / helpers
;; ---------------------------------------------------------------------------

(defn- q [s] (data/norm s))

(defn- name-matches?
  "True when query `qn` (already normalized) identifies team `team-norm`."
  [team-norm qn]
  (and (seq qn) (str/includes? team-norm qn)))

(defn- involves? [m qn]
  (or (name-matches? (:home-norm m) qn)
      (name-matches? (:away-norm m) qn)))

(defn- has-goals? [m]
  (and (number? (:home-goal m)) (number? (:away-goal m))))

(defn- pct [n d] (if (zero? d) 0.0 (* 100.0 (/ (double n) d))))

(defn- fmt1 [x] (format "%.1f" (double x)))

(defn- competition-label [m]
  (cond-> (:competition m)
    (:round m) (str " Round " (:round m))
    (and (not (:round m)) (:stage m)) (str " — " (:stage m))))

(defn- match-line [m]
  (str (or (:date m) "????-??-??") ": "
       (:home-display m) " " (:home-goal m) "-" (:away-goal m) " "
       (:away-display m)
       " (" (competition-label m) ")"))

(defn- filter-matches
  "Apply the common optional filters to a match seq."
  [matches {:keys [team opponent competition season start-date end-date]}]
  (let [tn (some-> team q)
        on (some-> opponent q)
        cn (some-> competition q)]
    (cond->> matches
      tn (filter #(involves? % tn))
      on (filter #(involves? % on))
      cn (filter #(str/includes? (q (:competition %)) cn))
      season (filter #(= (long season) (:season %)))
      start-date (filter #(and (:date %) (>= (compare (:date %) start-date) 0)))
      end-date (filter #(and (:date %) (<= (compare (:date %) end-date) 0))))))

;; ---------------------------------------------------------------------------
;; Result of a single match from one team's perspective
;; ---------------------------------------------------------------------------

(defn- perspective
  "Return {:gf :ga :result} for `team-norm` in match `m` (:win/:draw/:loss)."
  [m team-norm]
  (let [home? (name-matches? (:home-norm m) team-norm)
        gf (if home? (:home-goal m) (:away-goal m))
        ga (if home? (:away-goal m) (:home-goal m))]
    {:home? home?
     :gf gf :ga ga
     :result (cond (> gf ga) :win (< gf ga) :loss :else :draw)}))

(defn- display-for
  "Pick a clean display name for the queried team from its matches."
  [matches team-norm fallback]
  (or (some (fn [m]
              (cond
                (name-matches? (:home-norm m) team-norm) (:home-display m)
                (name-matches? (:away-norm m) team-norm) (:away-display m)))
            matches)
      (data/display-name fallback)))

;; ---------------------------------------------------------------------------
;; 1. Match queries
;; ---------------------------------------------------------------------------

(defn find-matches [{:keys [matches]} args]
  (let [{:keys [team opponent limit]} args
        sel (->> (filter-matches matches args)
                 (filter has-goals?)
                 (sort-by (juxt :date :competition)))
        sel (if limit (take limit sel) sel)]
    (if (empty? sel)
      "No matches found for those criteria."
      (let [body (str "Found " (count sel) " match"
                      (when (> (count sel) 1) "es") ":\n"
                      (str/join "\n" (map #(str "- " (match-line %)) sel)))]
        (if (and team opponent)
          (let [tn (q team) on (q opponent)
                td (display-for sel tn team)
                od (display-for sel on opponent)
                results (map #(perspective % tn) sel)
                tw (count (filter #(= :win (:result %)) results))
                ow (count (filter #(= :loss (:result %)) results))
                dr (count (filter #(= :draw (:result %)) results))]
            (str body "\n\nHead-to-head: "
                 td " " tw " wins, " od " " ow " wins, " dr " draws."))
          body)))))

;; ---------------------------------------------------------------------------
;; 2. Team queries
;; ---------------------------------------------------------------------------

(defn team-stats [{:keys [matches]} args]
  (let [{:keys [team season competition venue]} args
        tn (q team)
        venue (some-> venue str/lower-case)
        sel (->> (filter-matches matches (assoc args :team team))
                 (filter has-goals?)
                 (filter (fn [m]
                           (case venue
                             "home" (name-matches? (:home-norm m) tn)
                             "away" (name-matches? (:away-norm m) tn)
                             m))))
        results (map #(perspective % tn) sel)
        n (count results)
        wins (count (filter #(= :win (:result %)) results))
        draws (count (filter #(= :draw (:result %)) results))
        losses (count (filter #(= :loss (:result %)) results))
        gf (reduce + 0 (map :gf results))
        ga (reduce + 0 (map :ga results))
        td (display-for sel tn team)
        scope (->> [(when competition competition)
                    (when season (str season))
                    (when venue (str venue))]
                   (remove nil?) (str/join ", "))]
    (if (zero? n)
      (str "No matches found for " td
           (when (seq scope) (str " (" scope ")")) ".")
      (str td " — record"
           (when (seq scope) (str " (" scope ")")) ":\n"
           "- Matches: " n "\n"
           "- Wins: " wins ", Draws: " draws ", Losses: " losses "\n"
           "- Goals For: " gf ", Goals Against: " ga "\n"
           "- Win rate: " (fmt1 (pct wins n)) "%"))))

;; ---------------------------------------------------------------------------
;; Head-to-head comparison
;; ---------------------------------------------------------------------------

(defn compare-teams [{:keys [matches]} args]
  (let [{:keys [team1 team2]} args
        t1 (q team1) t2 (q team2)
        sel (->> matches
                 (filter has-goals?)
                 (filter #(and (involves? % t1) (involves? % t2)))
                 (sort-by :date))
        d1 (display-for sel t1 team1)
        d2 (display-for sel t2 team2)
        results (map #(perspective % t1) sel)
        w1 (count (filter #(= :win (:result %)) results))
        w2 (count (filter #(= :loss (:result %)) results))
        dr (count (filter #(= :draw (:result %)) results))]
    (if (empty? sel)
      (str "No matches found between " d1 " and " d2 ".")
      (str d1 " vs " d2 " — head-to-head (" (count sel) " matches):\n"
           d1 " " w1 " win" (when (not= w1 1) "s") ", "
           d2 " " w2 " win" (when (not= w2 1) "s") ", "
           dr " draw" (when (not= dr 1) "s") ".\n"
           (str/join "\n" (map #(str "- " (match-line %)) sel))))))

;; ---------------------------------------------------------------------------
;; 3. Player queries
;; ---------------------------------------------------------------------------

(defn search-players [{:keys [players]} args]
  (let [{:keys [name nationality club position limit]} args
        nn (some-> name q)
        natn (some-> nationality q)
        cn (some-> club q)
        posn (some-> position str/lower-case str/trim)
        sel (cond->> players
              nn (filter #(str/includes? (:name-norm %) nn))
              natn (filter #(str/includes? (:nat-norm %) natn))
              cn (filter #(str/includes? (:club-norm %) cn))
              posn (filter #(= posn (some-> (:position %) str/lower-case str/trim))))
        sel (->> sel (sort-by :overall >) (take (or limit 20)))]
    (if (empty? sel)
      "No players found for those criteria."
      (str "Found " (count sel) " player" (when (not= 1 (count sel)) "s") ":\n"
           (str/join "\n"
                     (map-indexed
                      (fn [i p]
                        (str (inc i) ". " (:name p)
                             " - Overall: " (:overall p)
                             (when (:position p) (str ", Position: " (:position p)))
                             (when (seq (:club p)) (str ", Club: " (:club p)))
                             (when (:nationality p) (str ", " (:nationality p)))))
                      sel))))))

;; ---------------------------------------------------------------------------
;; 4. Competition standings
;; ---------------------------------------------------------------------------

(defn- standings-rows [matches]
  (->> matches
       (filter has-goals?)
       (reduce
        (fn [acc m]
          (let [home (:home-norm m) away (:away-norm m)
                hg (:home-goal m) ag (:away-goal m)
                upd (fn [acc k display gf ga res]
                      (-> acc
                          (update-in [k :display] #(or % display))
                          (update-in [k :played] (fnil inc 0))
                          (update-in [k :gf] (fnil + 0) gf)
                          (update-in [k :ga] (fnil + 0) ga)
                          (update-in [k :w] (fnil + 0) (if (= res :w) 1 0))
                          (update-in [k :d] (fnil + 0) (if (= res :d) 1 0))
                          (update-in [k :l] (fnil + 0) (if (= res :l) 1 0))
                          (update-in [k :pts] (fnil + 0)
                                     (case res :w 3 :d 1 :l 0))))
                hres (cond (> hg ag) :w (< hg ag) :l :else :d)
                ares (cond (> ag hg) :w (< ag hg) :l :else :d)]
            (-> acc
                (upd home (:home-display m) hg ag hres)
                (upd away (:away-display m) ag hg ares))))
        {})
       vals
       (sort-by (juxt (comp - :pts)
                      (comp - #(- (:gf %) (:ga %)))
                      (comp - :gf)))))

(defn competition-standings [{:keys [matches]} args]
  (let [{:keys [competition season]} args
        sel (filter-matches matches {:competition competition :season season})
        rows (standings-rows sel)]
    (if (empty? rows)
      "No standings could be calculated for those criteria."
      (str (or competition "Competition") (when season (str " " season))
           " — Final Standings (calculated from matches):\n"
           (str/join "\n"
                     (map-indexed
                      (fn [i r]
                        (str (inc i) ". " (:display r) " - " (:pts r) " pts ("
                             (:w r) "W " (:d r) "D " (:l r) "L)"
                             " GF:" (:gf r) " GA:" (:ga r)
                             (when (zero? i) " - Champion")))
                      rows))))))

;; ---------------------------------------------------------------------------
;; 5. Statistical analysis
;; ---------------------------------------------------------------------------

(defn competition-stats [{:keys [matches]} args]
  (let [{:keys [competition season]} args
        sel (->> (filter-matches matches {:competition competition :season season})
                 (filter has-goals?))
        n (count sel)]
    (if (zero? n)
      "No matches found for those criteria."
      (let [goals (reduce + 0 (map #(+ (:home-goal %) (:away-goal %)) sel))
            home-wins (count (filter #(> (:home-goal %) (:away-goal %)) sel))
            away-wins (count (filter #(< (:home-goal %) (:away-goal %)) sel))
            draws (- n home-wins away-wins)
            biggest (->> sel
                         (sort-by #(- (Math/abs (- (:home-goal %) (:away-goal %)))))
                         (take 5))
            scope (->> [(when competition competition) (when season (str season))]
                       (remove nil?) (str/join " "))]
        (str "Statistics" (when (seq scope) (str " — " scope))
             " (" n " matches):\n"
             "- Average goals per match: " (format "%.2f" (/ (double goals) n)) "\n"
             "- Home win rate: " (fmt1 (pct home-wins n)) "%\n"
             "- Away win rate: " (fmt1 (pct away-wins n)) "%\n"
             "- Draw rate: " (fmt1 (pct draws n)) "%\n"
             "Biggest victories:\n"
             (str/join "\n"
                       (map (fn [m]
                              (str "- " (:date m) ": "
                                   (:home-display m) " " (:home-goal m) "-"
                                   (:away-goal m) " " (:away-display m)
                                   " (" (competition-label m) ")"))
                            biggest)))))))
