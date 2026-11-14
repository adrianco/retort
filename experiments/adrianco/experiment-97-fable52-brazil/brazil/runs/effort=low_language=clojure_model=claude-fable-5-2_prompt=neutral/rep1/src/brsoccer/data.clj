(ns brsoccer.data
  "Loads the six Kaggle CSV files into one in-memory database.

  Matches from all sources share one shape; the same fixture appearing in more
  than one file (the Serie A files overlap heavily) is kept once, so statistics
  are not double counted."
  (:require [brsoccer.teams :as teams]
            [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str])
  (:import (java.time LocalDate)))

(def competitions
  {:serie-a        "Brasileirão Série A"
   :serie-b        "Brasileirão Série B"
   :serie-c        "Brasileirão Série C"
   :copa-do-brasil "Copa do Brasil"
   :libertadores   "Copa Libertadores"})

(def files
  ["novo_campeonato_brasileiro.csv" "Brasileirao_Matches.csv" "Brazilian_Cup_Matches.csv"
   "Libertadores_Matches.csv" "BR-Football-Dataset.csv" "fifa_data.csv"])

(defn parse-date
  "Accepts \"2023-09-24\", \"2012-05-19 18:30:00\" and \"29/03/2003\"; returns ISO yyyy-MM-dd or nil."
  [s]
  (let [s (str/trim (str s))]
    (try
      (if-let [[_ y m d] (re-find #"^(\d{4})-(\d{1,2})-(\d{1,2})" s)]
        (str (LocalDate/of (parse-long y) (parse-long m) (parse-long d)))
        (when-let [[_ d m y] (re-find #"^(\d{1,2})/(\d{1,2})/(\d{4})" s)]
          (str (LocalDate/of (parse-long y) (parse-long m) (parse-long d)))))
      (catch Exception _ nil))))

(defn parse-int
  "\"3\" and \"3.0\" -> 3; blanks, \"NA\" and \"-\" -> nil."
  [s]
  (when-let [[_ n] (re-matches #"\s*(-?\d+)(?:\.0+)?\s*" (str s))]
    (parse-long n)))

(defn- read-csv [dir file]
  (with-open [r (io/reader (io/file dir file) :encoding "UTF-8")]
    (let [[header & rows] (csv/read-csv r)
          header (mapv #(str/replace % "﻿" "") header)]
      (mapv #(zipmap header %) rows))))

(defn- proto
  "Common match shape, or nil when the row has no usable score (unplayed match)."
  [source competition season date home away hg ag extra]
  (let [hg (parse-int hg) ag (parse-int ag) date (parse-date date)]
    (when (and hg ag home away)
      (merge {:source source :sources [source] :competition competition
              :season (or (parse-int season) (some-> date (subs 0 4) parse-long))
              :date date :home-p home :away-p away :hg hg :ag ag}
             extra))))

(defn- novo-matches [rows]
  (keep (fn [r]
          (proto "novo_campeonato_brasileiro.csv" :serie-a (r "Ano") (r "Data")
                 (teams/parse (r "Equipe_mandante") (r "Mandante_UF"))
                 (teams/parse (r "Equipe_visitante") (r "Visitante_UF"))
                 (r "Gols_mandante") (r "Gols_visitante")
                 {:round (parse-int (r "Rodada"))
                  :arena (when-not (str/blank? (r "Arena")) (r "Arena"))}))
        rows))

(defn- brasileirao-matches [rows]
  (keep (fn [r]
          (proto "Brasileirao_Matches.csv" :serie-a (r "season") (r "datetime")
                 (teams/parse (r "home_team") (r "home_team_state"))
                 (teams/parse (r "away_team") (r "away_team_state"))
                 (r "home_goal") (r "away_goal")
                 {:round (parse-int (r "round"))}))
        rows))

(defn- cup-stages
  "The cup file only numbers its rounds. Name the last rounds of each season
  that actually reaches a two-match final."
  [rows]
  (into {}
        (mapcat
         (fn [[season rs]]
           (let [counts (frequencies (keep #(parse-int (% "round")) rs))
                 rounds (sort > (keys counts))]
             (when (and (seq rounds) (<= (counts (first rounds)) 2))
               (keep (fn [[rnd [stage cap]]]
                       (when (<= (counts rnd) cap) [[season rnd] stage]))
                     (map vector rounds [["final" 2] ["semifinals" 4]
                                         ["quarterfinals" 8] ["round of 16" 16]]))))))
        (group-by #(% "season") rows)))

(defn- cup-matches [rows]
  (let [stages (cup-stages rows)]
    (keep (fn [r]
            (let [rnd (parse-int (r "round"))]
              (proto "Brazilian_Cup_Matches.csv" :copa-do-brasil (r "season") (r "datetime")
                     (teams/parse (r "home_team")) (teams/parse (r "away_team"))
                     (r "home_goal") (r "away_goal")
                     {:round rnd :stage (stages [(r "season") rnd])})))
          rows)))

(defn- libertadores-matches [rows]
  (keep (fn [r]
          (proto "Libertadores_Matches.csv" :libertadores (r "season") (r "datetime")
                 (teams/parse (r "home_team")) (teams/parse (r "away_team"))
                 (r "home_goal") (r "away_goal")
                 {:stage (some-> (r "stage") str/trim str/lower-case)}))
        rows))

(def ^:private br-tournaments
  {"Serie A" :serie-a "Serie B" :serie-b "Serie C" :serie-c "Copa do Brasil" :copa-do-brasil})

(defn- br-season
  "This file has no season column. The 2020 season was played into early 2021
  (pandemic), so those matches belong to 2020."
  [competition date]
  (when date
    (let [year (parse-long (subs date 0 4))
          cutoff (if (= competition :copa-do-brasil) "2021-03-08" "2021-03-01")]
      (if (and (= year 2021) (neg? (compare date cutoff))) 2020 year))))

(defn- br-football-matches [rows]
  (keep (fn [r]
          (when-let [comp (br-tournaments (r "tournament"))]
            (let [date (parse-date (r "date"))
                  n    (fn [k] (parse-int (r k)))]
              (proto "BR-Football-Dataset.csv" comp (str (br-season comp date)) (r "date")
                     (teams/parse (r "home")) (teams/parse (r "away"))
                     (r "home_goal") (r "away_goal")
                     {:stats {:home-corners (n "home_corner") :away-corners (n "away_corner")
                              :home-attacks (n "home_attack") :away-attacks (n "away_attack")
                              :home-shots (n "home_shots") :away-shots (n "away_shots")
                              :total-corners (n "total_corners")}}))))
        rows))

(defn- dedupe-matches
  "Sources are fed in priority order. A later row for the same competition and
  fixture within two days of one already kept (kick-off times differ by time
  zone between files) is the same match: keep the first, merge extras in."
  [ms]
  (:kept
   (reduce
    (fn [{:keys [kept idx] :as acc} m]
      (let [k   [(:competition m) (:home m) (:away m)]
            day (some-> (:date m) LocalDate/parse .toEpochDay)
            dup (when day
                  (some (fn [[d i]] (when (<= (abs (- day d)) 2) i)) (idx k)))]
        (cond
          dup  (assoc acc :kept
                      (update kept dup
                              (fn [a] (-> (merge (select-keys m [:stats :arena :round :stage])
                                                 (into {} (remove (comp nil? val)) a))
                                          (update :sources into (:sources m))))))
          :else {:kept (conj kept m)
                 :idx  (if day (update idx k (fnil conj []) [day (count kept)]) idx)})))
    {:kept [] :idx {}}
    ms)))

(def ^:private skill-columns
  ["Crossing" "Finishing" "HeadingAccuracy" "ShortPassing" "Volleys" "Dribbling" "Curve"
   "FKAccuracy" "LongPassing" "BallControl" "Acceleration" "SprintSpeed" "Agility"
   "Reactions" "Balance" "ShotPower" "Jumping" "Stamina" "Strength" "LongShots"
   "Aggression" "Interceptions" "Positioning" "Vision" "Penalties" "Composure"
   "Marking" "StandingTackle" "SlidingTackle" "GKDiving" "GKHandling" "GKKicking"
   "GKPositioning" "GKReflexes"])

(defn- player [r]
  (let [nb (fn [k] (let [v (r k)] (when-not (str/blank? v) v)))]
    {:id (parse-int (r "ID")) :name (r "Name") :name-fold (teams/fold (r "Name"))
     :age (parse-int (r "Age")) :nationality (r "Nationality")
     :overall (parse-int (r "Overall")) :potential (parse-int (r "Potential"))
     :club (nb "Club") :position (nb "Position") :jersey (parse-int (r "Jersey Number"))
     :height (nb "Height") :weight (nb "Weight") :value (nb "Value") :wage (nb "Wage")
     :foot (nb "Preferred Foot") :joined (nb "Joined") :contract (nb "Contract Valid Until")
     :skills (into (array-map) (keep (fn [c] (when-let [v (parse-int (r c))] [c v]))) skill-columns)}))

(defn- link-clubs
  "Attach :club-key to players whose FIFA club is one of the Brazilian teams in
  the match data. A name match alone is not enough (Portugal's Boavista FC is
  not Boavista-RJ), so the club's squad must also be mostly Brazilian."
  [players index teams]
  (let [club->key (into {}
                        (keep (fn [[club ps]]
                                (when club
                                  (let [k (teams/team-key index (teams/parse club))]
                                    (when (and (:brazilian? (teams k))
                                               (> (count (filter #(= "Brazil" (:nationality %)) ps))
                                                  (/ (count ps) 2)))
                                      [club k])))))
                        (group-by :club players))]
    (mapv #(assoc % :club-key (club->key (:club %))) players)))

(defn build-db [dir]
  (let [rows   (into {} (map (fn [f] [f (read-csv dir f)])) files)
        protos (vec (concat (novo-matches (rows "novo_campeonato_brasileiro.csv"))
                            (brasileirao-matches (rows "Brasileirao_Matches.csv"))
                            (cup-matches (rows "Brazilian_Cup_Matches.csv"))
                            (libertadores-matches (rows "Libertadores_Matches.csv"))
                            (br-football-matches (rows "BR-Football-Dataset.csv"))))
        index  (teams/build-index (mapcat (juxt :home-p :away-p) protos))
        keyed  (map #(assoc % :home (teams/team-key index (:home-p %))
                              :away (teams/team-key index (:away-p %)))
                    protos)
        names  (reduce (fn [m p] (-> m
                                     (update (:home p) (fnil conj []) (:home-p p))
                                     (update (:away p) (fnil conj []) (:away-p p))))
                       {} keyed)
        display (into {} (map (fn [[k ps]] [k (teams/display-name index k ps)])) names)
        matches (->> (dedupe-matches keyed)
                     (mapv #(-> %
                                (assoc :home-name (display (:home %)) :away-name (display (:away %)))
                                (dissoc :home-p :away-p))))
        teams  (reduce (fn [m {:keys [home away competition]}]
                         (reduce (fn [m k]
                                   (-> m
                                       (update-in [k :matches] (fnil inc 0))
                                       (update-in [k :competitions] (fnil conj #{}) competition)))
                                 m [home away]))
                       {} matches)
        teams  (into {} (map (fn [[k t]]
                               [k (assoc t :key k :name (display k) :name-fold (teams/fold (display k))
                                         :brazilian? (boolean (some #(not= :libertadores %)
                                                                    (:competitions t))))]))
                     teams)]
    {:dir dir
     :row-counts (into {} (map (fn [[f rs]] [f (count rs)])) rows)
     :index index
     :teams teams
     :matches matches
     :players (link-clubs (mapv player (rows "fifa_data.csv")) index teams)}))

(defn data-dir []
  (or (System/getenv "BRSOCCER_DATA_DIR") "data/kaggle"))

(defonce ^:private db* (delay (build-db (data-dir))))

(defn db [] @db*)
