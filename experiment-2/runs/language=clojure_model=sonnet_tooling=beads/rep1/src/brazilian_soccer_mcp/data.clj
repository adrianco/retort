(ns brazilian-soccer-mcp.data
  "Loads and normalizes all 6 CSV datasets."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; Utilities
;; ---------------------------------------------------------------------------

(defn- strip-bom [s]
  (if (and s (str/starts-with? s "\uFEFF"))
    (subs s 1)
    s))

(defn read-csv-file
  "Returns seq of maps from a CSV file.  Handles BOM and UTF-8."
  [path]
  (with-open [rdr (io/reader path :encoding "UTF-8")]
    (let [rows (csv/read-csv rdr)
          [raw-header & data] rows
          header (map (comp keyword strip-bom) raw-header)]
      (mapv #(zipmap header %) data))))

;; ---------------------------------------------------------------------------
;; Team name normalisation
;; ---------------------------------------------------------------------------

(def ^:private state-suffixes
  #{"AC" "AL" "AP" "AM" "BA" "CE" "DF" "ES" "GO" "MA" "MT" "MS" "MG"
    "PA" "PB" "PR" "PE" "PI" "RJ" "RN" "RS" "RO" "RR" "SC" "SP" "SE" "TO"})

(defn normalize-team-name
  "Strip state suffix (e.g. '-SP', '- RJ') and trim."
  [name]
  (when (and name (not= "" (str/trim name)))
    (let [trimmed (str/trim name)
          ;; Remove trailing state suffix like '-SP' or '- SP'
          stripped (str/replace trimmed #"\s*-\s*([A-Z]{2})\s*$"
                                (fn [[_ state]]
                                  (if (state-suffixes state) "" (str "-" state))))]
      (-> stripped
          str/trim
          ;; normalise internal whitespace
          (str/replace #"\s+" " ")))))

(defn team-matches?
  "True if query string is a case-insensitive substring of the normalised team name."
  [query team-name]
  (when (and query team-name)
    (str/includes? (str/lower-case (normalize-team-name team-name))
                   (str/lower-case (str/trim query)))))

;; ---------------------------------------------------------------------------
;; Date parsing
;; ---------------------------------------------------------------------------

(defn parse-int
  "Parse integer safely, returning nil for blank/NA/non-numeric strings."
  [s]
  (when (and s (not= "" (str/trim s)) (not= "NA" (str/trim s)))
    (try (Integer/parseInt (str/trim s)) (catch Exception _ nil))))

(defn parse-double-as-int
  "Parse a string as double then truncate to int, handling NA/blank."
  [s]
  (when (and s (not= "" (str/trim s)) (not= "NA" (str/trim s)))
    (try (int (Double/parseDouble (str/trim s))) (catch Exception _ nil))))

(defn parse-date
  "Try to parse various date formats and return a java.time.LocalDate or nil."
  [s]
  (when (and s (not= "" (str/trim s)))
    (try
      (cond
        ;; ISO datetime: 2012-05-19 18:30:00 or 2012-05-19T18:30:00
        (re-matches #"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}.*" s)
        (java.time.LocalDate/parse (subs s 0 10))
        ;; ISO date: 2023-09-24
        (re-matches #"\d{4}-\d{2}-\d{2}" s)
        (java.time.LocalDate/parse s)
        ;; Brazilian DD/MM/YYYY
        (re-matches #"\d{2}/\d{2}/\d{4}" s)
        (java.time.LocalDate/parse s (java.time.format.DateTimeFormatter/ofPattern "dd/MM/yyyy"))
        :else nil)
      (catch Exception _ nil))))

;; ---------------------------------------------------------------------------
;; Individual dataset loaders
;; ---------------------------------------------------------------------------

(defn- data-path [filename]
  (str "data/kaggle/" filename))

(defn load-brasileirao-matches []
  (map (fn [row]
         {:competition "Brasileirao Serie A"
          :datetime    (:datetime row)
          :date        (parse-date (:datetime row))
          :home-team   (:home_team row)
          :away-team   (:away_team row)
          :home-team-norm (normalize-team-name (:home_team row))
          :away-team-norm (normalize-team-name (:away_team row))
          :home-goals  (parse-int (:home_goal row))
          :away-goals  (parse-int (:away_goal row))
          :season      (parse-int (:season row))
          :round       (:round row)})
       (read-csv-file (data-path "Brasileirao_Matches.csv"))))

(defn load-cup-matches []
  (map (fn [row]
         {:competition "Copa do Brasil"
          :datetime    (:datetime row)
          :date        (parse-date (:datetime row))
          :home-team   (:home_team row)
          :away-team   (:away_team row)
          :home-team-norm (normalize-team-name (:home_team row))
          :away-team-norm (normalize-team-name (:away_team row))
          :home-goals  (parse-int (:home_goal row))
          :away-goals  (parse-int (:away_goal row))
          :season      (parse-int (:season row))
          :round       (:round row)})
       (read-csv-file (data-path "Brazilian_Cup_Matches.csv"))))

(defn load-libertadores-matches []
  (map (fn [row]
         {:competition "Copa Libertadores"
          :datetime    (:datetime row)
          :date        (parse-date (:datetime row))
          :home-team   (:home_team row)
          :away-team   (:away_team row)
          :home-team-norm (normalize-team-name (:home_team row))
          :away-team-norm (normalize-team-name (:away_team row))
          :home-goals  (parse-int (:home_goal row))
          :away-goals  (parse-int (:away_goal row))
          :season      (parse-int (:season row))
          :stage       (:stage row)})
       (read-csv-file (data-path "Libertadores_Matches.csv"))))

(defn load-br-football-dataset []
  (map (fn [row]
         {:competition (:tournament row)
          :date        (parse-date (:date row))
          :datetime    (:date row)
          :home-team   (:home row)
          :away-team   (:away row)
          :home-team-norm (normalize-team-name (:home row))
          :away-team-norm (normalize-team-name (:away row))
          :home-goals  (parse-double-as-int (:home_goal row))
          :away-goals  (parse-double-as-int (:away_goal row))
          :home-corners (parse-double-as-int (:home_corner row))
          :away-corners (parse-double-as-int (:away_corner row))
          :home-shots  (parse-double-as-int (:home_shots row))
          :away-shots  (parse-double-as-int (:away_shots row))
          :total-corners (parse-double-as-int (:total_corners row))})
       (read-csv-file (data-path "BR-Football-Dataset.csv"))))

(defn load-historico-brasileirao []
  (map (fn [row]
         {:competition "Brasileirao Serie A"
          :match-id    (:ID row)
          :date        (parse-date (:Data row))
          :datetime    (:Data row)
          :season      (parse-int (:Ano row))
          :round       (:Rodada row)
          :home-team   (:Equipe_mandante row)
          :away-team   (:Equipe_visitante row)
          :home-team-norm (normalize-team-name (:Equipe_mandante row))
          :away-team-norm (normalize-team-name (:Equipe_visitante row))
          :home-goals  (parse-int (:Gols_mandante row))
          :away-goals  (parse-int (:Gols_visitante row))
          :winner      (:Vencedor row)
          :arena       (:Arena row)})
       (read-csv-file (data-path "novo_campeonato_brasileiro.csv"))))

(defn load-fifa-players []
  (map (fn [row]
         {:id          (:ID row)
          :name        (:Name row)
          :age         (parse-int (:Age row))
          :nationality (:Nationality row)
          :overall     (parse-int (:Overall row))
          :potential   (parse-int (:Potential row))
          :club        (:Club row)
          :position    (:Position row)
          :jersey-number (get row (keyword "Jersey Number"))
          :height      (:Height row)
          :weight      (:Weight row)})
       (read-csv-file (data-path "fifa_data.csv"))))

;; ---------------------------------------------------------------------------
;; Unified DB (loaded once)
;; ---------------------------------------------------------------------------

(defonce ^:private db-atom (atom nil))

(defn load-all!
  "Load all datasets into memory.  Idempotent; only loads once unless reset."
  []
  (when (nil? @db-atom)
    (println "Loading datasets...")
    (let [brasileirao  (vec (load-brasileirao-matches))
          cup          (vec (load-cup-matches))
          libertadores (vec (load-libertadores-matches))
          br-football  (vec (load-br-football-dataset))
          historico    (vec (load-historico-brasileirao))
          fifa         (vec (load-fifa-players))
          all-matches  (concat brasileirao cup libertadores br-football historico)]
      (reset! db-atom {:brasileirao  brasileirao
                       :cup          cup
                       :libertadores libertadores
                       :br-football  br-football
                       :historico    historico
                       :all-matches  (vec all-matches)
                       :fifa         fifa}))
    (println "Datasets loaded."))
  @db-atom)

(defn db [] (or @db-atom (load-all!)))

(defn reset-db! [] (reset! db-atom nil))
