(ns brazilian-soccer.data
  "Loads the Kaggle CSV datasets and normalizes team names so that the same
  club can be matched across files that use different naming conventions
  (\"Palmeiras-SP\", \"Palmeiras\", \"América - MG\", \"America MG\", ...)."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]
           [java.time LocalDate]
           [java.time.format DateTimeFormatter]))

;; ---------------------------------------------------------------------------
;; Team-name normalization

(def ^:private state-codes
  #{"ac" "al" "ap" "am" "ba" "ce" "df" "es" "go" "ma" "mt" "ms" "mg"
    "pa" "pb" "pr" "pe" "pi" "rj" "rn" "rs" "ro" "rr" "sc" "sp" "se" "to"})

(def ^:private country-codes
  #{"arg" "bol" "chi" "col" "equ" "ecu" "mex" "par" "per" "uru" "ven" "bra"})

(def ^:private aliases
  "Maps normalized name variants to a canonical key. Keys with a -uf suffix
  pin the club to a state so distinct clubs with the same base name (e.g.
  Atlético-MG vs Athletico-PR) stay separate."
  {"athletico"                       "atletico-pr"
   "athletico-pr"                    "atletico-pr"
   "athletico paranaense"            "atletico-pr"
   "athletico paranaense-pr"         "atletico-pr"
   "atletico paranaense"             "atletico-pr"
   "atletico paranaense-pr"          "atletico-pr"
   "atletico mineiro"                "atletico-mg"
   "atletico mineiro-mg"             "atletico-mg"
   "atletico goianiense"             "atletico-go"
   "atletico goianiense-go"          "atletico-go"
   "america mineiro"                 "america-mg"
   "america fc natal"                "america-rn"
   "vasco da gama"                   "vasco"
   "vasco da gama-rj"                "vasco"
   "sport recife"                    "sport"
   "sport club do recife"            "sport"
   "sport club do recife-pe"         "sport"
   "sao paulo fc"                    "sao paulo"
   "sao paulo futebol clube"         "sao paulo"
   "sport club corinthians paulista" "corinthians"
   "red bull bragantino"             "bragantino"
   "rb bragantino"                   "bragantino"
   "abc"                             "abc-rn"
   "asa"                             "asa-al"})

(defn strip-accents
  "Removes diacritics: \"Grêmio\" -> \"Gremio\", \"Avaí\" -> \"Avai\"."
  [s]
  (-> (Normalizer/normalize (str s) Normalizer$Form/NFD)
      (str/replace #"\p{M}" "")))

(defn norm-team
  "Normalizes a raw team name into {:base ... :state ... :key ...}.
  :state is a lower-case state/country suffix when present, else nil.
  :key is base plus suffix (when present), suitable for grouping."
  [raw]
  (let [s (-> (str raw)
              (str/replace "﻿" "")
              strip-accents
              str/lower-case
              ;; \"guarani (par)\" -> \"guarani-par\", drop other parentheticals
              (str/replace #"\s*\(([a-z]{2,3})\)\s*$" "-$1")
              (str/replace #"\s*\([^)]*\)" " ")
              (str/replace #"\." "")
              ;; generic club-type words: \"Fortaleza FC\", \"EC Juventude\",
              ;; \"Aquidauanense Futebol Clube\"
              (str/replace #"\b(futebol clube|esporte clube|fc|ec)\b" " ")
              (str/replace #"\s*-\s*" "-")
              (str/replace #"\s+" " ")
              str/trim)
        ;; trailing space-separated state code: \"america mg\" -> \"america-mg\"
        s (if-let [[_ base suf] (re-matches #"(.+) ([a-z]{2})$" s)]
            (if (state-codes suf) (str base "-" suf) s)
            s)
        s (get aliases s s)
        [base state] (if-let [[_ b suf] (re-matches #"(.+?)-([a-z]{2,3})$" s)]
                       (if (or (state-codes suf) (country-codes suf))
                         [b suf]
                         [s nil])
                       [s nil])
        base' (get aliases base base)
        ;; an alias applied to the base may itself carry a state suffix
        [base state] (if-let [[_ b suf] (re-matches #"(.+?)-([a-z]{2,3})$" base')]
                       [b suf]
                       [base' state])]
    {:base  base
     :state state
     :key   (if state (str base "-" state) base)}))

(defn team-matches?
  "True when a user query (already passed through norm-team) refers to the
  given team. Bases must match exactly or as a whole-word substring; states
  must agree when both sides specify one."
  [query-norm team-norm]
  (let [qb (:base query-norm)
        tb (:base team-norm)]
    (and (or (= qb tb)
             (some? (re-find (re-pattern (str "(?<![a-z0-9])"
                                              (java.util.regex.Pattern/quote qb)
                                              "(?![a-z0-9])"))
                             tb)))
         (or (nil? (:state query-norm))
             (nil? (:state team-norm))
             (= (:state query-norm) (:state team-norm))))))

(defn display-name
  "Cleans a raw name for display: drops parentheticals and tightens
  \"América - MG\" / \"America MG\" into \"América-MG\"."
  [raw]
  (-> (str raw)
      (str/replace #"\s*\((?![A-Z]{2,3}\))[^)]*\)" "")
      (str/replace #"\s*\(([A-Z]{2,3})\)\s*$" "-$1")
      (str/replace #"\s+-\s+([A-Z]{2})$" "-$1")
      (str/replace #"\s+([A-Z]{2})$" "-$1")
      str/trim))

;; ---------------------------------------------------------------------------
;; Parsing helpers

(defn parse-num
  "Parses \"2\", \"2.0\" -> 2; blank/garbage -> nil."
  [s]
  (when-let [s (some-> s str/trim not-empty)]
    (try (long (Double/parseDouble s))
         (catch Exception _ nil))))

(def ^:private br-date (DateTimeFormatter/ofPattern "dd/MM/yyyy"))

(defn parse-date
  "Handles \"2012-05-19 18:30:00\", \"2023-09-24\" and \"29/03/2003\"."
  ^LocalDate [s]
  (when-let [s (some-> s str/trim not-empty)]
    (cond
      (re-matches #"\d{4}-\d{2}-\d{2}.*" s) (LocalDate/parse (subs s 0 10))
      (re-matches #"\d{2}/\d{2}/\d{4}" s)   (LocalDate/parse s br-date)
      :else nil)))

(defn norm-competition
  "Maps free-form competition input to the canonical competition name used
  in the loaded data, or nil when unrecognized."
  [s]
  (when-let [n (some-> s strip-accents str/lower-case)]
    (cond
      (re-find #"libertadores" n)             "Copa Libertadores"
      (re-find #"copa do brasil|cup" n)       "Copa do Brasil"
      (re-find #"serie\s*b\b" n)              "Brasileirão Série B"
      (re-find #"serie\s*c\b" n)              "Brasileirão Série C"
      (re-find #"brasileir|serie\s*a\b" n)    "Brasileirão Série A"
      :else nil)))

;; ---------------------------------------------------------------------------
;; CSV loading

(defn- read-csv [file]
  (with-open [r (io/reader file :encoding "UTF-8")]
    (let [[header & rows] (csv/read-csv r)
          header (mapv #(-> % (str/replace "﻿" "") str/trim) header)]
      (mapv #(zipmap header %) rows))))

(defn- make-match
  [{:keys [competition source priority]}
   {:keys [date season round stage home away home-goals away-goals venue stats]}]
  {:competition  competition
   :source       source
   :priority     priority
   :date         date
   :season       season
   :round        round
   :stage        stage
   :home-raw     home
   :away-raw     away
   :home-display (display-name home)
   :away-display (display-name away)
   :home         (norm-team home)
   :away         (norm-team away)
   :home-goals   home-goals
   :away-goals   away-goals
   :venue        venue
   :stats        stats})

(defn- load-brasileirao [dir]
  (for [m (read-csv (io/file dir "Brasileirao_Matches.csv"))]
    (make-match {:competition "Brasileirão Série A" :source :brasileirao :priority 1}
                {:date       (parse-date (m "datetime"))
                 :season     (parse-num (m "season"))
                 :round      (m "round")
                 :home       (m "home_team")
                 :away       (m "away_team")
                 :home-goals (parse-num (m "home_goal"))
                 :away-goals (parse-num (m "away_goal"))})))

(defn- load-historical [dir]
  (for [m (read-csv (io/file dir "novo_campeonato_brasileiro.csv"))]
    (make-match {:competition "Brasileirão Série A" :source :historical :priority 2}
                {:date       (parse-date (m "Data"))
                 :season     (parse-num (m "Ano"))
                 :round      (m "Rodada")
                 :home       (m "Equipe_mandante")
                 :away       (m "Equipe_visitante")
                 :home-goals (parse-num (m "Gols_mandante"))
                 :away-goals (parse-num (m "Gols_visitante"))
                 :venue      (not-empty (str/trim (or (m "Arena") "")))})))

(defn- load-cup [dir]
  (for [m (read-csv (io/file dir "Brazilian_Cup_Matches.csv"))]
    (make-match {:competition "Copa do Brasil" :source :cup :priority 1}
                {:date       (parse-date (m "datetime"))
                 :season     (parse-num (m "season"))
                 :round      (m "round")
                 :home       (m "home_team")
                 :away       (m "away_team")
                 :home-goals (parse-num (m "home_goal"))
                 :away-goals (parse-num (m "away_goal"))})))

(defn- load-libertadores [dir]
  (for [m (read-csv (io/file dir "Libertadores_Matches.csv"))]
    (make-match {:competition "Copa Libertadores" :source :libertadores :priority 1}
                {:date       (parse-date (m "datetime"))
                 :season     (parse-num (m "season"))
                 :stage      (m "stage")
                 :home       (m "home_team")
                 :away       (m "away_team")
                 :home-goals (parse-num (m "home_goal"))
                 :away-goals (parse-num (m "away_goal"))})))

(def ^:private brf-tournaments
  {"Serie A"        "Brasileirão Série A"
   "Serie B"        "Brasileirão Série B"
   "Serie C"        "Brasileirão Série C"
   "Copa do Brasil" "Copa do Brasil"})

(defn- load-extended [dir]
  (for [m     (read-csv (io/file dir "BR-Football-Dataset.csv"))
        :let  [comp (brf-tournaments (m "tournament"))
               date (parse-date (m "date"))]
        :when comp]
    (make-match {:competition comp :source :extended :priority 3}
                {:date       date
                 :season     (some-> date .getYear long)
                 :home       (m "home")
                 :away       (m "away")
                 :home-goals (parse-num (m "home_goal"))
                 :away-goals (parse-num (m "away_goal"))
                 :stats      {:home-corners (parse-num (m "home_corner"))
                              :away-corners (parse-num (m "away_corner"))
                              :home-attacks (parse-num (m "home_attack"))
                              :away-attacks (parse-num (m "away_attack"))
                              :home-shots   (parse-num (m "home_shots"))
                              :away-shots   (parse-num (m "away_shots"))
                              :ht-result    (m "ht_result")}})))

(def ^:private skill-columns
  ["Crossing" "Finishing" "HeadingAccuracy" "ShortPassing" "Volleys"
   "Dribbling" "Curve" "FKAccuracy" "LongPassing" "BallControl"
   "Acceleration" "SprintSpeed" "Agility" "Reactions" "Balance"
   "ShotPower" "Jumping" "Stamina" "Strength" "LongShots" "Aggression"
   "Interceptions" "Positioning" "Vision" "Penalties" "Composure"
   "Marking" "StandingTackle" "SlidingTackle" "GKDiving" "GKHandling"
   "GKKicking" "GKPositioning" "GKReflexes"])

(defn- load-players [dir]
  (for [m (read-csv (io/file dir "fifa_data.csv"))]
    {:id             (parse-num (m "ID"))
     :name           (m "Name")
     :name-norm      (str/lower-case (strip-accents (m "Name")))
     :age            (parse-num (m "Age"))
     :nationality    (m "Nationality")
     :overall        (parse-num (m "Overall"))
     :potential      (parse-num (m "Potential"))
     :club           (m "Club")
     :club-norm      (some-> (m "Club") not-empty strip-accents str/lower-case)
     :position       (m "Position")
     :jersey         (parse-num (m "Jersey Number"))
     :height         (m "Height")
     :weight         (m "Weight")
     :value          (m "Value")
     :wage           (m "Wage")
     :preferred-foot (m "Preferred Foot")
     :skills         (into (sorted-map)
                           (keep (fn [c]
                                   (when-let [v (parse-num (m c))]
                                     [c v])))
                           skill-columns)}))

(defn- dedupe-matches
  "Several files cover the same competition and seasons (e.g. Brasileirão
  2012-2019 appears in three datasets). For each [competition season] keep
  only the rows from the highest-priority source that has them."
  [matches]
  (->> matches
       (group-by (juxt :competition :season))
       vals
       (mapcat (fn [rows]
                 (let [best (apply min (map :priority rows))]
                   (filter #(= best (:priority %)) rows))))))

(defn- fill-missing-scores
  "Some rows in the primary Brasileirão file have NA scores (mostly late
  2022 fixtures). When the BR-Football dataset has the result for the same
  date and teams, fill it in."
  [matches extended]
  (let [;; join on date + base names: the two files suffix names differently
        join-key (fn [m] [(:date m) (get-in m [:home :base]) (get-in m [:away :base])])
        score-index (into {}
                          (for [m extended
                                :when (and (:date m) (:home-goals m) (:away-goals m))]
                            [(join-key m) [(:home-goals m) (:away-goals m)]]))]
    (mapv (fn [m]
            (if (or (:home-goals m) (nil? (:date m)))
              m
              ;; kickoff times near midnight shift the date by a day between
              ;; the two datasets, so probe the adjacent dates too
              (if-let [[hg ag] (some (fn [offset]
                                       (score-index
                                        (assoc (join-key m) 0
                                               (.plusDays ^LocalDate (:date m) offset))))
                                     [0 1 -1])]
                (assoc m :home-goals hg :away-goals ag)
                m)))
          matches)))

(defn load-data
  "Loads all six CSV files from `dir`. Returns
  {:matches [...] :extended [...] :players [...]}.
  :matches is the deduplicated cross-competition match list; :extended keeps
  every BR-Football row (with corners/shots stats) regardless of overlap."
  [dir]
  (let [extended (vec (load-extended dir))
        matches  (-> (dedupe-matches
                      (concat (load-brasileirao dir)
                              (load-historical dir)
                              (load-cup dir)
                              (load-libertadores dir)
                              extended))
                     (fill-missing-scores extended))]
    {:matches  matches
     :extended extended
     :players  (vec (load-players dir))}))

(def ^:dynamic *data-dir*
  (or (System/getenv "BRAZILIAN_SOCCER_DATA") "data/kaggle"))

(def db
  "Lazily-loaded singleton database used by the server and tests."
  (delay (load-data *data-dir*)))
