(ns soccer.data
  "Loading and normalizing the Kaggle CSV datasets."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]))

(def data-dir (or (System/getenv "SOCCER_DATA_DIR") "data/kaggle"))

;; ---------------------------------------------------------------- helpers

(defn strip-accents [s]
  (-> (Normalizer/normalize (str s) Normalizer$Form/NFD)
      (str/replace #"\p{M}" "")))

(def aliases
  "Normalized full/variant names -> canonical key."
  {"sport club corinthians paulista" "corinthians"
   "sociedade esportiva palmeiras" "palmeiras"
   "clube de regatas do flamengo" "flamengo"
   "fluminense football club" "fluminense"
   "sao paulo futebol clube" "sao paulo"
   "sao paulo fc" "sao paulo"
   "santos fc" "santos"
   "gremio foot-ball porto alegrense" "gremio"
   "sport club internacional" "internacional"
   "clube atletico mineiro" "atletico mineiro"
   "atletico-mg" "atletico mineiro"
   "atletico mg" "atletico mineiro"
   "atletico paranaense" "athletico paranaense"
   "athletico-pr" "athletico paranaense"
   "athletico pr" "athletico paranaense"
   "atletico-pr" "athletico paranaense"
   "atletico pr" "athletico paranaense"
   "atletico-go" "atletico goianiense"
   "atletico go" "atletico goianiense"
   "vasco da gama" "vasco"
   "cr vasco da gama" "vasco"
   "botafogo-rj" "botafogo"
   "botafogo rj" "botafogo"
   "america-mg" "america mineiro"
   "america mg" "america mineiro"
   "cruzeiro ec" "cruzeiro"
   "bragantino" "red bull bragantino"
   "rb bragantino" "red bull bragantino"
   "sport recife" "sport"
   "ceara sc" "ceara"
   "fortaleza ec" "fortaleza"
   "fortaleza esporte clube" "fortaleza"
   "ec bahia" "bahia"
   "esporte clube bahia" "bahia"
   "goias ec" "goias"
   "coritiba fc" "coritiba"
   "chapecoense-sc" "chapecoense"
   "avai fc" "avai"})

(def ^:private ambiguous-bases
  "Base names whose meaning depends on the state (e.g. Atletico-MG vs -PR)."
  #{"atletico" "america" "botafogo" "athletico"})

(def ^:private state-qualified
  {["atletico" "mg"] "atletico mineiro" ["atletico" "pr"] "athletico paranaense"
   ["athletico" "pr"] "athletico paranaense" ["atletico" "go"] "atletico goianiense"
   ["america" "mg"] "america mineiro" ["america" "rn"] "america rn"
   ["america" "rj"] "america rj" ["botafogo" "rj"] "botafogo"
   ["botafogo" "sp"] "botafogo sp" ["botafogo" "pb"] "botafogo pb"})

(defn team-key
  "Canonical lowercase, accent-free key used for matching team names across files.
  Handles 'Palmeiras-SP', 'América - MG', 'Nacional (URU)', full names, accents."
  [name]
  (let [s (-> (strip-accents name) str/lower-case str/trim
              (str/replace #"\(.*?\)" "") str/trim)
        [_ base st] (re-matches #"(.*?)\s*-\s*([a-z]{2,3})" s)
        base (str/trim (or base s))
        base (str/replace base #"\s+" " ")]
    (or (aliases s)
        (and st (state-qualified [base st]))
        (aliases base)
        base)))

(defn display-name
  "Human readable team name; the state suffix is dropped unless it is needed
  to disambiguate (Atlético-MG vs Atlético-PR)."
  [name]
  (let [s (-> (str name) (str/replace #"\s*\(.*?\)" "") str/trim)
        [_ base st] (re-matches #"(.*?)\s*-\s*([A-Z]{2,3})" s)
        base-key (some-> base strip-accents str/lower-case str/trim)]
    (cond (nil? base) s
          (ambiguous-bases base-key) (str base "-" st)
          :else base)))

(defn parse-int [s]
  (when-let [s (some-> s str/trim not-empty)]
    (try (int (Double/parseDouble s)) (catch Exception _ nil))))

(defn parse-date
  "Returns ISO yyyy-MM-dd string from ISO, ISO+time or DD/MM/YYYY formats."
  [s]
  (let [s (str/trim (str s))]
    (cond
      (re-find #"^\d{4}-\d{2}-\d{2}" s) (subs s 0 10)
      (re-find #"^\d{2}/\d{2}/\d{4}" s)
      (let [[d m y] (str/split (subs s 0 10) #"/")] (str y "-" m "-" d))
      :else nil)))

(defn read-csv [file]
  (with-open [r (io/reader (io/file data-dir file) :encoding "UTF-8")]
    (let [[header & rows] (doall (csv/read-csv r))
          header (map #(str/trim (str/replace % "﻿" "")) header)]
      (mapv #(zipmap header %) rows))))

(defn- match [m]
  (let [hg (:home-goal m) ag (:away-goal m)]
    (assoc m
           :home-key (team-key (:home m))
           :away-key (team-key (:away m))
           :home (display-name (:home m))
           :away (display-name (:away m))
           :result (cond (or (nil? hg) (nil? ag)) nil
                         (> hg ag) :home (< hg ag) :away :else :draw))))

;; ---------------------------------------------------------------- loaders

(defn load-brasileirao []
  (for [r (read-csv "Brasileirao_Matches.csv")]
    (match {:source "Brasileirao_Matches.csv" :competition "Brasileirão"
            :date (parse-date (r "datetime")) :season (parse-int (r "season"))
            :round (r "round") :home (r "home_team") :away (r "away_team")
            :home-goal (parse-int (r "home_goal")) :away-goal (parse-int (r "away_goal"))})))

(defn load-cup []
  (for [r (read-csv "Brazilian_Cup_Matches.csv")]
    (match {:source "Brazilian_Cup_Matches.csv" :competition "Copa do Brasil"
            :date (parse-date (r "datetime")) :season (parse-int (r "season"))
            :round (r "round") :home (r "home_team") :away (r "away_team")
            :home-goal (parse-int (r "home_goal")) :away-goal (parse-int (r "away_goal"))})))

(defn load-libertadores []
  (for [r (read-csv "Libertadores_Matches.csv")]
    (match {:source "Libertadores_Matches.csv" :competition "Copa Libertadores"
            :date (parse-date (r "datetime")) :season (parse-int (r "season"))
            :stage (r "stage") :home (r "home_team") :away (r "away_team")
            :home-goal (parse-int (r "home_goal")) :away-goal (parse-int (r "away_goal"))})))

(defn load-br-football []
  (for [r (read-csv "BR-Football-Dataset.csv")
        :let [t (r "tournament") d (parse-date (r "date"))]]
    (match {:source "BR-Football-Dataset.csv"
            :competition (case t "Serie A" "Brasileirão" "Serie B" "Brasileirão Série B"
                               "Serie C" "Brasileirão Série C" t)
            :date d :season (some-> d (subs 0 4) parse-int)
            :home (r "home") :away (r "away")
            :home-goal (parse-int (r "home_goal")) :away-goal (parse-int (r "away_goal"))
            :stats {:corners [(parse-int (r "home_corner")) (parse-int (r "away_corner"))]
                    :attacks [(parse-int (r "home_attack")) (parse-int (r "away_attack"))]
                    :shots [(parse-int (r "home_shots")) (parse-int (r "away_shots"))]}})))

(defn load-historical []
  (for [r (read-csv "novo_campeonato_brasileiro.csv")]
    (match {:source "novo_campeonato_brasileiro.csv" :competition "Brasileirão"
            :date (parse-date (r "Data")) :season (parse-int (r "Ano"))
            :round (r "Rodada") :home (r "Equipe_mandante") :away (r "Equipe_visitante")
            :home-goal (parse-int (r "Gols_mandante")) :away-goal (parse-int (r "Gols_visitante"))
            :arena (r "Arena")})))

(defn load-players []
  (vec (for [r (read-csv "fifa_data.csv")]
         {:id (r "ID") :name (r "Name") :age (parse-int (r "Age"))
          :nationality (r "Nationality") :overall (parse-int (r "Overall"))
          :potential (parse-int (r "Potential")) :club (r "Club")
          :club-key (when (seq (r "Club")) (team-key (r "Club")))
          :position (r "Position") :jersey (r "Jersey Number")
          :height (r "Height") :weight (r "Weight") :value (r "Value")
          :skills (into {} (for [k ["Crossing" "Finishing" "Dribbling" "ShortPassing"
                                    "Acceleration" "SprintSpeed" "Stamina" "Strength"]]
                             [k (parse-int (r k))]))})))

(defn load-all []
  (let [bra (vec (load-brasileirao)) cup (vec (load-cup)) lib (vec (load-libertadores))
        brf (vec (load-br-football)) his (vec (load-historical))]
    {:sources {:brasileirao bra :cup cup :libertadores lib :br-football brf :historical his}
     :matches (vec (concat bra cup lib brf his))
     :players (load-players)}))

(defonce ^:private db* (delay (load-all)))
(defn db [] @db*)
