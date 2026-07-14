(ns br-soccer.data
  "CSV loading and normalization for Brazilian soccer datasets."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]))

(def ^:dynamic *data-dir* "data/kaggle")

(defn- read-csv [path]
  (with-open [r (io/reader path :encoding "UTF-8")]
    (doall (csv/read-csv r))))

(defn- rows->maps [rows]
  (let [header (mapv #(-> % str/trim (str/replace "\uFEFF" "") keyword) (first rows))]
    (mapv #(zipmap header %) (rest rows))))

(defn load-csv [filename]
  (let [path (str *data-dir* "/" filename)]
    (if (.exists (io/file path))
      (rows->maps (read-csv path))
      [])))

(defn normalize-team
  "Normalize a team name: strip state suffix like '-SP', trim, lowercase."
  [s]
  (when s
    (let [s (str/trim s)
          ;; Remove trailing state suffixes: "Palmeiras-SP", "Team - RJ", "Team (URU)"
          s (str/replace s #"\s*-\s*[A-Z]{2,3}\s*$" "")
          s (str/replace s #"\s*\([A-Z]{2,4}\)\s*$" "")
          s (str/replace s #"\s*-\s*[A-Z]{2,3}\s*\(.*\)$" "")]
      (-> s str/trim str/lower-case))))

(defn team-matches?
  "Does query match a team name (fuzzy, case-insensitive, substring)?"
  [query team-name]
  (when (and query team-name)
    (let [q (str/lower-case (str/trim query))
          n (str/lower-case (str/trim team-name))
          norm (normalize-team team-name)]
      (or (= q n)
          (= q norm)
          (str/includes? n q)
          (str/includes? (or norm "") q)))))

(defn- parse-int [s]
  (try
    (cond
      (number? s) (long s)
      (nil? s) nil
      (str/blank? s) nil
      :else (Long/parseLong (str/trim (str s))))
    (catch Exception _ nil)))

(defn- parse-double* [s]
  (try
    (cond
      (number? s) (double s)
      (nil? s) nil
      (str/blank? s) nil
      :else (Double/parseDouble (str/trim (str s))))
    (catch Exception _ nil)))

(defn- parse-br-date
  "Parse date string: handles YYYY-MM-DD, DD/MM/YYYY, with optional time."
  [s]
  (when (and s (not (str/blank? s)))
    (let [s (str/trim s)
          date-part (first (str/split s #"\s+"))]
      (cond
        (re-matches #"\d{4}-\d{2}-\d{2}" date-part) date-part
        (re-matches #"\d{2}/\d{2}/\d{4}" date-part)
        (let [[d m y] (str/split date-part #"/")]
          (format "%s-%s-%s" y m d))
        :else date-part))))

(defn- season-of [date-str]
  (parse-int (first (str/split (or date-str "") #"-"))))

;; ---- Normalizers for each dataset ----

(defn- norm-brasileirao [row]
  (let [date (parse-br-date (:datetime row))]
    {:competition "Brasileirão"
     :date date
     :season (or (parse-int (:season row)) (season-of date))
     :round (parse-int (:round row))
     :home (:home_team row)
     :away (:away_team row)
     :home-goal (parse-int (:home_goal row))
     :away-goal (parse-int (:away_goal row))
     :home-state (:home_team_state row)
     :away-state (:away_team_state row)
     :source "Brasileirao_Matches.csv"}))

(defn- norm-cup [row]
  (let [date (parse-br-date (:datetime row))]
    {:competition "Copa do Brasil"
     :date date
     :season (or (parse-int (:season row)) (season-of date))
     :round (:round row)
     :home (:home_team row)
     :away (:away_team row)
     :home-goal (parse-int (:home_goal row))
     :away-goal (parse-int (:away_goal row))
     :source "Brazilian_Cup_Matches.csv"}))

(defn- norm-lib [row]
  (let [date (parse-br-date (:datetime row))]
    {:competition "Copa Libertadores"
     :date date
     :season (or (parse-int (:season row)) (season-of date))
     :stage (:stage row)
     :home (:home_team row)
     :away (:away_team row)
     :home-goal (parse-int (:home_goal row))
     :away-goal (parse-int (:away_goal row))
     :source "Libertadores_Matches.csv"}))

(defn- norm-ext [row]
  (let [date (parse-br-date (:date row))]
    {:competition (:tournament row)
     :date date
     :season (season-of date)
     :home (:home row)
     :away (:away row)
     :home-goal (some-> (:home_goal row) parse-double* long)
     :away-goal (some-> (:away_goal row) parse-double* long)
     :home-corners (parse-double* (:home_corner row))
     :away-corners (parse-double* (:away_corner row))
     :home-shots (parse-double* (:home_shots row))
     :away-shots (parse-double* (:away_shots row))
     :ht-result (:ht_result row)
     :source "BR-Football-Dataset.csv"}))

(defn- norm-novo [row]
  (let [date (parse-br-date (:Data row))]
    {:competition "Brasileirão"
     :date date
     :season (or (parse-int (:Ano row)) (season-of date))
     :round (parse-int (:Rodada row))
     :home (:Equipe_mandante row)
     :away (:Equipe_visitante row)
     :home-goal (parse-int (:Gols_mandante row))
     :away-goal (parse-int (:Gols_visitante row))
     :home-state (:Mandante_UF row)
     :away-state (:Visitante_UF row)
     :winner (:Vencedor row)
     :arena (:Arena row)
     :source "novo_campeonato_brasileiro.csv"}))

(defn- norm-player [row]
  {:id (parse-int (:ID row))
   :name (:Name row)
   :age (parse-int (:Age row))
   :nationality (:Nationality row)
   :overall (parse-int (:Overall row))
   :potential (parse-int (:Potential row))
   :club (:Club row)
   :position (:Position row)
   :jersey (parse-int (get row (keyword "Jersey Number")))
   :height (:Height row)
   :weight (:Weight row)
   :foot (get row (keyword "Preferred Foot"))})

;; ---- Lazy, memoized loaders ----

(def matches
  (delay
    (->> [[norm-brasileirao "Brasileirao_Matches.csv"]
          [norm-cup         "Brazilian_Cup_Matches.csv"]
          [norm-lib         "Libertadores_Matches.csv"]
          [norm-ext         "BR-Football-Dataset.csv"]
          [norm-novo        "novo_campeonato_brasileiro.csv"]]
         (mapcat (fn [[f file]] (map f (load-csv file))))
         (filter (fn [m] (and (:home m) (:away m))))
         vec)))

(def players
  (delay
    (->> (load-csv "fifa_data.csv")
         (map norm-player)
         (filter :name)
         vec)))

(defn all-matches [] @matches)
(defn all-players [] @players)
