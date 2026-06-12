(ns brazilian-soccer.data
  "Loading layer for the Brazilian Soccer knowledge graph.

  Each of the six provided Kaggle CSV files has its own column layout. This
  namespace reads them and projects every match onto a single unified schema:

    {:competition  \"Brasileirão\"        ; canonical competition label
     :season       2019                   ; integer year
     :round        \"20\"                  ; round / stage label (string)
     :stage        nil                    ; knockout stage when applicable
     :date         #object[LocalDate ...] ; parsed match date (may be nil)
     :home-team    \"Flamengo\"            ; suffix-stripped display name
     :away-team    \"Grêmio\"
     :home-goal    5
     :away-goal    0
     :source       \"Brasileirao_Matches.csv\"}

  Players from the FIFA dataset are projected onto:

    {:id 158023 :name \"Neymar Jr\" :age 27 :nationality \"Brazil\"
     :overall 92 :potential 93 :club \"Paris Saint-Germain\"
     :position \"LW\" :jersey 10}

  `load-db` returns {:matches [...] :players [...]} and is the single entry
  point the query layer builds on."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer.normalize :as norm]))

(defn read-csv
  "Read a CSV file into a vector of maps keyed by the (BOM-stripped) header row."
  [path]
  (with-open [r (io/reader path)]
    (let [[header & rows] (csv/read-csv r)
          header (mapv #(str/replace % "﻿" "") header)]
      (mapv #(zipmap header %) (vec rows)))))

(defn- match
  "Build a unified match map, dropping rows without both goal values."
  [{:keys [competition season round stage date home away home-goal away-goal source]}]
  (let [hg (norm/parse-int home-goal)
        ag (norm/parse-int away-goal)]
    (when (and (some? hg) (some? ag)
               (not (str/blank? (str home)))
               (not (str/blank? (str away))))
      {:competition competition
       :season (norm/parse-int season)
       :round (some-> round str/trim not-empty)
       :stage (some-> stage str/trim not-empty)
       :date (norm/parse-date date)
       :home-team (norm/clean-team home)
       :away-team (norm/clean-team away)
       ;; suffix-preserving names so clubs differing only by state stay distinct
       :home-raw (str/trim (str home))
       :away-raw (str/trim (str away))
       :home-goal hg
       :away-goal ag
       :source source})))

(defn- load-brasileirao [dir]
  (let [src "Brasileirao_Matches.csv"]
    (keep #(match {:competition "Brasileirão"
                   :season (get % "season")
                   :round (get % "round")
                   :date (get % "datetime")
                   :home (get % "home_team")
                   :away (get % "away_team")
                   :home-goal (get % "home_goal")
                   :away-goal (get % "away_goal")
                   :source src})
          (read-csv (str dir "/" src)))))

(defn- load-cup [dir]
  (let [src "Brazilian_Cup_Matches.csv"]
    (keep #(match {:competition "Copa do Brasil"
                   :season (get % "season")
                   :round (get % "round")
                   :stage (get % "round")
                   :date (get % "datetime")
                   :home (get % "home_team")
                   :away (get % "away_team")
                   :home-goal (get % "home_goal")
                   :away-goal (get % "away_goal")
                   :source src})
          (read-csv (str dir "/" src)))))

(defn- load-libertadores [dir]
  (let [src "Libertadores_Matches.csv"]
    (keep #(match {:competition "Libertadores"
                   :season (get % "season")
                   :round (get % "stage")
                   :stage (get % "stage")
                   :date (get % "datetime")
                   :home (get % "home_team")
                   :away (get % "away_team")
                   :home-goal (get % "home_goal")
                   :away-goal (get % "away_goal")
                   :source src})
          (read-csv (str dir "/" src)))))

(defn- competition-from-tournament
  "Map the BR-Football-Dataset `tournament` column onto a canonical label."
  [t]
  (case (str/lower-case (str t))
    "copa do brasil" "Copa do Brasil"
    (str t)))

(defn- load-br-dataset [dir]
  (let [src "BR-Football-Dataset.csv"]
    (keep #(match {:competition (competition-from-tournament (get % "tournament"))
                   :season (some-> (get % "date") (subs 0 4))
                   :date (get % "date")
                   :home (get % "home")
                   :away (get % "away")
                   :home-goal (get % "home_goal")
                   :away-goal (get % "away_goal")
                   :source src})
          (read-csv (str dir "/" src)))))

(defn- load-novo [dir]
  (let [src "novo_campeonato_brasileiro.csv"]
    (keep #(match {:competition "Brasileirão"
                   :season (get % "Ano")
                   :round (get % "Rodada")
                   :date (get % "Data")
                   :home (get % "Equipe_mandante")
                   :away (get % "Equipe_visitante")
                   :home-goal (get % "Gols_mandante")
                   :away-goal (get % "Gols_visitante")
                   :source src})
          (read-csv (str dir "/" src)))))

(defn- player [row]
  {:id (norm/parse-int (get row "ID"))
   :name (some-> (get row "Name") str/trim)
   :age (norm/parse-int (get row "Age"))
   :nationality (some-> (get row "Nationality") str/trim)
   :overall (norm/parse-int (get row "Overall"))
   :potential (norm/parse-int (get row "Potential"))
   :club (some-> (get row "Club") str/trim)
   :position (some-> (get row "Position") str/trim)
   :jersey (norm/parse-int (get row "Jersey Number"))})

(defn- load-players [dir]
  (->> (read-csv (str dir "/fifa_data.csv"))
       (map player)
       (filter :name)))

;; Lower number = preferred when two sources have the same row count for a
;; season. The dedicated single-competition files use the cleanest, most
;; consistent team naming, so they win ties over the broad datasets.
(def ^:private source-priority
  {"Brasileirao_Matches.csv" 0
   "Brazilian_Cup_Matches.csv" 0
   "Libertadores_Matches.csv" 0
   "BR-Football-Dataset.csv" 1
   "novo_campeonato_brasileiro.csv" 1})

(defn select-best-source
  "Several files overlap (e.g. Brasileirão 2012-2019 appears in both
  novo_campeonato_brasileiro and Brasileirao_Matches; Copa do Brasil appears in
  both Brazilian_Cup_Matches and BR-Football-Dataset). Naive concatenation
  double-counts every overlapping match and inflates standings, records and
  averages.

  Rather than fuzzily matching individual fixtures across files (which the
  inconsistent team naming makes unreliable), we pick, for each
  (competition, season), the single source with the most rows — that one file
  is internally consistent — and drop the rest. Ties go to the lower-priority
  (dedicated) source."
  [matches]
  (->> (group-by (juxt :competition :season) matches)
       (mapcat (fn [[_ ms]]
                 (->> (group-by :source ms)
                      (sort-by (fn [[src rows]]
                                 [(- (count rows)) (source-priority src 9)]))
                      first
                      second)))))

(defn load-db
  "Load all match files and the player file under `dir` into an in-memory db:
  {:matches [...] :players [...]}. Matches duplicated across source files are
  collapsed."
  [dir]
  {:matches (vec (select-best-source (concat (load-brasileirao dir)
                                             (load-cup dir)
                                             (load-libertadores dir)
                                             (load-br-dataset dir)
                                             (load-novo dir))))
   :players (vec (load-players dir))})
