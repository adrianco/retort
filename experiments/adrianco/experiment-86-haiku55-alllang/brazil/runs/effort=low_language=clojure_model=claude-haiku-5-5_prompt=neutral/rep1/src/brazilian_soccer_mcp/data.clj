(ns brazilian-soccer-mcp.data
  "Loads the Kaggle CSV files into normalized match and player records."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer-mcp.normalize :as n]))

(defn- read-rows
  "Reads a UTF-8 CSV file into a vector of header->value maps, stripping any BOM."
  [dir filename]
  (with-open [reader (io/reader (io/file dir filename) :encoding "UTF-8")]
    (let [[header & rows] (csv/read-csv reader)
          header (map #(str/trim (str/replace % "﻿" "")) header)]
      (mapv #(zipmap header %) rows))))

(defn- ->long
  "Parses an integer or decimal string such as \"2\" or \"2.0\". Blank or non-numeric values (e.g. \"NA\") give nil."
  [s]
  (let [s (str/trim (or s ""))]
    (when-not (str/blank? s)
      (try (long (Double/parseDouble s))
           (catch NumberFormatException _ nil)))))

(defn- match-record
  "Builds a normalized match, or nil when the row lacks a date, teams or scores."
  [{:keys [competition date home away home-goals away-goals round]}]
  (when (and competition date home away home-goals away-goals)
    {:competition competition
     :date date
     :season (.getYear date)
     :round (when-not (str/blank? round) round)
     :home (n/display-name home)
     :away (n/display-name away)
     :home-key (n/team-key home)
     :away-key (n/team-key away)
     :home-goals home-goals
     :away-goals away-goals}))

(defn- brasileirao-matches [dir]
  (->> (read-rows dir "Brasileirao_Matches.csv")
       (map (fn [r] {:competition :brasileirao
                     :date (n/parse-date (r "datetime"))
                     :round (r "round")
                     :home (r "home_team")
                     :away (r "away_team")
                     :home-goals (->long (r "home_goal"))
                     :away-goals (->long (r "away_goal"))}))
       (keep match-record)))

(defn- historical-matches
  "The 2003-2019 Brasileirão file, which uses Portuguese column names."
  [dir]
  (->> (read-rows dir "novo_campeonato_brasileiro.csv")
       (map (fn [r] {:competition :brasileirao
                     :date (n/parse-date (r "Data"))
                     :round (r "Rodada")
                     :home (r "Equipe_mandante")
                     :away (r "Equipe_visitante")
                     :home-goals (->long (r "Gols_mandante"))
                     :away-goals (->long (r "Gols_visitante"))}))
       (keep match-record)))

(defn- cup-matches [dir]
  (->> (read-rows dir "Brazilian_Cup_Matches.csv")
       (map (fn [r] {:competition :copa-do-brasil
                     :date (n/parse-date (r "datetime"))
                     :round (r "round")
                     :home (r "home_team")
                     :away (r "away_team")
                     :home-goals (->long (r "home_goal"))
                     :away-goals (->long (r "away_goal"))}))
       (keep match-record)))

(defn- libertadores-matches [dir]
  (->> (read-rows dir "Libertadores_Matches.csv")
       (map (fn [r] {:competition :libertadores
                     :date (n/parse-date (r "datetime"))
                     :round (r "stage")
                     :home (r "home_team")
                     :away (r "away_team")
                     :home-goals (->long (r "home_goal"))
                     :away-goals (->long (r "away_goal"))}))
       (keep match-record)))

(def ^:private extended-tournaments
  {"Serie A" :brasileirao
   "Serie B" :serie-b
   "Serie C" :serie-c
   "Copa do Brasil" :copa-do-brasil})

(defn- extended-matches [dir]
  (->> (read-rows dir "BR-Football-Dataset.csv")
       (map (fn [r] {:competition (extended-tournaments (r "tournament"))
                     :date (n/parse-date (r "date"))
                     :home (r "home")
                     :away (r "away")
                     :home-goals (->long (r "home_goal"))
                     :away-goals (->long (r "away_goal"))}))
       (keep match-record)))

(defn- dedupe-matches
  "Keeps the first record for each competition/season/home/away combination.
  Overlapping sources (e.g. 2012-2019 Brasileirão appears in several files) collapse
  here. Dates are not part of the key because the sources disagree by a day for some
  fixtures; a club pair meets at most once per season in each orientation."
  [ms]
  (->> ms
       (reduce (fn [{:keys [seen out] :as acc} m]
                 (let [k ((juxt :competition :season
                                #(get-in % [:home-key :base])
                                #(get-in % [:away-key :base]))
                          m)]
                   (if (seen k)
                     acc
                     {:seen (conj seen k) :out (conj out m)})))
               {:seen #{} :out []})
       :out))

(defn- ->player [r]
  (let [player-name (str/trim (r "Name" ""))]
    (when-not (str/blank? player-name)
      {:id (r "ID")
       :name player-name
       :age (->long (r "Age"))
       :nationality (r "Nationality" "")
       :overall (->long (r "Overall"))
       :potential (->long (r "Potential"))
       :club (r "Club" "")
       :position (r "Position" "")
       :jersey-number (->long (r "Jersey Number"))
       :height (r "Height" "")
       :weight (r "Weight" "")
       :preferred-foot (r "Preferred Foot" "")})))

(defn load-dataset
  "Loads every Kaggle file under `dir` into {:matches [...] :players [...]}.
  Matches are de-duplicated across overlapping sources and sorted by date."
  [dir]
  {:matches (->> (concat (brasileirao-matches dir)
                         (historical-matches dir)
                         (cup-matches dir)
                         (libertadores-matches dir)
                         (extended-matches dir))
                 dedupe-matches
                 (sort-by :date)
                 vec)
   :players (->> (read-rows dir "fifa_data.csv")
                 (keep ->player)
                 vec)})
