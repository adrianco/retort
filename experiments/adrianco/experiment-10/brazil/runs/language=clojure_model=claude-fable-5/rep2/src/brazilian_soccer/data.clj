(ns brazilian-soccer.data
  "Loads the six Kaggle CSV datasets into a unified in-memory model.

  Matches from all five match files are normalized into maps with keys
  :competition :season :round :stage :date :home :away :home-goals
  :away-goals :stadium :source, where :home/:away are canonical team
  names (state suffixes stripped, accents restored, aliases merged).
  Overlapping files (Serie A appears in three of them) are deduplicated
  by [date home away competition].

  Players come from the FIFA dataset and keep their full attribute row
  under :raw for detailed lookups."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]))

(def data-dir
  (or (System/getenv "BRAZILIAN_SOCCER_DATA") "data/kaggle"))

(defn- read-csv-maps
  "Reads a CSV file into a vector of {header-string value-string} maps.
  Strips a UTF-8 BOM from the first header cell if present."
  [filename]
  (with-open [r (io/reader (io/file data-dir filename) :encoding "UTF-8")]
    (let [[header & rows] (csv/read-csv r)
          header (into [(str/replace (first header) "﻿" "")] (rest header))]
      (mapv #(zipmap header %) rows))))

;; ---------------------------------------------------------------------------
;; Team name normalization

(defn deaccent [s]
  (-> (java.text.Normalizer/normalize s java.text.Normalizer$Form/NFD)
      (str/replace #"\p{InCombiningDiacriticalMarks}+" "")))

(defn norm
  "Lowercase, accent-free, punctuation-free key form of a name."
  [s]
  (when s
    (-> s deaccent str/lower-case (str/replace #"[^a-z0-9]+" " ") str/trim)))

(def ^:private uf?
  #{"ac" "al" "ap" "am" "ba" "ce" "df" "es" "go" "ma" "mt" "ms" "mg"
    "pa" "pb" "pr" "pe" "pi" "rj" "rn" "rs" "ro" "rr" "sc" "sp" "se" "to"})

;; Base names shared by more than one club, where the state suffix is the
;; only disambiguator and must not be stripped automatically.
(def ^:private ambiguous-base
  #{"america" "atletico" "botafogo" "boavista" "bragantino" "fluminense"})

;; Known variants (in norm form) -> canonical display name. Covers every
;; top-flight club spelling found across the five match files plus the
;; long official names used by the Copa do Brasil file and FIFA data.
(def aliases
  {"sao paulo" "São Paulo" "sao paulo sp" "São Paulo" "sao paulo fc" "São Paulo"
   "sao paulo futebol clube" "São Paulo"
   "flamengo" "Flamengo" "flamengo rj" "Flamengo" "cr flamengo" "Flamengo"
   "clube de regatas do flamengo" "Flamengo"
   "fluminense" "Fluminense" "fluminense rj" "Fluminense"
   "fluminense fc" "Fluminense" "fluminense football club" "Fluminense"
   "botafogo" "Botafogo" "botafogo rj" "Botafogo" "botafogo fr" "Botafogo"
   "botafogo de futebol e regatas" "Botafogo"
   "vasco" "Vasco da Gama" "vasco da gama" "Vasco da Gama"
   "vasco da gama rj" "Vasco da Gama" "cr vasco da gama" "Vasco da Gama"
   "club de regatas vasco da gama" "Vasco da Gama"
   "palmeiras" "Palmeiras" "palmeiras sp" "Palmeiras" "se palmeiras" "Palmeiras"
   "sociedade esportiva palmeiras" "Palmeiras"
   "corinthians" "Corinthians" "corinthians sp" "Corinthians"
   "corinthians paulista" "Corinthians" "sc corinthians paulista" "Corinthians"
   "sport club corinthians paulista" "Corinthians"
   "santos" "Santos" "santos sp" "Santos" "santos fc" "Santos"
   "santos futebol clube" "Santos"
   "gremio" "Grêmio" "gremio rs" "Grêmio" "gremio fbpa" "Grêmio"
   "gremio foot ball porto alegrense" "Grêmio"
   "internacional" "Internacional" "internacional rs" "Internacional"
   "sc internacional" "Internacional" "sport club internacional" "Internacional"
   "atletico mineiro" "Atlético Mineiro" "atletico mg" "Atlético Mineiro"
   "clube atletico mineiro" "Atlético Mineiro"
   "athletico paranaense" "Athletico Paranaense"
   "atletico paranaense" "Athletico Paranaense"
   "atletico pr" "Athletico Paranaense" "athletico pr" "Athletico Paranaense"
   "club athletico paranaense" "Athletico Paranaense"
   "atletico goianiense" "Atlético Goianiense" "atletico go" "Atlético Goianiense"
   "atletico clube goianiense" "Atlético Goianiense"
   "america mg" "América-MG" "america mineiro" "América-MG"
   "america futebol clube mg" "América-MG"
   "america rn" "América-RN" "america fc natal" "América-RN"
   "america de natal" "América-RN"
   "bahia" "Bahia" "bahia ba" "Bahia" "ec bahia" "Bahia"
   "esporte clube bahia" "Bahia"
   "vitoria" "Vitória" "vitoria ba" "Vitória" "ec vitoria" "Vitória"
   "esporte clube vitoria" "Vitória"
   "fortaleza" "Fortaleza" "fortaleza ce" "Fortaleza" "fortaleza ec" "Fortaleza"
   "fortaleza fc" "Fortaleza" "fortaleza esporte clube" "Fortaleza"
   "juventude" "Juventude" "juventude rs" "Juventude" "ec juventude" "Juventude"
   "esporte clube juventude" "Juventude"
   "bragantino" "Red Bull Bragantino" "bragantino sp" "Red Bull Bragantino"
   "rb bragantino" "Red Bull Bragantino" "red bull bragantino" "Red Bull Bragantino"
   "red bull bragantino sp" "Red Bull Bragantino"
   "cuiaba" "Cuiabá" "cuiaba mt" "Cuiabá" "cuiaba ec" "Cuiabá"
   "coritiba" "Coritiba" "coritiba pr" "Coritiba" "coritiba fc" "Coritiba"
   "coritiba foot ball club" "Coritiba"
   "csa" "CSA" "csa al" "CSA" "cs alagoano" "CSA" "centro sportivo alagoano" "CSA"
   "avai" "Avaí" "avai sc" "Avaí" "avai fc" "Avaí" "avai futebol clube" "Avaí"
   "ceara" "Ceará" "ceara ce" "Ceará" "ceara sc" "Ceará"
   "ceara sporting club" "Ceará"
   "goias" "Goiás" "goias go" "Goiás" "goias ec" "Goiás"
   "goias esporte clube" "Goiás"
   "nautico" "Náutico" "nautico pe" "Náutico" "clube nautico capibaribe" "Náutico"
   "sport" "Sport Recife" "sport pe" "Sport Recife" "sport recife" "Sport Recife"
   "sport club do recife" "Sport Recife"
   "santa cruz" "Santa Cruz" "santa cruz pe" "Santa Cruz"
   "santa cruz fc" "Santa Cruz" "santa cruz futebol clube" "Santa Cruz"
   "chapecoense" "Chapecoense" "chapecoense sc" "Chapecoense"
   "associacao chapecoense de futebol" "Chapecoense"
   "criciuma" "Criciúma" "criciuma sc" "Criciúma" "criciuma ec" "Criciúma"
   "parana" "Paraná" "parana pr" "Paraná" "parana clube" "Paraná"
   "ponte preta" "Ponte Preta" "ponte preta sp" "Ponte Preta"
   "aa ponte preta" "Ponte Preta" "associacao atletica ponte preta" "Ponte Preta"
   "portuguesa" "Portuguesa" "portuguesa sp" "Portuguesa"
   "associacao portuguesa de desportos" "Portuguesa"
   "cruzeiro" "Cruzeiro" "cruzeiro mg" "Cruzeiro" "cruzeiro ec" "Cruzeiro"
   "cruzeiro esporte clube" "Cruzeiro"
   "figueirense" "Figueirense" "figueirense sc" "Figueirense"
   "figueirense fc" "Figueirense"
   "joinville" "Joinville" "joinville sc" "Joinville" "joinville ec" "Joinville"
   "guarani" "Guarani" "guarani sp" "Guarani" "guarani fc" "Guarani"
   "sao caetano" "São Caetano" "ad sao caetano" "São Caetano"
   "santo andre" "Santo André" "ec santo andre" "Santo André"
   "gremio prudente" "Grêmio Prudente"
   "barueri" "Grêmio Barueri" "gremio barueri" "Grêmio Barueri"
   "ipatinga" "Ipatinga" "ipatinga fc" "Ipatinga"
   "paysandu" "Paysandu" "paysandu sc" "Paysandu" "paysandu pa" "Paysandu"
   "brasiliense" "Brasiliense" "brasiliense df" "Brasiliense"})

(defn canonical-team
  "Maps any team-name variant to one canonical display name.
  Falls back to stripping a trailing state suffix when unambiguous,
  otherwise returns the trimmed original."
  [raw]
  (when-not (str/blank? (str raw))
    (let [raw  (str/trim raw)
          n    (norm raw)
          toks (str/split n #" ")]
      (or (aliases n)
          (when (and (> (count toks) 1) (uf? (peek toks)))
            (let [base (str/join " " (pop toks))]
              (when-not (ambiguous-base base)
                (or (aliases base)
                    (str/trim (str/replace raw #"(?iu)\s*-?\s*\(?[A-Za-z]{2}\)?$" ""))))))
          raw))))

(defn team-matches?
  "Does a user-supplied team query refer to this canonical team name?
  Exact canonical match, or query contained in the team name."
  [query team]
  (let [qn (norm (canonical-team query))
        tn (norm team)]
    (and (seq qn) (or (= qn tn) (str/includes? tn qn)))))

;; ---------------------------------------------------------------------------
;; Parsing helpers

(defn parse-date
  "Normalizes '2012-05-19 18:30:00', '2023-09-24' and '29/03/2003'
  to an ISO yyyy-MM-dd string (lexicographically sortable). Nil if unparseable."
  [s]
  (when s
    (let [s (str/trim s)]
      (cond
        (re-find #"^\d{4}-\d{2}-\d{2}" s)
        (subs s 0 10)
        (re-matches #"\d{2}/\d{2}/\d{4}" s)
        (let [[d m y] (str/split s #"/")] (str y "-" m "-" d))
        :else nil))))

(defn parse-num
  "Parses '2', '2.0' -> 2 (long). Nil for blank/NA/garbage."
  [s]
  (when (and s (not (str/blank? s)) (not= "NA" (str/upper-case (str/trim s))))
    (try (long (Double/parseDouble (str/trim s)))
         (catch NumberFormatException _ nil))))

;; ---------------------------------------------------------------------------
;; Match loaders (one per CSV)

(defn- season-of [season-str date]
  (or (parse-num season-str)
      (some-> date (subs 0 4) parse-num)))

(defn load-brasileirao []
  (for [row (read-csv-maps "Brasileirao_Matches.csv")
        :let [date (parse-date (row "datetime"))]]
    {:competition "Brasileirão Série A"
     :season      (season-of (row "season") date)
     :round       (parse-num (row "round"))
     :date        date
     :home        (canonical-team (row "home_team"))
     :away        (canonical-team (row "away_team"))
     :home-goals  (parse-num (row "home_goal"))
     :away-goals  (parse-num (row "away_goal"))
     :source      "Brasileirao_Matches.csv"}))

(defn load-historical []
  (for [row (read-csv-maps "novo_campeonato_brasileiro.csv")
        :let [date (parse-date (row "Data"))]]
    {:competition "Brasileirão Série A"
     :season      (season-of (row "Ano") date)
     :round       (parse-num (row "Rodada"))
     :date        date
     :home        (canonical-team (row "Equipe_mandante"))
     :away        (canonical-team (row "Equipe_visitante"))
     :home-goals  (parse-num (row "Gols_mandante"))
     :away-goals  (parse-num (row "Gols_visitante"))
     :stadium     (let [a (row "Arena")] (when-not (str/blank? a) (str/trim a)))
     :source      "novo_campeonato_brasileiro.csv"}))

(defn load-cup []
  (let [rows    (read-csv-maps "Brazilian_Cup_Matches.csv")
        matches (for [row rows
                      :let [date (parse-date (row "datetime"))]]
                  {:competition "Copa do Brasil"
                   :season      (season-of (row "season") date)
                   :round       (parse-num (row "round"))
                   :date        date
                   :home        (canonical-team (row "home_team"))
                   :away        (canonical-team (row "away_team"))
                   :home-goals  (parse-num (row "home_goal"))
                   :away-goals  (parse-num (row "away_goal"))
                   :source      "Brazilian_Cup_Matches.csv"})
        ;; The cup file only has numeric rounds; the highest round of each
        ;; season is the final (two-legged), so tag it as a stage.
        finals  (reduce (fn [m {:keys [season round]}]
                          (if (and season round)
                            (update m season (fnil max 0) round)
                            m))
                        {} matches)]
    (map (fn [{:keys [season round] :as m}]
           (if (and season round (= round (finals season)))
             (assoc m :stage "final")
             m))
         matches)))

(defn load-libertadores []
  (for [row (read-csv-maps "Libertadores_Matches.csv")
        :let [date (parse-date (row "datetime"))]]
    {:competition "Copa Libertadores"
     :season      (season-of (row "season") date)
     :stage       (let [s (row "stage")] (when-not (str/blank? s) (str/trim s)))
     :date        date
     :home        (canonical-team (row "home_team"))
     :away        (canonical-team (row "away_team"))
     :home-goals  (parse-num (row "home_goal"))
     :away-goals  (parse-num (row "away_goal"))
     :source      "Libertadores_Matches.csv"}))

(def ^:private brf-competition
  {"Serie A"        "Brasileirão Série A"
   "Serie B"        "Brasileirão Série B"
   "Serie C"        "Brasileirão Série C"
   "Copa do Brasil" "Copa do Brasil"})

(defn load-extended []
  (for [row (read-csv-maps "BR-Football-Dataset.csv")
        :let [date (parse-date (row "date"))]]
    {:competition  (get brf-competition (row "tournament") (row "tournament"))
     :season       (some-> date (subs 0 4) parse-num)
     :date         date
     :home         (canonical-team (row "home"))
     :away         (canonical-team (row "away"))
     :home-goals   (parse-num (row "home_goal"))
     :away-goals   (parse-num (row "away_goal"))
     :home-corners (parse-num (row "home_corner"))
     :away-corners (parse-num (row "away_corner"))
     :home-shots   (parse-num (row "home_shots"))
     :away-shots   (parse-num (row "away_shots"))
     :source       "BR-Football-Dataset.csv"}))

(defn- epoch-day [iso-date]
  (.toEpochDay (java.time.LocalDate/parse iso-date)))

(defn- dedupe-matches
  "Several files cover the same Série A / Copa do Brasil fixtures, and the
  BR-Football dataset records kick-off dates one day later than the primary
  files (timezone differences). A match is a duplicate when an already-kept
  match has the same competition and home/away pair within 3 days. Loaders
  are concatenated in priority order, so the richer primary files win.
  Matches without a parseable date are always kept.

  When the kept match is missing its score and the duplicate has one
  (the primary 2022 file lists late-season fixtures without results),
  the duplicate's score is merged into the kept match."
  [matches]
  (let [out (java.util.ArrayList.)]
    (reduce
     (fn [seen m]
       (let [k   [(:competition m) (norm (:home m)) (norm (:away m))]
             day (some-> (:date m) epoch-day)
             hit (when day
                   (some (fn [[kept-day idx]]
                           (let [delta (abs (- day kept-day))]
                             ;; Same fixture within 3 days, or a rescheduled
                             ;; fixture: one row has no score and the dates
                             ;; are within a month.
                             (when (or (<= delta 3)
                                       (and (<= delta 30)
                                            (or (nil? (:home-goals (.get out idx)))
                                                (nil? (:home-goals m)))))
                               idx)))
                         (get seen k)))]
         (if hit
           (let [kept (.get out hit)]
             (when (and (nil? (:home-goals kept)) (:home-goals m))
               ;; The scored row carries the date the match was actually
               ;; played (vs. the originally scheduled date), so take both.
               (.set out hit (assoc kept
                                    :home-goals (:home-goals m)
                                    :away-goals (:away-goals m)
                                    :date (or (:date m) (:date kept)))))
             seen)
           (do (.add out m)
               (cond-> seen
                 day (update k (fnil conj []) [day (dec (.size out))]))))))
     {} matches)
    (vec out)))

(def all-matches
  "All matches from the five match CSVs, deduplicated, sorted by date."
  (delay (vec (sort-by #(or (:date %) "")
                       (dedupe-matches
                        (concat (load-brasileirao) (load-historical) (load-cup)
                                (load-libertadores) (load-extended)))))))

;; ---------------------------------------------------------------------------
;; FIFA players

(def ^:private skill-columns
  ["Crossing" "Finishing" "HeadingAccuracy" "ShortPassing" "Volleys"
   "Dribbling" "Curve" "FKAccuracy" "LongPassing" "BallControl"
   "Acceleration" "SprintSpeed" "Agility" "Reactions" "Balance"
   "ShotPower" "Jumping" "Stamina" "Strength" "LongShots" "Aggression"
   "Interceptions" "Positioning" "Vision" "Penalties" "Composure"
   "Marking" "StandingTackle" "SlidingTackle"
   "GKDiving" "GKHandling" "GKKicking" "GKPositioning" "GKReflexes"])

(defn load-players []
  (for [row (read-csv-maps "fifa_data.csv")]
    {:id          (row "ID")
     :name        (row "Name")
     :age         (parse-num (row "Age"))
     :nationality (row "Nationality")
     :overall     (parse-num (row "Overall"))
     :potential   (parse-num (row "Potential"))
     :club        (let [c (row "Club")] (when-not (str/blank? c) c))
     :position    (let [p (row "Position")] (when-not (str/blank? p) p))
     :jersey      (parse-num (row "Jersey Number"))
     :value       (row "Value")
     :wage        (row "Wage")
     :height      (row "Height")
     :weight      (row "Weight")
     :foot        (row "Preferred Foot")
     :skills      (into {} (keep (fn [c]
                                   (when-let [v (parse-num (row c))]
                                     [c v]))
                                 skill-columns))}))

(def all-players
  "All FIFA players, sorted by overall rating descending."
  (delay (vec (sort-by #(- (or (:overall %) 0)) (load-players)))))
