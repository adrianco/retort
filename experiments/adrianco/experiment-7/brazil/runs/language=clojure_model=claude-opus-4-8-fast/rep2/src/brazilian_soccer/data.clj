(ns brazilian-soccer.data
  "=============================================================================
   data.clj — CSV loading & the in-memory knowledge graph
   -----------------------------------------------------------------------------
   Context:
     Loads the six Kaggle CSV files in data/kaggle/ into normalized Clojure
     data structures that the query layer operates on. We intentionally use an
     in-memory model (rather than Neo4j) so the server is self-contained,
     fast (<2s lookups, <5s aggregates), and trivially testable.

   Produces two normalized collections:
     * matches — unified match records from the five match datasets:
         {:competition :season :round :date :stage :arena
          :home-team :away-team :home-goal :away-goal
          :home-key :away-key :source ...extended stats}
     * players — FIFA player records keyed by useful columns.

   Data-quality handling (per spec):
     * Team names normalized via brazilian-soccer.normalize
     * Multiple date formats (ISO, ISO+time, DD/MM/YYYY) -> ISO \"YYYY-MM-DD\"
     * Goals stored as floats (\"1.0\") or quoted strings -> longs
     * UTF-8 read explicitly; a BOM on fifa_data.csv is stripped.

   Loading is memoized behind delays so the CSVs are parsed once per process
   (or once per explicit (load-db!) call in tests).
   ============================================================================="
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer.normalize :as norm]))

(def ^:const data-dir "data/kaggle")

;; ---------------------------------------------------------------------------
;; Low level parsing helpers
;; ---------------------------------------------------------------------------

