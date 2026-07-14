(ns brazilian-soccer-mcp.data
  "Load and normalize all CSV datasets for the Brazilian Soccer MCP server."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; CSV utilities
;; ---------------------------------------------------------------------------

(defn- parse-int [s]
  (when (and s (not (str/blank? s)))
    (try (Integer/parseInt (str/trim s))
         (catch Exception _ nil))))

(defn- parse-dbl [s]
  (when (and s (not (str/blank? s)))
    (try (Double/parseDouble (str/trim s))
         (catch Exception _ nil))))

(defn- read-csv-file [path]
  (with-open [reader (io/reader path :encoding "UTF-8")]
    (let [rows (csv/read-csv reader)
          headers (map (comp keyword str/trim) (first rows))
          data (rest rows)]
      (mapv (fn [row]
              (zipmap headers (map str/trim row)))
            data))))

;; ---------------------------------------------------------------------------
;; Date normalization
;; ---------------------------------------------------------------------------

(defn normalize-date
  "Return a yyyy-MM-dd string from various input formats."
  [s]
  (when (and s (not (str/blank? s)))
    (let [s (str/trim s)]
      (cond
        ;; ISO with time: 2012-05-19 18:30:00 or 2012-05-19T18:30:00
        (re-matches #"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}.*" s)
        (subs s 0 10)
        ;; ISO date only
        (re-matches #"\d{4}-\d{2}-\d{2}" s)
        s
        ;; Brazilian DD/MM/YYYY
        (re-matches #"\d{2}/\d{2}/\d{4}" s)
        (let [[d m y] (str/split s #"/")]
          (str y "-" m "-" d))
        :else s))))

;; ---------------------------------------------------------------------------
;; Loaders per dataset
;; ---------------------------------------------------------------------------

(defn- load-brasileirao [dir]
  (->> (read-csv-file (str dir "/Brasileirao_Matches.csv"))
       (mapv (fn [r]
               {:home-team  (:home_team r)
                :away-team  (:away_team r)
                :home-goal  (parse-int (:home_goal r))
                :away-goal  (parse-int (:away_goal r))
                :date       (normalize-date (:datetime r))
                :season     (parse-int (:season r))
                :round      (parse-int (:round r))
                :competition "brasileirao"}))))

(defn- load-cup [dir]
  (->> (read-csv-file (str dir "/Brazilian_Cup_Matches.csv"))
       (mapv (fn [r]
               {:home-team  (:home_team r)
                :away-team  (:away_team r)
                :home-goal  (parse-int (:home_goal r))
                :away-goal  (parse-int (:away_goal r))
                :date       (normalize-date (:datetime r))
                :season     (parse-int (:season r))
                :round      (:round r)
                :competition "copa-do-brasil"}))))

(defn- load-libertadores [dir]
  (->> (read-csv-file (str dir "/Libertadores_Matches.csv"))
       (mapv (fn [r]
               {:home-team  (:home_team r)
                :away-team  (:away_team r)
                :home-goal  (parse-int (:home_goal r))
                :away-goal  (parse-int (:away_goal r))
                :date       (normalize-date (:datetime r))
                :season     (parse-int (:season r))
                :stage      (:stage r)
                :competition "libertadores"}))))

(defn- normalize-br-competition [tournament]
  (let [t (str/lower-case (str tournament))]
    (cond
      (or (str/includes? t "serie a") (str/includes? t "brasileirao")) "brasileirao"
      (or (str/includes? t "copa do brasil") (str/includes? t "copa do brasil")) "copa-do-brasil"
      (str/includes? t "libertadores") "libertadores"
      :else t)))

(defn- load-br-football [dir]
  (->> (read-csv-file (str dir "/BR-Football-Dataset.csv"))
       (mapv (fn [r]
               (let [date (normalize-date (:date r))
                     year (when (and date (>= (count date) 4))
                            (parse-int (subs date 0 4)))]
                 {:home-team    (:home r)
                  :away-team    (:away r)
                  :home-goal    (parse-int (re-find #"\d+" (str (:home_goal r))))
                  :away-goal    (parse-int (re-find #"\d+" (str (:away_goal r))))
                  :date         date
                  :season       year
                  :home-corner  (parse-int (re-find #"\d+" (str (:home_corner r))))
                  :away-corner  (parse-int (re-find #"\d+" (str (:away_corner r))))
                  :home-shots   (parse-int (re-find #"\d+" (str (:home_shots r))))
                  :away-shots   (parse-int (re-find #"\d+" (str (:away_shots r))))
                  :competition  (normalize-br-competition (:tournament r))
                  :time         (:time r)})))))

(defn- load-historical [dir]
  (->> (read-csv-file (str dir "/novo_campeonato_brasileiro.csv"))
       (mapv (fn [r]
               {:home-team  (:Equipe_mandante r)
                :away-team  (:Equipe_visitante r)
                :home-goal  (parse-int (:Gols_mandante r))
                :away-goal  (parse-int (:Gols_visitante r))
                :date       (normalize-date (:Data r))
                :season     (parse-int (:Ano r))
                :round      (parse-int (:Rodada r))
                :arena      (:Arena r)
                :winner     (:Vencedor r)
                :competition "brasileirao"}))))

(defn- load-fifa [dir]
  (->> (read-csv-file (str dir "/fifa_data.csv"))
       (mapv (fn [r]
               {:id          (:ID r)
                :name        (:Name r)
                :age         (parse-int (:Age r))
                :nationality (:Nationality r)
                :overall     (parse-int (:Overall r))
                :potential   (parse-int (:Potential r))
                :club        (:Club r)
                :position    (:Position r)
                :jersey      (get r (keyword "Jersey Number"))
                :height      (:Height r)
                :weight      (:Weight r)
                :value       (:Value r)
                :wage        (:Wage r)}))))

;; ---------------------------------------------------------------------------
;; Public API
;; ---------------------------------------------------------------------------

(defn load-all-data
  "Load all 6 CSV datasets from the given directory. Returns a map of datasets."
  [data-dir]
  {:brasileirao-matches (load-brasileirao data-dir)
   :cup-matches         (load-cup data-dir)
   :libertadores-matches (load-libertadores data-dir)
   :br-football         (load-br-football data-dir)
   :historical-brasileirao (load-historical data-dir)
   :fifa-players        (load-fifa data-dir)})
