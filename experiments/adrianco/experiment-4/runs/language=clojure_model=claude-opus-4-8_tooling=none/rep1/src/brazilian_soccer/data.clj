(ns brazilian-soccer.data
  "=============================================================================
   Brazilian Soccer MCP Server - Data Loading & Knowledge Graph
   =============================================================================

   CONTEXT
     Loads the six provided Kaggle CSV files into a single in-memory knowledge
     graph. Every match from every file is normalized into one uniform schema
     so downstream queries never need to care which file a row came from.

     The graph nodes are:
       Match        - a single game (unified schema below)
       Team         - derived from match home/away teams
       Competition  - Brasileirão Série A / B / C, Copa do Brasil, Libertadores
       Player       - FIFA player records

     Relationships are expressed implicitly through shared canonical keys
     (e.g. a Team node's :key matches a Match's :home-key / :away-key, and a
     Player's :club-key can match a Team :key) - this is the lightweight,
     dependency-free equivalent of edges in a property graph such as Neo4j.

   UNIFIED MATCH SCHEMA
     {:competition  \"Brasileirão Série A\"   ; canonical competition label
      :season       2019                      ; integer year
      :round        \"22\"                     ; round/stage label (string|nil)
      :stage        \"group stage\"            ; tournament stage (Libertadores)
      :date         \"2019-08-11\"             ; ISO date (or nil)
      :home         \"Flamengo\"               ; cleaned display name
      :away         \"Fluminense\"
      :home-key     \"flamengo\"               ; canonical lookup key
      :away-key     \"fluminense\"
      :home-goal    2                          ; integer (or nil)
      :away-goal    1
      :stats        {...}                      ; optional extended stats
      :source       \"Brasileirao_Matches.csv\"}

   PUBLIC API
     load-database         - read all CSVs, return a {:matches :players ...} db
     default-data-dir      - \"data/kaggle\"
     competition-of-file   - map a filename to its competition label
   ============================================================================="
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer.normalize :as norm]))

(def default-data-dir "data/kaggle")

;; ----------------------------------------------------------------------------
;; CSV reading helpers
;; ----------------------------------------------------------------------------

(defn- strip-bom
  "Remove a leading UTF-8 BOM from a header cell if present."
  [s]
  (if (and s (.startsWith ^String s "﻿"))
    (subs s 1)
    s))

(defn read-csv-maps
  "Read a CSV file into a lazy-realized vector of maps keyed by header string.
   Reads as UTF-8 and strips a BOM from the first header cell."
  [path]
  (with-open [r (io/reader path :encoding "UTF-8")]
    (let [rows (csv/read-csv r)
          header (mapv strip-bom (first rows))]
      (mapv (fn [row] (zipmap header row)) (rest rows)))))

(defn- mk-match
  "Build a unified match map from already-extracted, cleaned fields."
  [{:keys [competition season round stage date home away home-goal away-goal
           stats source]}]
  {:competition competition
   :season      (norm/parse-int season)
   :round       (when-not (norm/blank? round) (str/trim (str round)))
   :stage       (when-not (norm/blank? stage) (str/trim (str stage)))
   :date        (norm/parse-date date)
   :home        (norm/clean-team-name home)
   :away        (norm/clean-team-name away)
   :home-key    (norm/canonical-key home)
   :away-key    (norm/canonical-key away)
   :home-goal   (norm/parse-int home-goal)
   :away-goal   (norm/parse-int away-goal)
   :stats       (not-empty stats)
   :source      source})