(defn- read-csv
  "Read a UTF-8 CSV file into a seq of rows (vectors of strings).
   Strips a leading UTF-8 BOM from the first cell if present."
  [filename]
  (with-open [r (io/reader (io/file data-dir filename) :encoding "UTF-8")]
    (let [rows (doall (csv/read-csv r))]
      (when (seq rows)
        (let [[h & more] rows
              h (vec (cons (str/replace (first h) #"^﻿" "") (rest h)))]
          (cons h more))))))

(defn- rows->maps
  "Convert CSV rows (header + data) into a seq of keyword-keyed maps.
   Header strings are used verbatim as keyword names."
  [rows]
  (when (seq rows)
    (let [header (mapv keyword (first rows))]
      (map #(zipmap header %) (rest rows)))))

(defn ->long
  "Parse an integer that may be encoded as \"3\", \"3.0\", or quoted/blank.
   Returns nil when the value is missing or non-numeric."
  [v]
  (when (and v (not (str/blank? (str v))))
    (try
      (long (Double/parseDouble (str/trim (str v))))
      (catch Exception _ nil))))

(defn normalize-date
  "Normalize the various date formats to ISO \"YYYY-MM-DD\".
     \"2012-05-19 18:30:00\" -> \"2012-05-19\"
     \"2023-09-24\"          -> \"2023-09-24\"
     \"29/03/2003\"          -> \"2003-03-29\""
  [s]
  (when (and s (not (str/blank? s)))
    (let [s (str/trim s)]
      (cond
        ;; ISO date, optionally with a time component
        (re-find #"^\d{4}-\d{2}-\d{2}" s)
        (subs s 0 10)

        ;; Brazilian DD/MM/YYYY
        (re-find #"^\d{1,2}/\d{1,2}/\d{4}$" s)
        (let [[d m y] (str/split s #"/")]
          (format "%s-%02d-%02d" y (Integer/parseInt m) (Integer/parseInt d)))

        :else s))))

(defn- year-of [iso-date]
  (when (and iso-date (>= (count iso-date) 4))
    (->long (subs iso-date 0 4))))

;; ---------------------------------------------------------------------------
;; Per-file mappers -> unified match record
;; ---------------------------------------------------------------------------

(defn- ->match
  "Build a unified match record, computing normalized keys and the winner."
  [{:keys [home-team away-team home-goal away-goal] :as m}]
  (let [hg home-goal ag away-goal
        winner (cond
                 (or (nil? hg) (nil? ag)) nil
                 (> hg ag) :home
                 (< hg ag) :away
                 :else     :draw)]
    (assoc m
           ;; pretty display name (state/country suffix removed)
           :home-team (norm/display-name home-team)
           :away-team (norm/display-name away-team)
           ;; raw name preserves the suffix so distinct clubs that share a base
           ;; name (Atlético-MG vs Atlético-GO) are not conflated in league tables
           :home-raw  (some-> home-team str/trim)
           :away-raw  (some-> away-team str/trim)
           :home-key  (norm/match-key home-team)
           :away-key  (norm/match-key away-team)
           :winner    winner)))

(defn- load-brasileirao []
  (->> (rows->maps (read-csv "Brasileirao_Matches.csv"))
       (map (fn [r]
              (->match {:competition "Brasileirão"
                        :source      "Brasileirao_Matches"
                        :date        (normalize-date (:datetime r))
                        :home-team   (:home_team r)
                        :away-team   (:away_team r)
                        :home-goal   (->long (:home_goal r))
                        :away-goal   (->long (:away_goal r))
                        :season      (->long (:season r))
                        :round       (->long (:round r))})))))

(defn- load-cup []
  (->> (rows->maps (read-csv "Brazilian_Cup_Matches.csv"))
       (map (fn [r]
              (->match {:competition "Copa do Brasil"
                        :source      "Brazilian_Cup_Matches"
                        :date        (normalize-date (:datetime r))
                        :home-team   (:home_team r)
                        :away-team   (:away_team r)
                        :home-goal   (->long (:home_goal r))
                        :away-goal   (->long (:away_goal r))
                        :season      (->long (:season r))
                        :round       (:round r)})))))

(defn- load-libertadores []
  (->> (rows->maps (read-csv "Libertadores_Matches.csv"))
       (map (fn [r]
              (->match {:competition "Copa Libertadores"
                        :source      "Libertadores_Matches"
                        :date        (normalize-date (:datetime r))
                        :home-team   (:home_team r)
                        :away-team   (:away_team r)
                        :home-goal   (->long (:home_goal r))
                        :away-goal   (->long (:away_goal r))
                        :season      (->long (:season r))
                        :stage       (:stage r)})))))

(defn- load-historical []
  (->> (rows->maps (read-csv "novo_campeonato_brasileiro.csv"))
       (map (fn [r]
              (->match {:competition "Brasileirão"
                        :source      "novo_campeonato_brasileiro"
                        :date        (normalize-date (:Data r))
                        :home-team   (:Equipe_mandante r)
                        :away-team   (:Equipe_visitante r)
                        :home-goal   (->long (:Gols_mandante r))
                        :away-goal   (->long (:Gols_visitante r))
                        :season      (->long (:Ano r))
                        :round       (->long (:Rodada r))
                        :arena       (:Arena r)})))))

(defn- canonical-tournament
  "Map BR-Football tournament labels onto canonical competition names.
   Série A is the top flight and is folded into the canonical \"Brasileirão\"
   so it deduplicates against the other two Brasileirão sources for correct
   league tables. Série B / C are kept distinct (and named so their match-key
   does NOT contain \"brasileirao\", avoiding substring collisions in
   competition filters)."
  [t]
  (case (some-> t str/trim str/lower-case)
    "serie a"        "Brasileirão"
    "serie b"        "Série B"
    "serie c"        "Série C"
    "copa do brasil" "Copa do Brasil"
    (or t "Unknown")))

(defn- load-br-football []
  (->> (rows->maps (read-csv "BR-Football-Dataset.csv"))
       (map (fn [r]
              (let [date (normalize-date (:date r))]
                (->match {:competition (canonical-tournament (:tournament r))
                          :source      "BR-Football-Dataset"
                          :date        date
                          :home-team   (:home r)
                          :away-team   (:away r)
                          :home-goal   (->long (:home_goal r))
                          :away-goal   (->long (:away_goal r))
                          :season      (year-of date)
                          ;; extended statistics unique to this dataset
                          :home-corner (->long (:home_corner r))
                          :away-corner (->long (:away_corner r))
                          :home-shots  (->long (:home_shots r))
                          :away-shots  (->long (:away_shots r))
                          :home-attack (->long (:home_attack r))
                          :away-attack (->long (:away_attack r))
                          :ht-result   (:ht_result r)
                          :at-result   (:at_result r)}))))))

;; ---------------------------------------------------------------------------
;; Players (FIFA)
;; ---------------------------------------------------------------------------

(defn- load-players []
  (->> (rows->maps (read-csv "fifa_data.csv"))
       (map (fn [r]
              {:id          (->long (:ID r))
               :name        (:Name r)
               :age         (->long (:Age r))
               :nationality (:Nationality r)
               :overall     (->long (:Overall r))
               :potential   (->long (:Potential r))
               :club        (:Club r)
               :position    (:Position r)
               :jersey      (:Jersey_Number r)
               :height      (:Height r)
               :weight      (:Weight r)
               :value       (:Value r)
               :foot        (:Preferred_Foot r)}))
       (filter :name)))

;; ---------------------------------------------------------------------------
;; Dedup & assembly
;; ---------------------------------------------------------------------------

(def ^:private brasileirao-source-priority
  "Brasileirão appears in three datasets with heavy overlap (Brasileirao_Matches
   2012-2022, novo_campeonato 2003-2019, BR-Football Série A). Each uses a
   *different* naming convention for the same clubs (\"Atlético-MG\" vs
   \"Atlético Mineiro\"), so fuzzy-key merging across sources is unreliable and
   produces inflated league tables. Instead we pick ONE authoritative source
   per season, preferring the cleaner suffix-tagged feeds. This guarantees a
   single internally-consistent naming convention per season -> correct tables."
  {"Brasileirao_Matches"        0
   "novo_campeonato_brasileiro" 1
   "BR-Football-Dataset"        2})

(defn- dedupe-brasileirao
  "Collapse canonical \"Brasileirão\" matches to a single source per season
   (see brasileirao-source-priority). Other competitions are left untouched."
  [matches]
  (let [brasil? #(= "Brasileirão" (:competition %))
        canon   (filter brasil? matches)
        others  (remove brasil? matches)
        chosen  (mapcat
                 (fn [[_season ms]]
                   (let [best (->> ms
                                   (map :source)
                                   distinct
                                   (sort-by #(get brasileirao-source-priority % 99))
                                   first)]
                     (filter #(= best (:source %)) ms)))
                 (group-by :season canon))]
    (concat chosen others)))

(defn- build-db []
  (let [matches (-> (concat (load-brasileirao)
                            (load-cup)
                            (load-libertadores)
                            (load-historical)
                            (load-br-football))
                    dedupe-brasileirao
                    vec)
        players (vec (load-players))]
    {:matches  matches
     :players  players}))

;; Memoized singleton so the CSVs are parsed at most once per process.
(defonce ^:private db-cache (atom nil))

(defn db
  "Return the loaded knowledge graph, parsing the CSVs on first access."
  []
  (or @db-cache
      (reset! db-cache (build-db))))

(defn load-db!
  "Force a (re)load of the database. Returns the db map."
  []
  (reset! db-cache (build-db)))

(defn matches [] (:matches (db)))
(defn players [] (:players (db)))
