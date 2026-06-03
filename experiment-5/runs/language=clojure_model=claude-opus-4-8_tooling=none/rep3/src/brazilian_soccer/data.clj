;; =============================================================================
;; brazilian-soccer.data
;; -----------------------------------------------------------------------------
;; Dataset loading and normalisation.
;;
;; Reads the six Kaggle CSV files in `data/kaggle/` and converts them into two
;; uniform in-memory collections:
;;
;;   matches : a vector of match maps with a common schema (see ->match)
;;   players : a vector of FIFA player maps
;;
;; Each match map:
;;   {:competition  "Brasileirão Série A"  ; human label
;;    :source       "Brasileirao_Matches.csv"
;;    :date         "2012-05-19"           ; ISO yyyy-MM-dd (or nil)
;;    :season       2012                   ; integer year (or nil)
;;    :round        "1"                    ; round / stage label (or nil)
;;    :stage        "group stage"          ; libertadores only (or nil)
;;    :home         "Palmeiras"            ; cleaned display name
;;    :away         "Portuguesa"
;;    :home-raw     "Palmeiras-SP"         ; original string
;;    :away-raw     "Portuguesa-SP"
;;    :home-key     "palmeiras"            ; normalize/match-key
;;    :away-key     "portuguesa"
;;    :home-goal    1                      ; integer (or nil)
;;    :away-goal    1
;;    :winner       :home | :away | :draw | nil}
;;
;; Date strings appear in several formats (ISO, ISO+time, DD/MM/YYYY); parse-date
;; normalises them all to ISO yyyy-MM-dd.
;;
;; Datasets are loaded once and cached in `db` (delay) so the MCP server keeps a
;; single read-only snapshot in memory for fast (< 2s) query responses.
;; =============================================================================
(ns brazilian-soccer.data
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer.normalize :as norm]))

(def ^:dynamic *data-dir* "data/kaggle")

;; ---------------------------------------------------------------------------
;; Parsing helpers
;; ---------------------------------------------------------------------------

