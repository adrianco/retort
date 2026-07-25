(ns brazilian-soccer.data
  "Loading, normalisation and indexing of the six Kaggle CSV files.

  CONTEXT
  -------
  Builds the in-memory knowledge graph used by every MCP tool:

      teams   -- canonical clubs (see brazilian-soccer.names) with display
                 names, states, raw spelling variants and per-competition
                 coverage.
      matches -- one record per real world fixture.  The same fixture often
                 appears in several files (Serie A 2014-2019 is in three of
                 them), so records are de-duplicated and *merged*: the round
                 comes from one file, the stadium from another, the shots and
                 corners from a third.  Without this step every league table
                 and average would be counted two or three times.
      players -- the FIFA 19 snapshot, linked to canonical clubs where the
                 club also appears in the match data (cross-file queries).

  Everything is loaded once into an immutable map behind a delay, so the MCP
  process pays the parsing cost at start-up and every query afterwards is a
  hash-map lookup or a linear scan over pre-filtered vectors.

  Data files live in `data/kaggle` by default; override with the
  SOCCER_DATA_DIR environment variable or by calling `load-db` directly."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer.names :as names]))

;; ---------------------------------------------------------------------------
;; Source catalogue
;; ---------------------------------------------------------------------------

(def sources
  "Provenance of every CSV, surfaced by the `dataset_info` tool."
  [{:key :brasileirao  :file "Brasileirao_Matches.csv"
    :title "Brasileirão Série A matches (2012-2022)"
    :license "CC BY 4.0"
    :url "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro"}
   {:key :cup          :file "Brazilian_Cup_Matches.csv"
    :title "Copa do Brasil matches (2012-2021)"
    :license "CC BY 4.0"
    :url "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro"}
   {:key :libertadores :file "Libertadores_Matches.csv"
    :title "Copa Libertadores matches (2013-2022)"
    :license "CC BY 4.0"
    :url "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro"}
   {:key :br-football  :file "BR-Football-Dataset.csv"
    :title "Extended match statistics, Série A/B/C + Copa do Brasil (2014-2023)"
    :license "CC0 Public Domain"
    :url "https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches"}
   {:key :novo         :file "novo_campeonato_brasileiro.csv"
    :title "Historical Brasileirão (2003-2019)"
    :license "CC BY 4.0"
    :url "https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019"}
   {:key :fifa         :file "fifa_data.csv"
    :title "FIFA 19 player database (18,207 players)"
    :license "Apache 2.0"
    :url "https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data"}])

(def source-priority
  "Lower wins when two files describe the same fixture."
  {:brasileirao 0 :cup 0 :libertadores 0 :novo 1 :br-football 2})

(def competitions
  {:serie-a       {:name "Brasileirão Série A" :league? true}
   :serie-b       {:name "Brasileirão Série B" :league? true}
   :serie-c       {:name "Brasileirão Série C" :league? true}
   :copa-do-brasil {:name "Copa do Brasil"     :league? false}
   :libertadores  {:name "Copa Libertadores"   :league? false}})

(def competition-aliases
  {"serie a" :serie-a "série a" :serie-a "seriea" :serie-a
   "brasileirao" :serie-a "brasileirão" :serie-a "brasileirao serie a" :serie-a
   "campeonato brasileiro" :serie-a "brazilian league" :serie-a
   "brasileirao serie b" :serie-b "serie b" :serie-b "série b" :serie-b
   "serie c" :serie-c "série c" :serie-c
   "copa do brasil" :copa-do-brasil "brazilian cup" :copa-do-brasil
   "cup" :copa-do-brasil "copa" :copa-do-brasil
   "libertadores" :libertadores "copa libertadores" :libertadores
   "conmebol libertadores" :libertadores})

(defn competition-key
  "Resolve user input (\"Brasileirão\", :serie-a, \"libertadores\") to a key."
  [x]
  (cond
    (nil? x)     nil
    (keyword? x) (when (competitions x) x)
    :else        (let [s (-> x str names/strip-accents str/lower-case str/trim)]
                   (or (competition-aliases s)
                       (competition-aliases (str/replace s #"\s+" " "))
                       (competitions (keyword s))
                       (some (fn [[k {:keys [name]}]]
                               (when (= s (-> name names/strip-accents str/lower-case)) k))
                             competitions)))))

(defn competition-name [k]
  (get-in competitions [k :name] (some-> k name)))

;; ---------------------------------------------------------------------------
;; CSV helpers
;; ---------------------------------------------------------------------------

(defn- read-csv-rows [path]
  (with-open [rdr (io/reader path :encoding "UTF-8")]
    (let [[header & rows] (csv/read-csv rdr)
          header (mapv #(str/replace (str %) "﻿" "") header)]
      {:header header :rows (mapv vec rows)})))

(defn- row-maps [path]
  (let [{:keys [header rows]} (read-csv-rows path)]
    (mapv #(zipmap header %) rows)))

(defn- blank->nil [s]
  (let [s (str/trim (str s))]
    (when-not (or (str/blank? s) (= s "-") (= s "NA") (= s "null")) s)))

(defn ->int [s]
  (when-let [s (blank->nil s)]
    (try
      (long (Double/parseDouble s))
      (catch Exception _ nil))))

(defn ->double [s]
  (when-let [s (blank->nil s)]
    (try (Double/parseDouble s) (catch Exception _ nil))))

(defn parse-date
  "Accepts \"2012-05-19 18:30:00\", \"2023-09-24\" and \"29/03/2003\".
  Returns [iso-date time-or-nil]; dates stay strings because ISO dates sort
  and compare correctly as strings."
  [s]
  (when-let [s (blank->nil s)]
    (cond
      (re-matches #"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?" s)
      [(subs s 0 10) (subs s 11 16)]

      (re-matches #"\d{4}-\d{2}-\d{2}" s)
      [s nil]

      (re-matches #"\d{1,2}/\d{1,2}/\d{4}" s)
      (let [[d m y] (str/split s #"/")]
        [(format "%s-%02d-%02d" y (Integer/parseInt m) (Integer/parseInt d)) nil])

      :else nil)))

;; ---------------------------------------------------------------------------
;; Per-file readers -> "raw match" maps (team names still un-normalised)
;; ---------------------------------------------------------------------------

(defn- brasileirao-rows [dir]
  (for [r (row-maps (io/file dir "Brasileirao_Matches.csv"))
        :let [[date time] (parse-date (r "datetime"))]]
    {:source :brasileirao :competition :serie-a
     :season (->int (r "season")) :round (->int (r "round"))
     :date date :time time
     :home-raw (r "home_team") :away-raw (r "away_team")
     :home-state (blank->nil (r "home_team_state"))
     :away-state (blank->nil (r "away_team_state"))
     :home-goals (->int (r "home_goal")) :away-goals (->int (r "away_goal"))}))

(defn- cup-rows [dir]
  (for [r (row-maps (io/file dir "Brazilian_Cup_Matches.csv"))
        :let [[date time] (parse-date (r "datetime"))]]
    {:source :cup :competition :copa-do-brasil
     :season (->int (r "season")) :round (->int (r "round"))
     :date date :time time
     :home-raw (r "home_team") :away-raw (r "away_team")
     :home-goals (->int (r "home_goal")) :away-goals (->int (r "away_goal"))}))

(defn- libertadores-rows [dir]
  (for [r (row-maps (io/file dir "Libertadores_Matches.csv"))
        :let [[date time] (parse-date (r "datetime"))]]
    {:source :libertadores :competition :libertadores
     :season (->int (r "season")) :stage (blank->nil (r "stage"))
     :date date :time time
     :home-raw (r "home_team") :away-raw (r "away_team")
     :home-goals (->int (r "home_goal")) :away-goals (->int (r "away_goal"))}))

(def ^:private br-football-competitions
  {"Serie A" :serie-a "Serie B" :serie-b "Serie C" :serie-c
   "Copa do Brasil" :copa-do-brasil})

(defn br-football-season
  "This file has no season column, only a date.  The Brasileirão never kicks off
  before April, but the COVID-shifted 2020 and 2021 seasons ran into January and
  February of the following year, so early-year league fixtures belong to the
  previous season.  Cup fixtures do start in February and are left alone."
  [date competition]
  (when date
    (let [year  (->int (subs date 0 4))
          month (->int (subs date 5 7))]
      (if (and (get-in competitions [competition :league?]) (<= month 3))
        (dec year)
        year))))

(defn- br-football-rows [dir]
  (for [r (row-maps (io/file dir "BR-Football-Dataset.csv"))
        :let [[date _] (parse-date (r "date"))
              competition (br-football-competitions (str/trim (str (r "tournament"))))]
        :when competition]
    {:source :br-football :competition competition
     :season (br-football-season date competition)
     :date date :time (some-> (blank->nil (r "time")) (subs 0 5))
     :home-raw (r "home") :away-raw (r "away")
     :home-goals (->int (r "home_goal")) :away-goals (->int (r "away_goal"))
     :stats (into {} (remove (comp nil? val))
                  {:home-corners (->int (r "home_corner"))
                   :away-corners (->int (r "away_corner"))
                   :home-shots   (->int (r "home_shots"))
                   :away-shots   (->int (r "away_shots"))
                   :home-attacks (->int (r "home_attack"))
                   :away-attacks (->int (r "away_attack"))
                   :total-corners (->int (r "total_corners"))
                   :ht-home-result (blank->nil (r "ht_result"))
                   :ht-away-result (blank->nil (r "at_result"))})}))

(defn- novo-rows [dir]
  (for [r (row-maps (io/file dir "novo_campeonato_brasileiro.csv"))
        :let [[date _] (parse-date (r "Data"))]]
    {:source :novo :competition :serie-a
     :season (->int (r "Ano")) :round (->int (r "Rodada"))
     :date date
     :home-raw (r "Equipe_mandante") :away-raw (r "Equipe_visitante")
     :home-state (blank->nil (r "Mandante_UF"))
     :away-state (blank->nil (r "Visitante_UF"))
     :home-goals (->int (r "Gols_mandante")) :away-goals (->int (r "Gols_visitante"))
     :venue (blank->nil (r "Arena"))}))

;; ---------------------------------------------------------------------------
;; Team index
;; ---------------------------------------------------------------------------

(defn- strip-region-suffix [raw]
  (str/trim (str/replace raw #"(?i)[\s]*[-–][\s]*([A-Za-zÀ-ú]{2,3})$"
                         (fn [[whole code]]
                           (if (names/region-code? (names/strip-accents code)) "" whole)))))

(defn- best-variant
  "Prefer an accented spelling, then the shortest, then the most frequent."
  [variants]
  (->> variants
       (sort-by (fn [[raw n]]
                  [(if (= raw (names/strip-accents raw)) 1 0)
                   (count (strip-region-suffix raw))
                   (- n)]))
       ffirst))

(defn build-team-index
  "raw-name-counts: {\"Flamengo-RJ\" 418, ...}.  Returns
  {:raw->id {...} :teams {id {:id :display :base :region :variants}}}."
  [raw-name-counts]
  (let [parsed (into {} (for [[raw _] raw-name-counts]
                          [raw (names/parse-team-name raw)]))
        ;; regions actually observed for each base, used to fill in the blanks
        base->regions (reduce (fn [m [_ {:keys [base region]}]]
                                (if region (update-in m [base region] (fnil inc 0)) m))
                              {} parsed)
        raw->id (into {}
                      (for [[raw {:keys [base region]}] parsed
                            :let [region (or region
                                             (let [rs (keys (base->regions base))]
                                               (when (= 1 (count rs)) (first rs))))]]
                        [raw (names/team-id base region)]))
        variants (reduce (fn [m [raw id]]
                           (update m id (fnil conj {}) [raw (get raw-name-counts raw 0)]))
                         {} raw->id)
        ;; a base shared by several ids (América-MG vs América-RN) needs the
        ;; state shown in the display name to stay unambiguous
        base-counts (frequencies (map names/id-base (keys variants)))
        teams (into {}
                    (for [[id vs] variants
                          :let [base   (names/id-base id)
                                region (names/id-region id)
                                raw    (best-variant vs)
                                plain  (strip-region-suffix raw)
                                ambiguous? (> (get base-counts base 0) 1)]]
                      [id {:id      id
                           :base    base
                           :region  region
                           :state   (when (names/brazilian-states (str region))
                                      (str/upper-case region))
                           :country (when (names/foreign-codes (str region))
                                      (str/upper-case region))
                           :display (or (names/display-names id)
                                        (if (and ambiguous? region)
                                          (str plain " (" (str/upper-case region) ")")
                                          plain))
                           :variants (vec (sort (keys vs)))}]))]
    {:raw->id raw->id :teams teams :base->regions base->regions}))

(defn resolve-name
  "Canonical team id for a name that was not part of the corpus (a FIFA club, a
  user's query), using the same region inference as `build-team-index`."
  [{:keys [raw->id base->regions]} raw]
  (or (get raw->id raw)
      (let [{:keys [base region]} (names/parse-team-name raw)
            region (or region
                       (let [rs (keys (get base->regions base))]
                         (when (= 1 (count rs)) (first rs))))]
        (names/team-id base region))))

;; ---------------------------------------------------------------------------
;; De-duplication / merging across files
;; ---------------------------------------------------------------------------

(defn- days-apart [a b]
  (when (and a b)
    (abs (- (.toEpochDay (java.time.LocalDate/parse a))
            (.toEpochDay (java.time.LocalDate/parse b))))))

(defn- same-score? [a b]
  (= [(:home-goals a) (:away-goals a)] [(:home-goals b) (:away-goals b)]))

(defn- mergeable?
  "Do two records describe the same fixture?

  Across files, a league fixture is identified by competition/season/home/away
  alone - every ordered pair meets exactly once per season - which matters
  because the files disagree about kick-off dates (late kick-offs roll over
  midnight) and occasionally about the score itself.  Cup competitions can pair
  the same teams twice in a season (group stage, then a knockout round), so
  there the records must also agree on the score or fall within a couple of
  days of each other.

  Within a single file (BR-Football-Dataset.csv lists a handful of fixtures
  twice, a day or two apart) both the score and the date must line up."
  [a b]
  (if (= (:source a) (:source b))
    (and (same-score? a b)
         (when-let [d (days-apart (:date a) (:date b))] (<= d 3)))
    (or (get-in competitions [(:competition a) :league?])
        (same-score? a b)
        (when-let [d (days-apart (:date a) (:date b))] (<= d 2)))))

(defn- merge-into-primary
  "Fold lower priority records into the best one, filling in whatever it is
  missing.  Brasileirao_Matches.csv was scraped mid-2022 and lists 82 fixtures
  with a round and a kick-off time but no score; the score arrives here from
  BR-Football-Dataset.csv."
  [primary others]
  (reduce (fn [acc other]
            (-> acc
                (update :home-goals #(or % (:home-goals other)))
                (update :away-goals #(or % (:away-goals other)))
                (update :date   #(or % (:date other)))
                (update :time   #(or % (:time other)))
                (update :round  #(or % (:round other)))
                (update :stage  #(or % (:stage other)))
                (update :venue  #(or % (:venue other)))
                (update :stats  #(merge (:stats other) %))
                (update :sources conj (:source other))))
          (assoc primary :sources #{(:source primary)})
          others))

(defn- cluster-fixtures
  "Group the records of one [competition season home away] key into clusters
  that each describe a single fixture."
  [group]
  (reduce (fn [clusters m]
            (if-let [idx (first (keep-indexed
                                 (fn [i c]
                                   (when (every? #(mergeable? m %) c) i))
                                 clusters))]
              (update clusters idx conj m)
              (conj clusters [m])))
          []
          (sort-by (comp source-priority :source) group)))

(defn- dedupe-matches [raw-matches]
  (->> raw-matches
       (group-by (juxt :competition :season :home-id :away-id))
       (mapcat (fn [[_ group]]
                 (map (fn [c] (merge-into-primary (first c) (rest c)))
                      (cluster-fixtures group))))
       vec))

(def ^:private complete-season-threshold
  "A Série A or Série B season of this size is a full double round-robin."
  300)

(defn- mislabelled-league-matches
  "BR-Football-Dataset.csv files a handful of state championship games under
  \"Serie A\" / \"Serie B\" (Brasília vs Taguatinga in the 2015 Série A, Bagé vs
  Monsoon in the 2022 Série B).  In a complete national season every club plays
  38 matches, so a club with fewer than five is not in that division at all."
  [matches]
  (set (for [[[competition _] ms] (group-by (juxt :competition :season) matches)
             :when (and (#{:serie-a :serie-b} competition)
                        (>= (count ms) complete-season-threshold))
             :let [appearances (frequencies (mapcat (juxt :home-id :away-id) ms))]
             m ms
             :when (or (< (appearances (:home-id m)) 5)
                       (< (appearances (:away-id m)) 5))]
         m)))

;; ---------------------------------------------------------------------------
;; Match records
;; ---------------------------------------------------------------------------

(defn result
  "One of :home-win, :away-win, :draw (nil when the score is unknown)."
  [{:keys [home-goals away-goals]}]
  (when (and home-goals away-goals)
    (cond (> home-goals away-goals) :home-win
          (< home-goals away-goals) :away-win
          :else                     :draw)))

(defn- finish-match [teams m]
  (let [home (get teams (:home-id m))
        away (get teams (:away-id m))]
    (assoc m
           :home (:display home) :away (:display away)
           :home-state (or (:home-state m) (:state home))
           :away-state (or (:away-state m) (:state away))
           :competition-name (competition-name (:competition m))
           :result (result m)
           :played? (boolean (and (:home-goals m) (:away-goals m)))
           :total-goals (when (and (:home-goals m) (:away-goals m))
                          (+ (:home-goals m) (:away-goals m)))
           :sources (vec (sort (map name (:sources m)))))))

;; ---------------------------------------------------------------------------
;; Players
;; ---------------------------------------------------------------------------

(def ^:private player-skill-columns
  ["Crossing" "Finishing" "HeadingAccuracy" "ShortPassing" "Dribbling" "Curve"
   "FKAccuracy" "LongPassing" "BallControl" "Acceleration" "SprintSpeed"
   "Agility" "Reactions" "Balance" "ShotPower" "Jumping" "Stamina" "Strength"
   "LongShots" "Aggression" "Interceptions" "Positioning" "Vision" "Penalties"
   "Composure" "Marking" "StandingTackle" "SlidingTackle" "GKDiving"
   "GKHandling" "GKKicking" "GKPositioning" "GKReflexes"])

(defn- load-players [dir]
  (let [{:keys [header rows]} (read-csv-rows (io/file dir "fifa_data.csv"))
        idx    (into {} (map-indexed (fn [i h] [h i]) header))
        get-in-row (fn [row col] (when-let [i (idx col)] (blank->nil (nth row i nil))))]
    (mapv (fn [row]
            (let [g #(get-in-row row %)]
              {:id          (->int (g "ID"))
               :name        (g "Name")
               :age         (->int (g "Age"))
               :nationality (g "Nationality")
               :overall     (->int (g "Overall"))
               :potential   (->int (g "Potential"))
               :club        (g "Club")
               :position    (g "Position")
               :jersey      (->int (g "Jersey Number"))
               :value       (g "Value")
               :wage        (g "Wage")
               :foot        (g "Preferred Foot")
               :height      (g "Height")
               :weight      (g "Weight")
               :joined      (g "Joined")
               :contract    (g "Contract Valid Until")
               :skills      (into {} (for [c player-skill-columns
                                           :let [v (->int (g c))]
                                           :when v]
                                       [c v]))}))
          rows)))

(def position-groups
  {"GK"  :goalkeeper
   "CB"  :defender "LCB" :defender "RCB" :defender "LB" :defender "RB" :defender
   "LWB" :defender "RWB" :defender
   "CDM" :midfielder "LDM" :midfielder "RDM" :midfielder "CM" :midfielder
   "LCM" :midfielder "RCM" :midfielder "LM" :midfielder "RM" :midfielder
   "CAM" :midfielder "LAM" :midfielder "RAM" :midfielder
   "ST"  :forward "LS" :forward "RS" :forward "CF" :forward "LF" :forward
   "RF"  :forward "LW" :forward "RW" :forward})

(defn position-group [pos] (get position-groups (str pos)))

;; ---------------------------------------------------------------------------
;; Database assembly
;; ---------------------------------------------------------------------------

(defn default-data-dir []
  (or (System/getenv "SOCCER_DATA_DIR") "data/kaggle"))

(defn load-db
  "Read every CSV under `dir` and build the query database."
  ([] (load-db (default-data-dir)))
  ([dir]
   (let [dir (io/file dir)
         _   (when-not (.isDirectory dir)
               (throw (ex-info (str "Data directory not found: " dir
                                    " (set SOCCER_DATA_DIR)")
                               {:dir (str dir)})))
         raw-matches (vec (concat (brasileirao-rows dir) (cup-rows dir)
                                  (libertadores-rows dir) (br-football-rows dir)
                                  (novo-rows dir)))
         name-counts (frequencies (mapcat (juxt :home-raw :away-raw) raw-matches))
         players     (load-players dir)
         index       (build-team-index name-counts)
         {:keys [raw->id teams]} index
         ;; a row without a season cannot be placed in the graph at all (one
         ;; placeholder row in the Libertadores file); rows without a score are
         ;; kept, flagged :played? false and skipped by every statistic
         playable    (filter :season raw-matches)
         dropped     (- (count raw-matches) (count playable))
         identified  (map #(assoc % :home-id (raw->id (:home-raw %))
                                  :away-id (raw->id (:away-raw %)))
                          playable)
         deduped     (dedupe-matches identified)
         strays      (mislabelled-league-matches deduped)
         matches     (->> deduped
                          (remove strays)
                          (map #(finish-match teams %))
                          (sort-by (juxt :date :competition))
                          vec)
         by-team     (reduce (fn [m mt]
                               (-> m
                                   (update (:home-id mt) (fnil conj []) mt)
                                   (update (:away-id mt) (fnil conj []) mt)))
                             {} matches)
         ;; FIFA squads are linked to a canonical club only when the club also
         ;; appears in the match data *and* the squad is predominantly
         ;; Brazilian.  Without the second test "FC Barcelona" would normalise
         ;; onto Barcelona SC of Ecuador, which does play in the Libertadores.
         by-club     (group-by :club players)
         club->team  (into {} (for [[club squad] by-club
                                    :when (and club (seq squad))
                                    :let [brazilians (count (filter #(= "Brazil" (:nationality %)) squad))
                                          id (resolve-name index club)]
                                    :when (and (contains? by-team id)
                                               (>= brazilians (/ (count squad) 2)))]
                                [club id]))
         ;; clubs whose only appearances were the mislabelled rows above drop
         ;; out of the index entirely - they never played in this data
         teams       (reduce-kv (fn [m id t]
                                  (if-let [team-matches (seq (get by-team id))]
                                    (assoc m id
                                           (assoc t
                                                  :match-count (count team-matches)
                                                  :competitions (vec (sort (distinct (map :competition team-matches))))))
                                    m))
                                {} teams)]
     {:dir          (str dir)
      :teams        teams
      :index        index
      :matches      matches
      :by-team      by-team
      :players      players
      :players-by-club by-club
      :club->team-id club->team
      :team-id->clubs (reduce (fn [m [club id]] (update m id (fnil conj []) club)) {} club->team)
      :stats        {:raw-match-rows (count raw-matches)
                     :dropped-rows   dropped
                     :mislabelled-rows (count strays)
                     :unique-matches (count matches)
                     :teams          (count teams)
                     :players        (count players)
                     :rows-by-source (frequencies (map :source raw-matches))}
      :sources      sources})))

(defonce ^{:doc "The shared, lazily loaded database."} db-delay
  (atom (delay (load-db))))

(defn db [] @@db-delay)

(defn reset-db!
  "Point the shared database at another directory (used by tests)."
  ([] (reset! db-delay (delay (load-db))))
  ([dir] (reset! db-delay (delay (load-db dir)))))
