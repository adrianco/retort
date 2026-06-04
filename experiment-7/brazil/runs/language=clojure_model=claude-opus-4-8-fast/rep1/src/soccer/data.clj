;; =============================================================================
;; soccer.data — Dataset loading & normalization into in-memory records
;; -----------------------------------------------------------------------------
;; Project: brazilian-soccer-mcp
;;
;; Context:
;;   Loads the six Kaggle CSV files from data/kaggle/ and projects each into a
;;   uniform shape so the query layer never has to care which file a row came
;;   from.  Everything is held in memory (a few tens of thousands of rows),
;;   which keeps every query well under the spec's 2s/5s latency budgets.
;;
;; Uniform match record:
;;   {:competition  "Brasileirão Série A"   ; canonical competition label
;;    :season       2012                     ; integer year (nil if unknown)
;;    :round        "1"                       ; round/stage label (string|nil)
;;    :stage        "group stage"             ; knockout stage (Libertadores)
;;    :date         #object[LocalDate ...]    ; parsed match date (nil if none)
;;    :home         "Palmeiras"               ; canonical home team
;;    :away         "Portuguesa"              ; canonical away team
;;    :home-raw     "Palmeiras-SP"            ; original spelling (home)
;;    :away-raw     "Portuguesa-SP"           ; original spelling (away)
;;    :home-goals   1   :away-goals 1         ; final score (nil if missing)
;;    :arena        "Brinco de Ouro"          ; stadium (when available)
;;    :stats        {:home-shots .. }         ; extra stats (BR-Football only)
;;    :source       "Brasileirao_Matches.csv"}
;;
;; Uniform player record (from fifa_data.csv):
;;   {:id :name :age :nationality :overall :potential :club :position
;;    :jersey :height :weight :foot :value :wage}
;;
;; Public API:
;;   (load-db)        -> {:matches [...] :players [...]}  (deduped matches)
;;   (load-db path)   -> as above, loading CSVs from `path`
;;   (db)             -> memoized default database (lazy, loaded once)
;; =============================================================================
(ns soccer.data
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [soccer.normalize :as n]))

(def default-data-dir "data/kaggle")

;; --- low level CSV helpers --------------------------------------------------

