(ns brazil-soccer.data
  "Loads the Kaggle CSV files in data/kaggle into one normalized match table and one
  player table. Each match is a map with :date, :competition, :season, :round, :stage,
  :home, :away (team keys), :home-goals and :away-goals."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazil-soccer.teams :as teams])
  (:import [java.time LocalDate]
           [java.time.format DateTimeFormatter]))

(def default-data-dir "data/kaggle")

(defn parse-date
  "Parses ISO (2023-09-24, 2012-05-19 18:30:00) or Brazilian (29/03/2003) dates.
  Returns nil for blank or unrecognised input."
  [s]
  (let [s (str/trim (str s))]
    (cond
      (re-matches #"\d{4}-\d{2}-\d{2}.*" s) (LocalDate/parse (subs s 0 10))
      (re-matches #"\d{2}/\d{2}/\d{4}" s) (LocalDate/parse s (DateTimeFormatter/ofPattern "dd/MM/yyyy"))
      :else nil)))

(defn- parse-number [s]
  (let [s (str/trim (str s))]
    (when-not (str/blank? s)
      (try (Double/parseDouble s) (catch NumberFormatException _ nil)))))

(defn- parse-int [s]
  (some-> (parse-number s) int))

(defn- read-rows
  "Reads a CSV file into a seq of maps keyed by the header names (BOM stripped)."
  [path]
  (with-open [r (io/reader path :encoding "UTF-8")]
    (let [[header & rows] (csv/read-csv r)
          cols (map #(str/trim (str/replace % "﻿" "")) header)]
      (doall (map #(zipmap cols %) rows)))))

(defn- match-map
  "Builds a normalized match from source-specific raw values; nil when incomplete."
  [{:keys [competition date home away home-goals away-goals round stage]}]
  (when (and competition date home away home-goals away-goals)
    {:date date
     :season (.getYear ^LocalDate date)
     :competition competition
     :round round
     :stage (when-not (str/blank? stage) (str/trim stage))
     :home (teams/team-key home)
     :away (teams/team-key away)
     :home-goals home-goals
     :away-goals away-goals}))

(defn- brasileirao-matches [rows]
  (for [r rows]
    (match-map {:competition :serie-a
                :date (parse-date (get r "datetime"))
                :round (parse-int (get r "round"))
                :home (get r "home_team") :away (get r "away_team")
                :home-goals (parse-int (get r "home_goal"))
                :away-goals (parse-int (get r "away_goal"))})))

(defn- novo-campeonato-matches [rows]
  (for [r rows]
    (match-map {:competition :serie-a
                :date (parse-date (get r "Data"))
                :round (parse-int (get r "Rodada"))
                :home (get r "Equipe_mandante") :away (get r "Equipe_visitante")
                :home-goals (parse-int (get r "Gols_mandante"))
                :away-goals (parse-int (get r "Gols_visitante"))})))

(defn- cup-matches [rows]
  (for [r rows]
    (match-map {:competition :copa-do-brasil
                :date (parse-date (get r "datetime"))
                :round (parse-int (get r "round"))
                :home (get r "home_team") :away (get r "away_team")
                :home-goals (parse-int (get r "home_goal"))
                :away-goals (parse-int (get r "away_goal"))})))

(defn- libertadores-matches [rows]
  (for [r rows]
    (match-map {:competition :libertadores
                :date (parse-date (get r "datetime"))
                :stage (get r "stage")
                :home (get r "home_team") :away (get r "away_team")
                :home-goals (parse-int (get r "home_goal"))
                :away-goals (parse-int (get r "away_goal"))})))

(defn- extended-matches [rows]
  (for [r rows]
    (match-map {:competition (teams/competition-of (get r "tournament"))
                :date (parse-date (get r "date"))
                :home (get r "home") :away (get r "away")
                :home-goals (parse-int (get r "home_goal"))
                :away-goals (parse-int (get r "away_goal"))})))

(def ^:private match-sources
  "Files in priority order; when the same fixture appears in several files the first wins.
  Sources disagree on dates by a day for some fixtures, so a fixture is identified by
  competition, season, teams and score rather than by date."
  [["Brasileirao_Matches.csv" brasileirao-matches]
   ["novo_campeonato_brasileiro.csv" novo-campeonato-matches]
   ["Brazilian_Cup_Matches.csv" cup-matches]
   ["Libertadores_Matches.csv" libertadores-matches]
   ["BR-Football-Dataset.csv" extended-matches]])

(defn load-matches
  "Loads and merges all match files under `data-dir`, dropping duplicate fixtures."
  [data-dir]
  (let [all (mapcat (fn [[file parse-rows]]
                      (keep identity (parse-rows (read-rows (io/file data-dir file)))))
                    match-sources)]
    (->> all
         (reduce (fn [[seen acc] m]
                   (let [k [(:competition m) (:season m) (:home m) (:away m) (:home-goals m) (:away-goals m)]]
                     (if (contains? seen k)
                       [seen acc]
                       [(conj seen k) (conj acc m)])))
                 [#{} []])
         second
         (sort-by :date))))

(defn- player-map [r]
  (let [club (str/trim (str (get r "Club")))]
    {:id (parse-int (get r "ID"))
     :name (get r "Name")
     :age (parse-int (get r "Age"))
     :nationality (get r "Nationality")
     :overall (parse-int (get r "Overall"))
     :potential (parse-int (get r "Potential"))
     :club (when-not (str/blank? club) club)
     :club-key (when-not (str/blank? club) (teams/team-key club))
     :position (get r "Position")
     :jersey-number (parse-int (get r "Jersey Number"))
     :value (get r "Value")
     :wage (get r "Wage")}))

(defn load-players
  "Loads the FIFA player table."
  [data-dir]
  (mapv player-map (read-rows (io/file data-dir "fifa_data.csv"))))

(defn load-db
  "Loads every dataset under `data-dir` into the database map used by the queries."
  ([] (load-db default-data-dir))
  ([data-dir]
   {:matches (vec (load-matches data-dir))
    :players (load-players data-dir)}))
