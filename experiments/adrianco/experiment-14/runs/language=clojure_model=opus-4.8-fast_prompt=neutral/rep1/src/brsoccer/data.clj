;; =============================================================================
;; brsoccer.data
;;
;; Context:
;;   Loads the six bundled Kaggle CSV files into a single in-memory knowledge
;;   graph.  No external database is required -- "Neo4j-style" entities and
;;   relationships are represented as plain Clojure maps/indexes, which is enough
;;   to satisfy every query in the spec and keeps the project dependency-free and
;;   fast (full load is well under a second).
;;
;;   The graph (see `load-graph`) contains:
;;     :matches   -> vector of normalized match maps, one per row, deduplicated
;;                   so overlapping Brasileirao sources are not double-counted.
;;     :players   -> vector of normalized FIFA player maps.
;;     :teams     -> {team-key {:name display-name :key k}}  (node table)
;;     :by-team   -> {team-key [match ...]}                  (adjacency index)
;;
;;   Each match map is the canonical edge:
;;     {:competition :season :date :round :stage :source
;;      :home :home-key :away :away-key :home-goal :away-goal ...}
;;
;;   Loading is cached in an atom so repeated tool calls are cheap.
;; =============================================================================
(ns brsoccer.data
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brsoccer.normalize :as n]))

(def ^:dynamic *data-dir*
  "Directory holding the Kaggle CSVs. Overridable via the BRSOCCER_DATA_DIR env."
  (or (System/getenv "BRSOCCER_DATA_DIR") "data/kaggle"))

;; ---------------------------------------------------------------------------
;; CSV helpers
;; ---------------------------------------------------------------------------