(defn- read-csv
  "Read a CSV file into a seq of maps keyed by header string.
   Returns nil (with a warning) if the file is missing."
  [path]
  (if (.exists (io/file path))
    (with-open [r (io/reader path :encoding "UTF-8")]
      (let [[header & rows] (csv/read-csv r)
            ;; strip a possible UTF-8 BOM from the first header cell
            header (vec (cons (str/replace (first header) "﻿" "")
                              (rest header)))]
        (doall (map #(zipmap header %) rows))))
    (do (binding [*out* *err*]
          (println "WARN: dataset not found:" path))
        nil)))

(defn- ->int [s]
  (when (and s (not (str/blank? s)) (not= "NA" s))
    (try (Integer/parseInt (str/trim (first (str/split (str s) #"\."))))
         (catch Exception _ nil))))

(defn- ->double [s]
  (when (and s (not (str/blank? s)) (not= "NA" s))
    (try (Double/parseDouble (str/trim s)) (catch Exception _ nil))))

(defn- mk-match
  "Build a uniform match record, filling in canonical team names."
  [{:keys [home away] :as m}]
  (assoc m
         :home (n/canonical-name home)
         :away (n/canonical-name away)
         :home-raw home
         :away-raw away))

;; --- per-file loaders -------------------------------------------------------

(defn- load-brasileirao [dir]
  (->> (read-csv (str dir "/Brasileirao_Matches.csv"))
       (keep (fn [r]
               (mk-match
                {:competition "Brasileirão Série A"
                 :season      (->int (get r "season"))
                 :round       (get r "round")
                 :stage       nil
                 :date        (n/parse-date (get r "datetime"))
                 :home        (get r "home_team")
                 :away        (get r "away_team")
                 :home-goals  (->int (get r "home_goal"))
                 :away-goals  (->int (get r "away_goal"))
                 :source      "Brasileirao_Matches.csv"})))))

(defn- load-cup [dir]
  (->> (read-csv (str dir "/Brazilian_Cup_Matches.csv"))
       (keep (fn [r]
               (mk-match
                {:competition "Copa do Brasil"
                 :season      (->int (get r "season"))
                 :round       (get r "round")
                 :stage       nil
                 :date        (n/parse-date (get r "datetime"))
                 :home        (get r "home_team")
                 :away        (get r "away_team")
                 :home-goals  (->int (get r "home_goal"))
                 :away-goals  (->int (get r "away_goal"))
                 :source      "Brazilian_Cup_Matches.csv"})))))

(defn- load-libertadores [dir]
  (->> (read-csv (str dir "/Libertadores_Matches.csv"))
       (keep (fn [r]
               (mk-match
                {:competition "Copa Libertadores"
                 :season      (->int (get r "season"))
                 :round       (get r "stage")
                 :stage       (get r "stage")
                 :date        (n/parse-date (get r "datetime"))
                 :home        (get r "home_team")
                 :away        (get r "away_team")
                 :home-goals  (->int (get r "home_goal"))
                 :away-goals  (->int (get r "away_goal"))
                 :source      "Libertadores_Matches.csv"})))))

(def ^:private br-football-competition
  {"Serie A" "Brasileirão Série A"
   "Serie B" "Brasileirão Série B"
   "Serie C" "Brasileirão Série C"
   "Copa do Brasil" "Copa do Brasil"})

(defn- load-br-football [dir]
  (->> (read-csv (str dir "/BR-Football-Dataset.csv"))
       (keep (fn [r]
               (let [tourn (get r "tournament")
                     date  (n/parse-date (get r "date"))]
                 (mk-match
                  {:competition (br-football-competition tourn tourn)
                   :season      (when date (.getYear date))
                   :round       nil
                   :stage       nil
                   :date        date
                   :home        (get r "home")
                   :away        (get r "away")
                   :home-goals  (->int (get r "home_goal"))
                   :away-goals  (->int (get r "away_goal"))
                   :stats       {:home-corner (->double (get r "home_corner"))
                                 :away-corner (->double (get r "away_corner"))
                                 :home-shots  (->double (get r "home_shots"))
                                 :away-shots  (->double (get r "away_shots"))
                                 :home-attack (->double (get r "home_attack"))
                                 :away-attack (->double (get r "away_attack"))
                                 :total-corners (->double (get r "total_corners"))
                                 :ht-result   (get r "ht_result")}
                   :source      "BR-Football-Dataset.csv"}))))))

(defn- load-novo [dir]
  (->> (read-csv (str dir "/novo_campeonato_brasileiro.csv"))
       (keep (fn [r]
               (mk-match
                {:competition "Brasileirão Série A"
                 :season      (->int (get r "Ano"))
                 :round       (get r "Rodada")
                 :stage       nil
                 :date        (n/parse-date (get r "Data"))
                 :home        (get r "Equipe_mandante")
                 :away        (get r "Equipe_visitante")
                 :home-goals  (->int (get r "Gols_mandante"))
                 :away-goals  (->int (get r "Gols_visitante"))
                 :arena       (get r "Arena")
                 :source      "novo_campeonato_brasileiro.csv"})))))

(defn- load-players [dir]
  (->> (read-csv (str dir "/fifa_data.csv"))
       (keep (fn [r]
               (when-let [nm (get r "Name")]
                 {:id          (->int (get r "ID"))
                  :name        nm
                  :age         (->int (get r "Age"))
                  :nationality (get r "Nationality")
                  :overall     (->int (get r "Overall"))
                  :potential   (->int (get r "Potential"))
                  :club        (get r "Club")
                  :position    (get r "Position")
                  :jersey      (->int (get r "Jersey Number"))
                  :height      (get r "Height")
                  :weight      (get r "Weight")
                  :foot        (get r "Preferred Foot")
                  :value       (get r "Value")
                  :wage        (get r "Wage")})))))

;; --- dedup & assembly -------------------------------------------------------

(defn- dedup-key
  "Two rows describe the same match if they share competition, season, both
   (canonical) teams, date and score.  Used to drop overlap between the two
   Brasileirão sources (2012-2019 appear in both files)."
  [m]
  [(:competition m) (:season m)
   (n/match-key (:home m)) (n/match-key (:away m))
   (:date m) (:home-goals m) (:away-goals m)])

(defn- dedup-matches
  "Remove duplicate match rows, preferring the first occurrence.
   Rows without a date are never treated as duplicates (kept as-is)."
  [matches]
  (let [seen (volatile! #{})]
    (vec (filter (fn [m]
                   (if (:date m)
                     (let [k (dedup-key m)]
                       (if (@seen k) false (do (vswap! seen conj k) true)))
                     true))
                 matches))))

(defn load-db
  "Load all datasets from `dir` (defaults to data/kaggle) and return
   {:matches [...] :players [...]}.  Matches are deduplicated."
  ([] (load-db default-data-dir))
  ([dir]
   (let [matches (dedup-matches
                  (concat (load-brasileirao dir)
                          (load-cup dir)
                          (load-libertadores dir)
                          (load-br-football dir)
                          (load-novo dir)))
         players (vec (load-players dir))]
     {:matches matches
      :players players})))

(def db
  "Memoized default database — loaded from data/kaggle on first use."
  (memoize (fn [] (load-db))))
