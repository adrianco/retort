(ns brazilian-soccer.data
  "Context
  =======
  Loads the six provided Kaggle CSV files into two in-memory collections:

    * `matches` - one normalised map per match, unifying five differently
                  shaped match files into a single schema.
    * `players` - one map per FIFA player row.

  All files are read as UTF-8. Team names are normalised via
  `brazilian-soccer.normalize`; dates are coerced to ISO `yyyy-MM-dd`.

  Unified match schema:
    {:competition  str   ; e.g. \"Brasileirão Série A\"
     :season       int   ; year of the competition
     :round        str   ; round / stage label (nil when unknown)
     :stage        str   ; tournament stage, Libertadores only (else nil)
     :date         str   ; ISO \"yyyy-MM-dd\" (nil if unparseable)
     :home         str   ; display name (suffix stripped, accents kept)
     :away         str
     :home-key     str   ; canonical match key (accent/suffix free)
     :away-key     str
     :home-goal    int
     :away-goal    int
     :arena        str   ; stadium (when available)
     :source       str}  ; originating file name

  The loaded data is cached behind `db` so the CSVs are parsed only once."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer.normalize :as nz]))

(def ^:private data-dir
  (or (System/getenv "BSOCCER_DATA_DIR") "data/kaggle"))

;; ---------------------------------------------------------------------------
;; Parsing helpers
;; ---------------------------------------------------------------------------

(defn parse-int
  "Lenient integer parse. Accepts \"3\", \"3.0\", 3 ; returns nil on failure."
  [v]
  (cond
    (integer? v) v
    (number? v)  (long v)
    (string? v)  (let [s (str/trim v)]
                   (when (seq s)
                     (try
                       (long (Double/parseDouble s))
                       (catch Exception _ nil))))
    :else nil))

(defn parse-date
  "Normalise the many date formats in the data to ISO `yyyy-MM-dd`.

    \"2012-05-19 18:30:00\" -> \"2012-05-19\"
    \"2023-09-24\"          -> \"2023-09-24\"
    \"29/03/2003\"          -> \"2003-03-29\""
  [v]
  (when (and v (string? v) (seq (str/trim v)))
    (let [s (str/trim v)]
      (cond
        ;; ISO with optional time component
        (re-find #"^\d{4}-\d{2}-\d{2}" s)
        (subs s 0 10)

        ;; Brazilian DD/MM/YYYY
        (re-find #"^\d{1,2}/\d{1,2}/\d{4}" s)
        (let [[d m y] (str/split (first (str/split s #"\s")) #"/")]
          (format "%04d-%02d-%02d"
                  (Integer/parseInt y)
                  (Integer/parseInt m)
                  (Integer/parseInt d)))

        :else nil))))

(defn year-of
  "Extract the four-digit year from an ISO date string, or nil."
  [iso-date]
  (when (and iso-date (>= (count iso-date) 4))
    (parse-int (subs iso-date 0 4))))

;; ---------------------------------------------------------------------------
;; CSV reading
;; ---------------------------------------------------------------------------

(defn- read-csv
  "Read a CSV file into a seq of maps keyed by header string. Strips a UTF-8
  BOM from the first header cell if present."
  [filename]
  (let [path (str data-dir "/" filename)
        f (io/file path)]
    (when (.exists f)
      (with-open [rdr (io/reader f :encoding "UTF-8")]
        (let [[header & rows] (csv/read-csv rdr)
              header (vec (cons (str/replace (first header) "﻿" "")
                                (rest header)))]
          (doall
           (for [row rows :when (seq row)]
             (zipmap header row))))))))

(defn- mk-match
  "Build a unified match map from already-extracted fields."
  [{:keys [competition season round stage date home away
           home-goal away-goal arena source]}]
  (let [iso (parse-date date)]
    {:competition competition
     :season      (or (parse-int season) (year-of iso))
     :round       (when (and round (seq (str round))) (str round))
     :stage       (when (and stage (seq (str stage))) (str stage))
     :date        iso
     :home        (nz/display-name home)
     :away        (nz/display-name away)
     :home-key    (nz/match-key home)
     :away-key    (nz/match-key away)
     :home-goal   (parse-int home-goal)
     :away-goal   (parse-int away-goal)
     :arena       (when (and arena (seq (str arena))) (str arena))
     :source      source}))

(defn- valid-match?
  "A row is usable only when both teams and both scores resolved."
  [m]
  (and (:home-key m) (:away-key m)
       (:home-goal m) (:away-goal m)))

;; ---------------------------------------------------------------------------
;; Per-file loaders
;; ---------------------------------------------------------------------------

(defn- load-brasileirao []
  (for [r (read-csv "Brasileirao_Matches.csv")]
    (mk-match {:competition "Brasileirão Série A"
               :season (get r "season")
               :round (get r "round")
               :date (get r "datetime")
               :home (get r "home_team")
               :away (get r "away_team")
               :home-goal (get r "home_goal")
               :away-goal (get r "away_goal")
               :source "Brasileirao_Matches.csv"})))

(defn- load-cup []
  (for [r (read-csv "Brazilian_Cup_Matches.csv")]
    (mk-match {:competition "Copa do Brasil"
               :season (get r "season")
               :round (get r "round")
               :date (get r "datetime")
               :home (get r "home_team")
               :away (get r "away_team")
               :home-goal (get r "home_goal")
               :away-goal (get r "away_goal")
               :source "Brazilian_Cup_Matches.csv"})))

(defn- load-libertadores []
  (for [r (read-csv "Libertadores_Matches.csv")]
    (mk-match {:competition "Copa Libertadores"
               :season (get r "season")
               :stage (get r "stage")
               :date (get r "datetime")
               :home (get r "home_team")
               :away (get r "away_team")
               :home-goal (get r "home_goal")
               :away-goal (get r "away_goal")
               :source "Libertadores_Matches.csv"})))

(defn- load-extended []
  (for [r (read-csv "BR-Football-Dataset.csv")]
    (let [tour (get r "tournament")]
      (mk-match {:competition (case tour
                                "Serie A" "Brasileirão Série A"
                                "Serie B" "Brasileirão Série B"
                                "Serie C" "Brasileirão Série C"
                                tour)
                 :date (get r "date")
                 :home (get r "home")
                 :away (get r "away")
                 :home-goal (get r "home_goal")
                 :away-goal (get r "away_goal")
                 :source "BR-Football-Dataset.csv"}))))

(defn- load-historical []
  (for [r (read-csv "novo_campeonato_brasileiro.csv")]
    (mk-match {:competition "Brasileirão Série A"
               :season (get r "Ano")
               :round (get r "Rodada")
               :date (get r "Data")
               :home (get r "Equipe_mandante")
               :away (get r "Equipe_visitante")
               :home-goal (get r "Gols_mandante")
               :away-goal (get r "Gols_visitante")
               :arena (get r "Arena")
               :source "novo_campeonato_brasileiro.csv"})))

;; Preference order when two files cover the same competition+season slice.
;; The dedicated league/cup files use cleaner, internally-consistent team names
;; than the broad BR-Football aggregate, so they win ties.
(def ^:private source-priority
  {"novo_campeonato_brasileiro.csv" 5
   "Brasileirao_Matches.csv"        4
   "Brazilian_Cup_Matches.csv"      4
   "Libertadores_Matches.csv"       4
   "BR-Football-Dataset.csv"        1})

(defn- dedupe-matches
  "The provided files overlap heavily (e.g. the 2019 Brasileirão appears in
  Brasileirao_Matches, the historical file AND BR-Football, sometimes with
  off-by-one dates and divergent team spellings). Unioning them double/triple
  counts every match and corrupts standings.

  We therefore keep, for each [competition season] slice, the matches from a
  single authoritative source: the file contributing the most matches for that
  slice (ties broken by `source-priority`). Within one file team names are
  internally consistent, so standings and records come out clean, and no real
  fixture is dropped by fuzzy cross-file matching."
  [ms]
  (->> ms
       (group-by (juxt :competition :season))
       (mapcat (fn [[_ slice]]
                 (let [by-src (group-by :source slice)
                       winner (apply max-key
                                     (fn [[src rows]]
                                       ;; Dedicated files carry a real `season`
                                       ;; column and always beat the BR-Football
                                       ;; aggregate (whose season is derived from
                                       ;; the date and mixes COVID-delayed
                                       ;; campaigns). Within a tier, more matches
                                       ;; wins, then explicit priority.
                                       (let [prio (get source-priority src 0)]
                                         (+ (if (>= prio 4) 100000000 0)
                                            (* 100 (count rows))
                                            prio)))
                                     by-src)]
                   (val winner))))
       vec))

(defn- load-matches []
  (->> (concat (load-brasileirao)
               (load-cup)
               (load-libertadores)
               (load-extended)
               (load-historical))
       (filter valid-match?)
       dedupe-matches
       (sort-by (juxt :season :date))
       vec))

;; ---------------------------------------------------------------------------
;; Players
;; ---------------------------------------------------------------------------

(defn- load-players []
  (->> (read-csv "fifa_data.csv")
       (keep (fn [r]
               (let [name (get r "Name")]
                 (when (and name (seq (str/trim name)))
                   {:id        (parse-int (get r "ID"))
                    :name      (str/trim name)
                    :age       (parse-int (get r "Age"))
                    :nationality (get r "Nationality")
                    :overall   (parse-int (get r "Overall"))
                    :potential (parse-int (get r "Potential"))
                    :club      (get r "Club")
                    :club-key  (nz/match-key (get r "Club"))
                    :position  (get r "Position")
                    :jersey    (parse-int (get r "Jersey Number"))
                    :height    (get r "Height")
                    :weight    (get r "Weight")
                    :value     (get r "Value")
                    :wage      (get r "Wage")
                    :preferred-foot (get r "Preferred Foot")}))))
       vec))

;; ---------------------------------------------------------------------------
;; Cached database
;; ---------------------------------------------------------------------------

(def db
  "Delay holding {:matches [...] :players [...]}; parsed on first deref."
  (delay
    {:matches (load-matches)
     :players (load-players)}))

(defn matches [] (:matches @db))
(defn players [] (:players @db))

(defn reset-db!
  "Forget the cached database (used by tests after changing BSOCCER_DATA_DIR)."
  []
  (alter-var-root #'db (fn [_] (delay {:matches (load-matches)
                                       :players (load-players)}))))