(defn- read-csv
  "Read a CSV file into a seq of maps keyed by header string. Strips a leading
   UTF-8 BOM from the first header cell. Returns nil if the file is missing."
  [filename]
  (let [f (io/file *data-dir* filename)]
    (when (.exists f)
      (with-open [r (io/reader f :encoding "UTF-8")]
        (let [[header & rows] (csv/read-csv r)
              header (vec (cons (str/replace (first header) "﻿" "") (rest header)))]
          (doall (map #(zipmap header %) rows)))))))

(defn- match-map
  "Build a canonical match edge map from already-extracted fields."
  [{:keys [competition season date round stage home away home-goal away-goal source]}]
  (let [hg (n/parse-int home-goal)
        ag (n/parse-int away-goal)]
    {:competition competition
     :season      (or (n/parse-int season) (n/year-of date))
     :date        date
     :round       round
     :stage       stage
     :source      source
     :home        (n/clean-name home)
     :away        (n/clean-name away)
     :home-key    (n/team-key home)
     :away-key    (n/team-key away)
     :home-goal   hg
     :away-goal   ag
     :result      (cond (nil? hg) nil
                        (> hg ag) :home
                        (< hg ag) :away
                        :else     :draw)}))

(defn- valid-match? [m]
  (and (:home-key m) (:away-key m)
       (:home-goal m) (:away-goal m)
       (not= (:home-key m) (:away-key m))))

;; ---------------------------------------------------------------------------
;; Per-file loaders -> seq of canonical match maps
;; ---------------------------------------------------------------------------

(defn- load-brasileirao []
  (for [r (read-csv "Brasileirao_Matches.csv")]
    (match-map {:competition "Brasileirão Série A" :source "Brasileirao_Matches"
                :season (get r "season") :round (get r "round")
                :date (n/parse-date (get r "datetime"))
                :home (get r "home_team") :away (get r "away_team")
                :home-goal (get r "home_goal") :away-goal (get r "away_goal")})))

(defn- load-cup []
  (for [r (read-csv "Brazilian_Cup_Matches.csv")]
    (match-map {:competition "Copa do Brasil" :source "Brazilian_Cup_Matches"
                :season (get r "season") :round (get r "round")
                :date (n/parse-date (get r "datetime"))
                :home (get r "home_team") :away (get r "away_team")
                :home-goal (get r "home_goal") :away-goal (get r "away_goal")})))

(defn- load-libertadores []
  (for [r (read-csv "Libertadores_Matches.csv")]
    (match-map {:competition "Copa Libertadores" :source "Libertadores_Matches"
                :season (get r "season") :stage (get r "stage")
                :date (n/parse-date (get r "datetime"))
                :home (get r "home_team") :away (get r "away_team")
                :home-goal (get r "home_goal") :away-goal (get r "away_goal")})))

(def ^:private br-football-comp
  {"Serie A" "Brasileirão Série A"
   "Serie B" "Brasileirão Série B"
   "Serie C" "Brasileirão Série C"
   "Copa do Brasil" "Copa do Brasil"})

(defn- load-br-football []
  (for [r (read-csv "BR-Football-Dataset.csv")
        :let [date (n/parse-date (get r "date"))]]
    (match-map {:competition (get br-football-comp (get r "tournament") (get r "tournament"))
                :source "BR-Football-Dataset"
                :season (n/year-of date) :date date
                :home (get r "home") :away (get r "away")
                :home-goal (get r "home_goal") :away-goal (get r "away_goal")})))

(defn- load-novo []
  (for [r (read-csv "novo_campeonato_brasileiro.csv")]
    (match-map {:competition "Brasileirão Série A" :source "novo_campeonato"
                :season (get r "Ano") :round (get r "Rodada")
                :date (n/parse-date (get r "Data"))
                :home (get r "Equipe_mandante") :away (get r "Equipe_visitante")
                :home-goal (get r "Gols_mandante") :away-goal (get r "Gols_visitante")})))

;; ---------------------------------------------------------------------------
;; Players
;; ---------------------------------------------------------------------------

(defn- player-map [r]
  {:id          (n/parse-int (get r "ID"))
   :name        (get r "Name")
   :age         (n/parse-int (get r "Age"))
   :nationality (get r "Nationality")
   :overall     (n/parse-int (get r "Overall"))
   :potential   (n/parse-int (get r "Potential"))
   :club        (n/clean-name (get r "Club"))
   :club-key    (n/team-key (get r "Club"))
   :position    (get r "Position")
   :jersey      (n/parse-int (get r "Jersey Number"))
   :height      (get r "Height")
   :weight      (get r "Weight")
   :foot        (get r "Preferred Foot")
   :value       (get r "Value")
   :wage        (get r "Wage")
   :name-key    (some-> (get r "Name") n/strip-accents str/lower-case)
   :nat-key     (some-> (get r "Nationality") n/strip-accents str/lower-case)})

(defn- load-players []
  (->> (read-csv "fifa_data.csv")
       (map player-map)
       (filter :name)
       vec))

;; ---------------------------------------------------------------------------
;; Graph assembly
;; ---------------------------------------------------------------------------

(defn- dedup-matches
  "Several sources overlap (e.g. Brasileirão 2012-2019 appears in three files,
   each with slightly different date strings). Within one competition+season a
   given ORDERED (home,away) pairing occurs at most once across these formats
   (league double round-robin -> each pair home once; knockout two-leg ties swap
   venues -> distinct ordered pairs), so we collapse on that key WITHOUT the date
   to avoid double-counting the same fixture recorded by multiple datasets."
  [matches]
  (->> matches
       (reduce (fn [[seen acc] m]
                 (let [k [(:competition m) (:season m)
                          (:home-key m) (:away-key m)]]
                   (if (contains? seen k)
                     [seen acc]
                     [(conj seen k) (conj acc m)])))
               [#{} []])
       second))

(defn- build-teams
  "Node table: team-key -> {:key :name} where :name is the most common cleaned
   display form seen for that key across all matches."
  [matches]
  (let [pairs (mapcat (juxt (juxt :home-key :home)
                            (juxt :away-key :away))
                      matches)]
    (->> pairs
         (filter first)
         (group-by first)
         (reduce-kv
           (fn [acc k entries]
             (let [name (->> entries (map second) (remove str/blank?)
                             frequencies (sort-by (comp - val)) ffirst)]
               (assoc acc k {:key k :name (or name k)})))
           {}))))

(defn load-graph
  "Read every dataset and assemble the in-memory knowledge graph (see ns doc)."
  []
  (let [matches (-> (concat (load-brasileirao) (load-cup) (load-libertadores)
                            (load-br-football) (load-novo))
                    (->> (filter valid-match?))
                    dedup-matches
                    vec)
        teams   (build-teams matches)
        by-team (reduce (fn [acc m]
                          (-> acc
                              (update (:home-key m) (fnil conj []) m)
                              (update (:away-key m) (fnil conj []) m)))
                        {} matches)]
    {:matches matches
     :players (load-players)
     :teams   teams
     :by-team by-team}))

(defonce ^:private graph-cache (atom nil))

(defn graph
  "Return the cached knowledge graph, loading it on first use."
  []
  (or @graph-cache (reset! graph-cache (load-graph))))

(defn reset-cache! [] (reset! graph-cache nil))
