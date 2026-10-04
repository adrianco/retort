(ns brsoccer.data
  "Loads the six Kaggle CSV files into one in-memory database:

    {:matches [...]   ; unified, de-duplicated matches from the 5 match files
     :players [...]   ; FIFA players
     :teams   {key display-name}
     :files   {file-name row-count}}

  The same fixture can appear in up to three files (e.g. a 2015 Série A game
  is in Brasileirao_Matches, novo_campeonato_brasileiro and
  BR-Football-Dataset). Such rows are merged into a single match that keeps
  the union of their fields (round, arena, corners, shots ...)."
  (:require [brsoccer.names :as names]
            [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str])
  (:import (java.time LocalDate)))

(def default-data-dir
  (or (System/getenv "BRSOCCER_DATA_DIR") "data/kaggle"))

(defn- read-csv
  "Reads a CSV file into a vector of header->value maps."
  [dir file]
  (with-open [r (io/reader (io/file dir file) :encoding "UTF-8")]
    (let [[header & rows] (csv/read-csv r)
          header (map #(str/replace % "﻿" "") header)]
      (mapv #(zipmap header %) rows))))

(defn parse-num [s]
  (let [s (some-> s str/trim)]
    (when (and s (re-matches #"-?\d+(\.\d+)?" s))
      (Double/parseDouble s))))

(defn parse-int [s]
  (some-> (parse-num s) long))

(defn iso-date
  "Normalises \"2012-05-19 18:30:00\" and \"29/03/2003\" to \"YYYY-MM-DD\"."
  [s]
  (let [s (str/trim (str s))]
    (if-let [[_ d m y] (re-matches #"(\d{2})/(\d{2})/(\d{4})" s)]
      (str y "-" m "-" d)
      (re-find #"^\d{4}-\d{2}-\d{2}" s))))

(defn- time-of [s]
  (second (re-find #"(\d{2}:\d{2})(:\d{2})?$" (str s))))

(defn- non-blank [s]
  (when-not (str/blank? s) (str/trim s)))

(defn- match
  "Builds a match map, or nil when the row has no date or no score (fixtures
  not yet played) or pits a team against itself (two corrupt cup rows)."
  [m]
  (let [home (names/team-key (:home-raw m))
        away (names/team-key (:away-raw m))]
    (when (and (:date m) (:home-goals m) (:away-goals m) (not= home away))
      (into {:home home :away away}
            (remove (comp nil? val))
            m))))

;; ---------------------------------------------------------------------------
;; One loader per match file

(defn- brasileirao [rows]
  (for [r rows]
    (match {:source "Brasileirao_Matches.csv"
            :competition names/serie-a
            :season (parse-int (r "season"))
            :date (iso-date (r "datetime"))
            :time (time-of (r "datetime"))
            :round (parse-int (r "round"))
            :home-raw (r "home_team") :away-raw (r "away_team")
            :home-state (non-blank (r "home_team_state"))
            :away-state (non-blank (r "away_team_state"))
            :home-goals (parse-int (r "home_goal"))
            :away-goals (parse-int (r "away_goal"))})))

(def ^:private knockout-stages
  {2 "final" 4 "semifinals" 8 "quarterfinals" 16 "round of 16"})

(defn- cup-stages
  "The cup file only numbers its rounds. For seasons whose last round is a
  two-legged final, names the closing rounds: {[season round] stage}."
  [rows]
  (let [sizes (frequencies (map (juxt #(parse-int (% "season")) #(parse-int (% "round"))) rows))]
    (into {}
          (for [[season rounds] (group-by ffirst sizes)
                :let [last-round (apply max (map (comp second key) rounds))]
                :when (= 2 (sizes [season last-round]))
                [[_ round] n] rounds
                :let [stage (knockout-stages n)]
                :when (and stage (> round (- last-round 4)))]
            [[season round] stage]))))

(defn- copa-do-brasil [rows]
  (let [stages (cup-stages rows)]
    (for [r rows
          :let [season (parse-int (r "season"))
                round (parse-int (r "round"))]]
      (match {:source "Brazilian_Cup_Matches.csv"
              :competition names/copa-do-brasil
              :season season
              :date (iso-date (r "datetime"))
              :time (time-of (r "datetime"))
              :round round
              :stage (stages [season round])
              :home-raw (r "home_team") :away-raw (r "away_team")
              :home-goals (parse-int (r "home_goal"))
              :away-goals (parse-int (r "away_goal"))}))))

(defn- libertadores [rows]
  (for [r rows]
    (match {:source "Libertadores_Matches.csv"
            :competition names/libertadores
            :season (parse-int (r "season"))
            :date (iso-date (r "datetime"))
            :time (time-of (r "datetime"))
            :stage (non-blank (r "stage"))
            :home-raw (r "home_team") :away-raw (r "away_team")
            :home-goals (parse-int (r "home_goal"))
            :away-goals (parse-int (r "away_goal"))})))

(defn- season-of
  "BR-Football-Dataset has no season column. The 2020 competitions were
  delayed by the pandemic and finished in early 2021."
  [date]
  (let [year (parse-int (subs date 0 4))]
    (if (and (= year 2021) (neg? (compare date "2021-03-08")))
      2020
      year)))

(defn- br-football [rows]
  (for [r rows
        :let [date (iso-date (r "date"))
              stats (into {}
                          (keep (fn [[k col]] (when-let [v (parse-int (r col))] [k v])))
                          {:home-corners "home_corner" :away-corners "away_corner"
                           :home-attacks "home_attack" :away-attacks "away_attack"
                           :home-shots "home_shots" :away-shots "away_shots"})]]
    (match {:source "BR-Football-Dataset.csv"
            :competition (names/competition (r "tournament"))
            :season (some-> date season-of)
            :date date
            :time (time-of (r "time"))
            :home-raw (r "home") :away-raw (r "away")
            :home-goals (parse-int (r "home_goal"))
            :away-goals (parse-int (r "away_goal"))
            :stats (not-empty stats)})))

(defn- historical [rows]
  (for [r rows]
    (match {:source "novo_campeonato_brasileiro.csv"
            :competition names/serie-a
            :season (parse-int (r "Ano"))
            :date (iso-date (r "Data"))
            :round (parse-int (r "Rodada"))
            :home-raw (r "Equipe_mandante") :away-raw (r "Equipe_visitante")
            :home-state (non-blank (r "Mandante_UF"))
            :away-state (non-blank (r "Visitante_UF"))
            :home-goals (parse-int (r "Gols_mandante"))
            :away-goals (parse-int (r "Gols_visitante"))
            :arena (non-blank (r "Arena"))})))

;; ---------------------------------------------------------------------------
;; Cross-file merge

(def ^:private source-priority
  "Lower wins when two files disagree about a merged match."
  {"Brasileirao_Matches.csv" 0 "Brazilian_Cup_Matches.csv" 0
   "Libertadores_Matches.csv" 0 "novo_campeonato_brasileiro.csv" 1
   "BR-Football-Dataset.csv" 2})

(defn- epoch-day [date]
  (.toEpochDay (LocalDate/parse date)))

(defn- merge-cluster [cluster]
  (let [by-priority (sort-by (comp source-priority :source) cluster)]
    (-> (apply merge (reverse by-priority))
        (dissoc :source)
        (assoc :sources (vec (distinct (map :source by-priority)))))))

(defn- same-fixture?
  "Files disagree by a day or two on kick-off dates (time zones), and may
  record a different result for an awarded game, so the score is ignored.
  Rows repeated within one file collapse the same way."
  [cluster m]
  (<= (- (epoch-day (:date m)) (epoch-day (:date (first cluster)))) 3))

(defn merge-duplicates
  "Collapses rows describing the same fixture in different files."
  [matches]
  (->> matches
       (group-by (juxt :competition :home :away))
       vals
       (mapcat (fn [fixtures]
                 (->> (sort-by (juxt :date (comp source-priority :source)) fixtures)
                      (reduce (fn [clusters m]
                                (if (and (seq clusters) (same-fixture? (peek clusters) m))
                                  (conj (pop clusters) (conj (peek clusters) m))
                                  (conj clusters [m])))
                              [])
                      (map merge-cluster))))))

(defn- team-names
  "key -> display name; the first file to mention a team names it."
  [matches]
  (reduce (fn [acc m]
            (reduce (fn [acc [k raw]]
                      (if (contains? acc k) acc (assoc acc k (names/display-name raw k))))
                    acc
                    [[(:home m) (:home-raw m)] [(:away m) (:away-raw m)]]))
          {}
          matches))

;; ---------------------------------------------------------------------------
;; Players

(def skill-columns
  ["Crossing" "Finishing" "HeadingAccuracy" "ShortPassing" "Volleys" "Dribbling"
   "Curve" "FKAccuracy" "LongPassing" "BallControl" "Acceleration" "SprintSpeed"
   "Agility" "Reactions" "Balance" "ShotPower" "Jumping" "Stamina" "Strength"
   "LongShots" "Aggression" "Interceptions" "Positioning" "Vision" "Penalties"
   "Composure" "Marking" "StandingTackle" "SlidingTackle" "GKDiving" "GKHandling"
   "GKKicking" "GKPositioning" "GKReflexes"])

(defn- player [r]
  (let [club (non-blank (r "Club"))]
    {:id (parse-int (r "ID"))
     :name (r "Name")
     :age (parse-int (r "Age"))
     :nationality (r "Nationality")
     :overall (parse-int (r "Overall"))
     :potential (parse-int (r "Potential"))
     :club club
     :club-key (some-> club names/team-key)
     :position (non-blank (r "Position"))
     :jersey (parse-int (r "Jersey Number"))
     :foot (non-blank (r "Preferred Foot"))
     :height (non-blank (r "Height"))
     :weight (non-blank (r "Weight"))
     :value (non-blank (r "Value"))
     :wage (non-blank (r "Wage"))
     :skills (into {}
                   (keep (fn [c] (when-let [v (parse-int (r c))] [c v])))
                   skill-columns)}))

;; ---------------------------------------------------------------------------

(defn load-db
  "Reads every CSV file in `dir` and builds the database."
  ([] (load-db default-data-dir))
  ([dir]
   (let [files [["novo_campeonato_brasileiro.csv" historical]
                ["Brasileirao_Matches.csv" brasileirao]
                ["Brazilian_Cup_Matches.csv" copa-do-brasil]
                ["Libertadores_Matches.csv" libertadores]
                ["BR-Football-Dataset.csv" br-football]]
         loaded (for [[file parse] files
                      :let [rows (read-csv dir file)]]
                  {:file file :rows (count rows) :matches (doall (remove nil? (parse rows)))})
         raw (mapcat :matches loaded)
         teams (team-names raw)
         matches (->> (merge-duplicates raw)
                      (map #(-> %
                                (assoc :home-name (teams (:home %))
                                       :away-name (teams (:away %)))
                                (dissoc :home-raw :away-raw)))
                      (sort-by (juxt :date :competition :home))
                      vec)
         player-rows (read-csv dir "fifa_data.csv")]
     {:matches matches
      :players (mapv player player-rows)
      :teams teams
      :files (assoc (into {} (map (juxt :file :rows)) loaded)
                    "fifa_data.csv" (count player-rows))})))

(def db
  "The database for the default data directory, loaded on first use."
  (delay (load-db)))