;; ----------------------------------------------------------------------------
;; Per-file loaders (each maps a file's columns to the unified schema)
;; ----------------------------------------------------------------------------

(defn- load-brasileirao [path]
  (mapv (fn [r]
          (mk-match {:competition "Brasileirão Série A"
                     :season    (get r "season")
                     :round     (get r "round")
                     :date      (get r "datetime")
                     :home      (get r "home_team")
                     :away      (get r "away_team")
                     :home-goal (get r "home_goal")
                     :away-goal (get r "away_goal")
                     :source    "Brasileirao_Matches.csv"}))
        (read-csv-maps path)))

(defn- load-cup [path]
  (mapv (fn [r]
          (mk-match {:competition "Copa do Brasil"
                     :season    (get r "season")
                     :round     (get r "round")
                     :date      (get r "datetime")
                     :home      (get r "home_team")
                     :away      (get r "away_team")
                     :home-goal (get r "home_goal")
                     :away-goal (get r "away_goal")
                     :source    "Brazilian_Cup_Matches.csv"}))
        (read-csv-maps path)))

(defn- load-libertadores [path]
  (mapv (fn [r]
          (mk-match {:competition "Copa Libertadores"
                     :season    (get r "season")
                     :stage     (get r "stage")  ; round intentionally left blank (stage carries it)
                     :date      (get r "datetime")
                     :home      (get r "home_team")
                     :away      (get r "away_team")
                     :home-goal (get r "home_goal")
                     :away-goal (get r "away_goal")
                     :source    "Libertadores_Matches.csv"}))
        (read-csv-maps path)))

(def ^:private br-football-competition
  "Map the BR-Football-Dataset 'tournament' column to a canonical label."
  {"Serie A" "Brasileirão Série A"
   "Serie B" "Brasileirão Série B"
   "Serie C" "Brasileirão Série C"
   "Copa do Brasil" "Copa do Brasil"})

(defn- load-br-football [path]
  (mapv (fn [r]
          (let [tourn (get r "tournament")]
            (mk-match {:competition (get br-football-competition tourn tourn)
                       :season    (norm/year-of (get r "date"))
                       :date      (get r "date")
                       :home      (get r "home")
                       :away      (get r "away")
                       :home-goal (get r "home_goal")
                       :away-goal (get r "away_goal")
                       :stats     {:home-corner (norm/parse-int (get r "home_corner"))
                                   :away-corner (norm/parse-int (get r "away_corner"))
                                   :home-shots  (norm/parse-int (get r "home_shots"))
                                   :away-shots  (norm/parse-int (get r "away_shots"))
                                   :home-attack (norm/parse-int (get r "home_attack"))
                                   :away-attack (norm/parse-int (get r "away_attack"))
                                   :ht-result   (get r "ht_result")
                                   :at-result   (get r "at_result")}
                       :source    "BR-Football-Dataset.csv"})))
        (read-csv-maps path)))

(defn- load-novo [path]
  (mapv (fn [r]
          (mk-match {:competition "Brasileirão Série A"
                     :season    (get r "Ano")
                     :round     (get r "Rodada")
                     :date      (get r "Data")
                     :home      (get r "Equipe_mandante")
                     :away      (get r "Equipe_visitante")
                     :home-goal (get r "Gols_mandante")
                     :away-goal (get r "Gols_visitante")
                     :stats     {:arena (get r "Arena")
                                 :winner (get r "Vencedor")}
                     :source    "novo_campeonato_brasileiro.csv"}))
        (read-csv-maps path)))

(defn- load-players [path]
  (->> (read-csv-maps path)
       (mapv (fn [r]
               {:id          (norm/parse-int (get r "ID"))
                :name        (get r "Name")
                :age         (norm/parse-int (get r "Age"))
                :nationality (get r "Nationality")
                :overall     (norm/parse-int (get r "Overall"))
                :potential   (norm/parse-int (get r "Potential"))
                :club        (get r "Club")
                :club-key    (norm/canonical-key (get r "Club"))
                :position    (get r "Position")
                :jersey      (get r "Jersey Number")
                :height      (get r "Height")
                :weight      (get r "Weight")
                :name-key    (norm/normalize-text (get r "Name"))
                :nat-key     (norm/normalize-text (get r "Nationality"))}))))

(defn competition-of-file
  "The competition label primarily associated with a data file (best effort)."
  [filename]
  (case filename
    "Brasileirao_Matches.csv"        "Brasileirão Série A"
    "Brazilian_Cup_Matches.csv"      "Copa do Brasil"
    "Libertadores_Matches.csv"       "Copa Libertadores"
    "novo_campeonato_brasileiro.csv" "Brasileirão Série A"
    "BR-Football-Dataset.csv"        "Mixed (Serie A/B/C, Copa do Brasil)"
    "Unknown"))

;; ----------------------------------------------------------------------------
;; Top-level loader
;; ----------------------------------------------------------------------------

(defn- has-accent?
  "True when s contains characters that differ from their accent-folded form
   (i.e. it carries diacritics like São / Grêmio)."
  [s]
  (and s (not= s (norm/fold-accents s))))

(defn- canonical-display-names
  "Across ALL raw matches, pick the best display name for each canonical team
   key. The same club is spelled inconsistently between files (\"Grêmio\" vs
   \"Gremio\", \"Atlético\" vs \"Atletico\"); we prefer an accented spelling and,
   among equally-accented candidates, the most frequently occurring one.
   Returns {canonical-key display-name}."
  [matches]
  (let [freqs (reduce (fn [acc {:keys [home away home-key away-key]}]
                        (-> acc
                            (update-in [home-key home] (fnil inc 0))
                            (update-in [away-key away] (fnil inc 0))))
                      {} matches)]
    (into {}
          (map (fn [[k name->n]]
                 [k (->> name->n
                         (sort-by (fn [[name n]] [(if (has-accent? name) 1 0) n]) #(compare %2 %1))
                         ffirst)]))
          freqs)))

(defn- apply-canonical-names
  "Rewrite each match's :home/:away display name to the canonical spelling."
  [matches names]
  (mapv (fn [m]
          (assoc m
                 :home (get names (:home-key m) (:home m))
                 :away (get names (:away-key m) (:away m))))
        matches))

(defn- dedupe-matches
  "Drop exact-duplicate rows (same competition, season, date, both teams and
   both scores). With one authoritative source per competition (see
   load-database) cross-source overlap is already eliminated, so this only
   removes genuine repeated rows within a file - it never collapses two
   legitimately distinct fixtures."
  [matches]
  (let [k (juxt :competition :season :date :home-key :away-key :home-goal :away-goal)]
    (->> matches
         (reduce (fn [[seen acc] m]
                   (let [kk (k m)]
                     (if (contains? seen kk)
                       [seen acc]
                       [(conj seen kk) (conj acc m)])))
                 [#{} []])
         second)))

(defn- derive-teams
  "Build the set of Team nodes from all match endpoints:
   {canonical-key {:key k :name display-name :competitions #{...}}}."
  [matches]
  (reduce
   (fn [acc {:keys [home away home-key away-key competition]}]
     (-> acc
         (update home-key (fn [t]
                            (-> (or t {:key home-key :name home :competitions #{}})
                                (update :competitions conj competition))))
         (update away-key (fn [t]
                            (-> (or t {:key away-key :name away :competitions #{}})
                                (update :competitions conj competition))))))
   {}
   matches))

(defn load-database
  "Load all available CSVs under data-dir (default \"data/kaggle\") into the
   knowledge graph. Missing files are skipped with a warning on stderr.

   Returns:
     {:matches [unified-match ...]
      :players [player ...]
      :teams   {key team-node ...}
      :data-dir \"...\"}"
  ([] (load-database default-data-dir))
  ([data-dir]
   (let [file  (fn [f] (io/file data-dir f))
         exists? (fn [f] (.exists ^java.io.File (file f)))
         load-if (fn [f loader] (if (exists? f)
                                  (loader (file f))
                                  (do (binding [*out* *err*]
                                        (println (str "WARN: missing data file " f " in " data-dir)))
                                      [])))
         ;; --- Single authoritative source per competition (no overlap) ------
         ;; Brasileirão Série A is split between two files that overlap in
         ;; 2012-2019. We take the modern, complete file as the primary source
         ;; and use the historical file ONLY for the earlier seasons it alone
         ;; covers, so no season is double-counted.
         brasileirao (load-if "Brasileirao_Matches.csv" load-brasileirao)
         covered     (set (keep :season brasileirao))
         historical  (->> (load-if "novo_campeonato_brasileiro.csv" load-novo)
                          (remove #(contains? covered (:season %))))
         cup          (load-if "Brazilian_Cup_Matches.csv" load-cup)
         libertadores (load-if "Libertadores_Matches.csv" load-libertadores)
         ;; BR-Football's Série A / Copa do Brasil rows duplicate the primary
         ;; sources above (with different team spellings), so we keep only the
         ;; Série B / Série C rows for which it is the sole source.
         br-football  (->> (load-if "BR-Football-Dataset.csv" load-br-football)
                           (filter #(#{"Brasileirão Série B" "Brasileirão Série C"} (:competition %))))
         raw     (concat brasileirao historical cup libertadores br-football)
         matches (-> raw
                     (apply-canonical-names (canonical-display-names raw))
                     dedupe-matches)
         players (if (exists? "fifa_data.csv")
                   (load-players (file "fifa_data.csv"))
                   (do (binding [*out* *err*]
                         (println "WARN: missing fifa_data.csv"))
                       []))]
     {:matches matches
      :players players
      :teams   (derive-teams matches)
      :data-dir data-dir})))