(defn parse-int
  "Parse `s` as an integer, tolerating floats like \"1.0\" and blanks. nil-safe."
  [s]
  (when (and s (not (str/blank? (str s))))
    (try
      (let [t (str/trim (str s))]
        (cond
          (re-matches #"-?\d+" t)            (Long/parseLong t)
          (re-matches #"-?\d+\.\d+" t)       (long (Double/parseDouble t))
          :else nil))
      (catch Exception _ nil))))

(defn parse-date
  "Normalise a date string to ISO yyyy-MM-dd. Handles:
     2012-05-19 18:30:00 | 2023-09-24 | 29/03/2003
   Returns nil when no date can be extracted."
  [s]
  (when (and s (not (str/blank? (str s))))
    (let [t (str/trim (str s))]
      (cond
        ;; ISO, optionally with a time component
        (re-find #"^\d{4}-\d{2}-\d{2}" t)
        (subs t 0 10)

        ;; Brazilian DD/MM/YYYY
        (re-matches #"\d{1,2}/\d{1,2}/\d{4}" t)
        (let [[d m y] (str/split t #"/")]
          (format "%04d-%02d-%02d"
                  (Long/parseLong y) (Long/parseLong m) (Long/parseLong d)))

        :else nil))))

(defn year-of
  "Year integer from an ISO date string, or nil."
  [iso-date]
  (when iso-date (parse-int (subs iso-date 0 4))))

(defn- winner
  "Classify a result from two goal totals -> :home | :away | :draw | nil."
  [hg ag]
  (when (and (some? hg) (some? ag))
    (cond (> hg ag) :home
          (< hg ag) :away
          :else     :draw)))

(defn ->match
  "Build a normalised match map from already-parsed fields. `home-state` /
   `away-state` are the dataset's dedicated state/UF column values when present
   (nil otherwise); they feed the canonical team identity (:home-uid/:away-uid)."
  [{:keys [competition source date season round stage
           home-raw away-raw home-state away-state hg ag]}]
  (let [date* (parse-date date)]
    {:competition competition
     :source      source
     :date        date*
     :season      (or (parse-int season) (year-of date*))
     :round       (when round (str/trim (str round)))
     :stage       (when stage (str/trim (str stage)))
     :home        (norm/clean-team home-raw)
     :away        (norm/clean-team away-raw)
     :home-raw    home-raw
     :away-raw    away-raw
     :home-key    (norm/match-key home-raw)
     :away-key    (norm/match-key away-raw)
     :home-uid    (norm/team-uid home-raw home-state)
     :away-uid    (norm/team-uid away-raw away-state)
     :home-goal   (parse-int hg)
     :away-goal   (parse-int ag)
     :winner      (winner (parse-int hg) (parse-int ag))}))

;; ---------------------------------------------------------------------------
;; CSV reading
;; ---------------------------------------------------------------------------

(defn- read-csv-maps
  "Read `filename` from *data-dir* and return a lazy-realised vector of row maps
   keyed by header string. Reads as UTF-8. Strips a leading BOM from the first
   header cell (present in fifa_data.csv)."
  [filename]
  (let [path (str *data-dir* "/" filename)]
    (with-open [r (io/reader path :encoding "UTF-8")]
      (let [[header & rows] (csv/read-csv r)
            header (vec (cons (str/replace (first header) #"^﻿" "")
                              (rest header)))]
        (mapv #(zipmap header %) rows)))))

(defn- safe-read
  "read-csv-maps but returns [] (with a stderr warning) if the file is missing,
   so the server still starts when a dataset is absent."
  [filename]
  (try
    (read-csv-maps filename)
    (catch Exception e
      (binding [*out* *err*]
        (println "WARN: could not read" filename "-" (.getMessage e)))
      [])))

;; ---------------------------------------------------------------------------
;; Per-file loaders
;; ---------------------------------------------------------------------------

(defn load-brasileirao []
  (mapv (fn [r]
          (->match {:competition "Brasileirão Série A"
                    :source      "Brasileirao_Matches.csv"
                    :date        (get r "datetime")
                    :season      (get r "season")
                    :round       (get r "round")
                    :home-raw    (get r "home_team")
                    :away-raw    (get r "away_team")
                    :home-state  (get r "home_team_state")
                    :away-state  (get r "away_team_state")
                    :hg          (get r "home_goal")
                    :ag          (get r "away_goal")}))
        (safe-read "Brasileirao_Matches.csv")))

(defn load-cup []
  (mapv (fn [r]
          (->match {:competition "Copa do Brasil"
                    :source      "Brazilian_Cup_Matches.csv"
                    :date        (get r "datetime")
                    :season      (get r "season")
                    :round       (get r "round")
                    :home-raw    (get r "home_team")
                    :away-raw    (get r "away_team")
                    :hg          (get r "home_goal")
                    :ag          (get r "away_goal")}))
        (safe-read "Brazilian_Cup_Matches.csv")))

(defn load-libertadores []
  (mapv (fn [r]
          (->match {:competition "Copa Libertadores"
                    :source      "Libertadores_Matches.csv"
                    :date        (get r "datetime")
                    :season      (get r "season")
                    :round       (get r "stage")
                    :stage       (get r "stage")
                    :home-raw    (get r "home_team")
                    :away-raw    (get r "away_team")
                    :hg          (get r "home_goal")
                    :ag          (get r "away_goal")}))
        (safe-read "Libertadores_Matches.csv")))

(defn load-br-football []
  (mapv (fn [r]
          (->match {:competition (str/trim (str (get r "tournament")))
                    :source      "BR-Football-Dataset.csv"
                    :date        (get r "date")
                    :round       nil
                    :home-raw    (get r "home")
                    :away-raw    (get r "away")
                    :hg          (get r "home_goal")
                    :ag          (get r "away_goal")}))
        (safe-read "BR-Football-Dataset.csv")))

(defn load-historical []
  (mapv (fn [r]
          (->match {:competition "Brasileirão Série A"
                    :source      "novo_campeonato_brasileiro.csv"
                    :date        (get r "Data")
                    :season      (get r "Ano")
                    :round       (get r "Rodada")
                    :home-raw    (get r "Equipe_mandante")
                    :away-raw    (get r "Equipe_visitante")
                    :home-state  (get r "Mandante_UF")
                    :away-state  (get r "Visitante_UF")
                    :hg          (get r "Gols_mandante")
                    :ag          (get r "Gols_visitante")}))
        (safe-read "novo_campeonato_brasileiro.csv")))

(defn load-players []
  (mapv (fn [r]
          {:id          (parse-int (get r "ID"))
           :name        (get r "Name")
           :age         (parse-int (get r "Age"))
           :nationality (get r "Nationality")
           :overall     (parse-int (get r "Overall"))
           :potential   (parse-int (get r "Potential"))
           :club        (get r "Club")
           :position    (get r "Position")
           :jersey      (get r "Jersey Number")
           :height      (get r "Height")
           :weight      (get r "Weight")
           :foot        (get r "Preferred Foot")
           :value       (get r "Value")
           :wage        (get r "Wage")
           :name-key    (norm/match-key (get r "Name"))
           :club-key    (norm/match-key (get r "Club"))
           :nat-key     (norm/match-key (get r "Nationality"))})
        (safe-read "fifa_data.csv")))

;; ---------------------------------------------------------------------------
;; Aggregate snapshot
;; ---------------------------------------------------------------------------

(defn dedupe-matches
  "The Brasileirão Série A appears in three source files (Brasileirao_Matches,
   the historical novo_campeonato file, and BR-Football's 'Serie A' rows), so the
   same physical game can appear up to three times. Collapse duplicates that share
   the same date, both team keys, and final score — keeping the first occurrence
   (load order favours the richer, competition-labelled sources). Matches without
   a parsed date are never merged (their key is unique)."
  [matches]
  (let [seen (volatile! #{})]
    (->> matches
         (reduce
          (fn [acc m]
            (if (nil? (:date m))
              (conj acc m)
              (let [k [(:date m) (:home-uid m) (:away-uid m)
                       (:home-goal m) (:away-goal m)]]
                (if (contains? @seen k)
                  acc
                  (do (vswap! seen conj k) (conj acc m))))))
          [])
         vec)))

(defn load-all
  "Eagerly load every dataset and return {:matches [...] :players [...]}.
   Match sources are concatenated then de-duplicated across files."
  []
  {:matches (dedupe-matches
             (concat (load-brasileirao)
                     (load-cup)
                     (load-libertadores)
                     (load-br-football)
                     (load-historical)))
   :players (load-players)})

(def db
  "Cached, lazily-initialised snapshot of all datasets."
  (delay (load-all)))

(defn matches [] (:matches @db))
(defn players [] (:players @db))
