(ns brazilian-soccer-mcp.data
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer-mcp.normalization :as norm]
            [brazilian-soccer-mcp.dates :as dates]))

(defn load-csv
  "Loads a CSV file, returning a sequence of row maps (header → value)."
  [path]
  (with-open [reader (io/reader path :encoding "UTF-8")]
    (let [rows (csv/read-csv reader)
          ;; strip BOM from first header if present
          headers (mapv #(str/replace % "﻿" "") (first rows))
          data-rows (rest rows)]
      (doall (map (fn [row] (zipmap headers row)) data-rows)))))

(defn parse-int [s]
  (when (and s (not (str/blank? s)))
    (try (Integer/parseInt (str/trim s)) (catch Exception _ nil))))

(defn normalize-competition
  "Maps various competition name spellings to canonical keys."
  [t]
  (let [tl (str/lower-case (or t ""))]
    (cond
      (or (str/includes? tl "série a") (str/includes? tl "serie a")) "brasileirao"
      (str/includes? tl "copa do brasil") "copa-do-brasil"
      (str/includes? tl "libertadores") "libertadores"
      :else t)))

(defn parse-float->int [s]
  (when (and s (not (str/blank? s)))
    (try (int (Double/parseDouble (str/trim s))) (catch Exception _ nil))))

(defn parse-brasileirao-row [row]
  {:competition   "brasileirao"
   :home-team     (norm/normalize-team (get row "home_team"))
   :home-team-raw (get row "home_team")
   :home-state    (get row "home_team_state")
   :away-team     (norm/normalize-team (get row "away_team"))
   :away-team-raw (get row "away_team")
   :away-state    (get row "away_team_state")
   :home-goal     (parse-int (get row "home_goal"))
   :away-goal     (parse-int (get row "away_goal"))
   :season        (parse-int (get row "season"))
   :round         (parse-int (get row "round"))
   :date          (dates/parse-date (get row "datetime"))
   :datetime-raw  (get row "datetime")})

(defn parse-cup-row [row]
  {:competition   "copa-do-brasil"
   :round         (get row "round")
   :home-team     (norm/normalize-team (get row "home_team"))
   :home-team-raw (get row "home_team")
   :away-team     (norm/normalize-team (get row "away_team"))
   :away-team-raw (get row "away_team")
   :home-goal     (parse-int (get row "home_goal"))
   :away-goal     (parse-int (get row "away_goal"))
   :season        (parse-int (get row "season"))
   :date          (dates/parse-date (get row "datetime"))
   :datetime-raw  (get row "datetime")})

(defn parse-libertadores-row [row]
  {:competition   "libertadores"
   :home-team     (norm/normalize-team (get row "home_team"))
   :home-team-raw (get row "home_team")
   :away-team     (norm/normalize-team (get row "away_team"))
   :away-team-raw (get row "away_team")
   :home-goal     (parse-int (get row "home_goal"))
   :away-goal     (parse-int (get row "away_goal"))
   :season        (parse-int (get row "season"))
   :stage         (get row "stage")
   :date          (dates/parse-date (get row "datetime"))
   :datetime-raw  (get row "datetime")})

(defn parse-br-football-row [row]
  (let [home-raw (get row "home")
        home-normalized (or (norm/canonical-name home-raw) home-raw)
        away-raw (get row "away")
        away-normalized (or (norm/canonical-name away-raw) away-raw)
        date-str (get row "date")]
    {:competition  (normalize-competition (get row "tournament"))
     :tournament   (get row "tournament")
     :home-team    home-normalized
     :home-team-raw home-raw
     :away-team    away-normalized
     :away-team-raw away-raw
     :home-goal    (parse-float->int (get row "home_goal"))
     :away-goal    (parse-float->int (get row "away_goal"))
     :home-corner  (parse-float->int (get row "home_corner"))
     :away-corner  (parse-float->int (get row "away_corner"))
     :home-shots   (parse-float->int (get row "home_shots"))
     :away-shots   (parse-float->int (get row "away_shots"))
     :ht-result    (get row "ht_result")
     :at-result    (get row "at_result")
     :total-corners (parse-float->int (get row "total_corners"))
     :season       (dates/extract-year date-str)
     :date         (dates/parse-date date-str)
     :datetime-raw date-str}))

(defn parse-historico-row [row]
  {:competition   "brasileirao-historico"
   :home-team     (norm/normalize-team (get row "Equipe_mandante"))
   :home-team-raw (get row "Equipe_mandante")
   :home-state    (get row "Mandante_UF")
   :away-team     (norm/normalize-team (get row "Equipe_visitante"))
   :away-team-raw (get row "Equipe_visitante")
   :away-state    (get row "Visitante_UF")
   :home-goal     (parse-int (get row "Gols_mandante"))
   :away-goal     (parse-int (get row "Gols_visitante"))
   :season        (parse-int (get row "Ano"))
   :round         (parse-int (get row "Rodada"))
   :winner        (get row "Vencedor")
   :arena         (get row "Arena")
   :date          (dates/parse-date (get row "Data"))
   :datetime-raw  (get row "Data")
   :match-id      (get row "ID")})

(defn parse-fifa-row [row]
  {:id          (str/trim (get row "" (get row "ID" "")))
   :name        (get row "Name")
   :age         (parse-int (get row "Age"))
   :nationality (get row "Nationality")
   :overall     (parse-int (get row "Overall"))
   :potential   (parse-int (get row "Potential"))
   :club        (get row "Club")
   :position    (get row "Position")
   :jersey      (get row "Jersey Number")
   :height      (get row "Height")
   :weight      (get row "Weight")})

;; Data store - loaded once at startup
(def ^:private db (atom nil))

(defn load-all-data!
  "Loads all CSV datasets from the given base directory. Returns the db atom."
  [data-dir]
  (let [brasileirao  (mapv parse-brasileirao-row
                           (load-csv (str data-dir "/Brasileirao_Matches.csv")))
        copa-brasil  (mapv parse-cup-row
                           (load-csv (str data-dir "/Brazilian_Cup_Matches.csv")))
        libertadores (mapv parse-libertadores-row
                           (load-csv (str data-dir "/Libertadores_Matches.csv")))
        br-football  (mapv parse-br-football-row
                           (load-csv (str data-dir "/BR-Football-Dataset.csv")))
        historico    (mapv parse-historico-row
                           (load-csv (str data-dir "/novo_campeonato_brasileiro.csv")))
        fifa         (mapv parse-fifa-row
                           (load-csv (str data-dir "/fifa_data.csv")))]
    (reset! db {:brasileirao  brasileirao
                :copa-brasil  copa-brasil
                :libertadores libertadores
                :br-football  br-football
                :historico    historico
                :fifa         fifa
                :all-matches  (concat brasileirao copa-brasil libertadores
                                      br-football historico)})))

(defn get-db [] @db)

(defn all-matches []  (get (get-db) :all-matches []))
(defn brasileirao []  (get (get-db) :brasileirao []))
(defn copa-brasil []  (get (get-db) :copa-brasil []))
(defn libertadores [] (get (get-db) :libertadores []))
(defn br-football []  (get (get-db) :br-football []))
(defn historico []    (get (get-db) :historico []))
(defn fifa-players [] (get (get-db) :fifa []))
