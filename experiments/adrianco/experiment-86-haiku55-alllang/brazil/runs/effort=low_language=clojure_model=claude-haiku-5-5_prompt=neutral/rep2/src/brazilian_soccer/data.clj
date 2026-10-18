(ns brazilian-soccer.data
  "Loads the Kaggle CSV files into normalized match and player records.

  A match is {:date \"yyyy-MM-dd\" :season int :competition str :round str|nil
              :home str :away str :home-key str :away-key str
              :home-goals int :away-goals int :source str}.
  Matches that appear in several files are kept once (first source wins)."
  (:require [brazilian-soccer.csv :as csv]
            [brazilian-soccer.names :as names]
            [clojure.java.io :as io]
            [clojure.string :as str]))

(defn parse-date
  "Accepts ISO 'yyyy-MM-dd[ hh:mm:ss]' or Brazilian 'dd/MM/yyyy' and returns
  ISO 'yyyy-MM-dd', or nil when the value is not recognised."
  [s]
  (cond
    (re-find #"^\s*\d{4}-\d{2}-\d{2}" (str s))
    (subs (str/trim s) 0 10)

    :else
    (when-let [[_ d m y] (re-find #"^\s*(\d{2})/(\d{2})/(\d{4})" (str s))]
      (str y "-" m "-" d))))

(defn parse-whole
  "Parses numbers written as '2', '2.0' or '1.0' into a whole number; nil if blank or invalid."
  [s]
  (when-not (str/blank? s)
    (try
      (Math/round (Double/parseDouble (str/trim s)))
      (catch NumberFormatException _ nil))))

(defn- build-match
  [{:keys [source competition date round home away home-goals away-goals]}]
  (let [date (parse-date date)
        hk (names/team-key home)
        ak (names/team-key away)
        hg (parse-whole home-goals)
        ag (parse-whole away-goals)]
    (when (and date hk ak hg ag)
      {:date date
       :season (parse-long (subs date 0 4))
       :competition competition
       :round (when-not (str/blank? round) (str/trim round))
       :home (names/base-name home)
       :away (names/base-name away)
       :home-key hk
       :away-key ak
       :home-goals hg
       :away-goals ag
       :source source})))

(defn- rows->matches [rows f]
  (->> rows (map f) (keep build-match) vec))

(defn- brasileirao-series-name [tournament]
  (case (names/normalize-text tournament)
    "serie a" "Brasileirão"
    "serie b" "Brasileirão Série B"
    "serie c" "Brasileirão Série C"
    "copa do brasil" "Copa do Brasil"
    tournament))

(defn- day-gap [a b]
  (Math/abs (- (.toEpochDay (java.time.LocalDate/parse b))
               (.toEpochDay (java.time.LocalDate/parse a)))))

(defn- dedupe-matches
  "Keeps the first copy of each match. BR-Football stores some dates one day
  off (UTC), so a match counts as already seen when the same teams produced the
  same score within one day of an earlier kept match."
  [ms]
  (->> ms
       (reduce (fn [[seen out] m]
                 (let [k [(:home-key m) (:away-key m) (:home-goals m) (:away-goals m)]
                       dates (get seen k [])]
                   (if (some #(<= (day-gap % (:date m)) 1) dates)
                     [seen out]
                     [(assoc seen k (conj dates (:date m))) (conj out m)])))
               [{} []])
       second))

(defn load-matches-from
  "Reads all match files under dir and returns the de-duplicated match vector."
  [dir]
  (let [file #(str (io/file dir %))
        brasileirao (rows->matches
                     (csv/read-maps (file "Brasileirao_Matches.csv"))
                     #(hash-map :source "Brasileirao_Matches.csv" :competition "Brasileirão"
                                :date (% "datetime") :round (% "round")
                                :home (% "home_team") :away (% "away_team")
                                :home-goals (% "home_goal") :away-goals (% "away_goal")))
        cup (rows->matches
             (csv/read-maps (file "Brazilian_Cup_Matches.csv"))
             #(hash-map :source "Brazilian_Cup_Matches.csv" :competition "Copa do Brasil"
                        :date (% "datetime") :round (% "round")
                        :home (% "home_team") :away (% "away_team")
                        :home-goals (% "home_goal") :away-goals (% "away_goal")))
        libertadores (rows->matches
                      (csv/read-maps (file "Libertadores_Matches.csv"))
                      #(hash-map :source "Libertadores_Matches.csv" :competition "Libertadores"
                                 :date (% "datetime") :round (% "stage")
                                 :home (% "home_team") :away (% "away_team")
                                 :home-goals (% "home_goal") :away-goals (% "away_goal")))
        historical (rows->matches
                    (csv/read-maps (file "novo_campeonato_brasileiro.csv"))
                    #(hash-map :source "novo_campeonato_brasileiro.csv" :competition "Brasileirão"
                               :date (% "Data") :round (% "Rodada")
                               :home (% "Equipe_mandante") :away (% "Equipe_visitante")
                               :home-goals (% "Gols_mandante") :away-goals (% "Gols_visitante")))
        extended (rows->matches
                  (csv/read-maps (file "BR-Football-Dataset.csv"))
                  #(hash-map :source "BR-Football-Dataset.csv"
                             :competition (brasileirao-series-name (% "tournament"))
                             :date (% "date")
                             :home (% "home") :away (% "away")
                             :home-goals (% "home_goal") :away-goals (% "away_goal")))]
    ;; BR-Football overlaps the primary files but its dates and names disagree
    ;; with them in places, so it is only used for competition-seasons that no
    ;; primary file covers.
    (let [primary (concat brasileirao cup libertadores historical)
          covered (set (map (juxt #(names/competition-key (:competition %)) :season) primary))
          extended (remove #(covered [(names/competition-key (:competition %)) (:season %)])
                           extended)]
      (dedupe-matches (concat primary extended)))))

(defn load-players-from
  "Reads fifa_data.csv under dir and returns player records."
  [dir]
  (->> (csv/read-maps (str (io/file dir "fifa_data.csv")))
       (mapv (fn [r]
               {:id (get r "ID")
                :name (get r "Name")
                :age (parse-whole (get r "Age"))
                :nationality (get r "Nationality")
                :overall (parse-whole (get r "Overall"))
                :potential (parse-whole (get r "Potential"))
                :club (let [c (get r "Club")] (when-not (str/blank? c) c))
                :position (let [p (get r "Position")] (when-not (str/blank? p) (str/upper-case p)))
                :jersey-number (parse-whole (get r "Jersey Number"))}))))

(defn load-all
  "Loads every dataset under dir (default data/kaggle)."
  ([] (load-all "data/kaggle"))
  ([dir] {:matches (load-matches-from dir)
          :players (load-players-from dir)}))
