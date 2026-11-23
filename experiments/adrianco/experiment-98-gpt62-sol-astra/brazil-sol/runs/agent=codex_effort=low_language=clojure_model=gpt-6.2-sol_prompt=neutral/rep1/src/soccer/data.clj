(ns soccer.data
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]
           [java.time LocalDate]
           [java.time.format DateTimeFormatter DateTimeParseException ResolverStyle]))

(defn fold [s]
  (-> (Normalizer/normalize (or s "") Normalizer$Form/NFD)
      (str/replace #"\p{M}" "") str/lower-case str/trim))

(def team-aliases
  (into {}
        (mapcat (fn [[team & aliases]] (map #(vector % team) (cons team aliases))))
        [["flamengo" "clube de regatas do flamengo" "cr flamengo" "flamengo rj"]
         ["fluminense" "fluminense football club" "fluminense rj"]
         ["corinthians" "sport club corinthians paulista" "sc corinthians paulista"]
         ["palmeiras" "sociedade esportiva palmeiras" "se palmeiras"]
         ["santos" "santos fc" "santos futebol clube"]
         ["sao paulo" "sao paulo fc" "sao paulo futebol clube"]
         ["vasco" "vasco da gama" "vasco da gama rj" "cr vasco da gama"]
         ["gremio" "gremio rs" "gremio fbpa"]
         ["internacional" "internacional rs" "sport club internacional" "sc internacional"]
         ["atletico mg" "atletico mineiro" "clube atletico mineiro"]
         ["atletico go" "atletico goianiense" "atletico clube goianiense"]
         ["athletico pr" "atletico pr" "athletico" "athletico paranaense"
          "atletico paranaense" "club athletico paranaense"]
         ["america mg" "america mineiro" "america fc minas gerais" "america mg belo horizonte"]
         ["america rn" "america fc natal"]
         ["botafogo" "botafogo rj" "botafogo fr" "botafogo de futebol e regatas"]
         ["bahia" "ec bahia" "esporte clube bahia"]
         ["vitoria" "ec vitoria" "esporte clube vitoria"]
         ["sport" "sport recife" "sport club do recife" "sport club recife"]
         ["ceara" "ceara sporting club" "ceara sc"]
         ["fortaleza" "fortaleza ec" "fortaleza esporte clube" "fortaleza fc"]
         ["csa" "cs alagoano" "centro sportivo alagoano"]
         ["bragantino" "red bull bragantino" "ca bragantino"]
         ["parana" "ca parana" "parana clube"]
         ["portuguesa" "portuguesa desportos" "associacao portuguesa de desportos"]
         ["nautico" "nautico capibaribe"]
         ["juventude" "ec juventude"]
         ["cuiaba" "cuiaba mt" "cuiaba ec"]
         ["coritiba" "coritiba pr" "coritiba fc"]
         ["guarani" "guarani sp" "guarani fc"]
         ["santa cruz" "santa cruz fc"]]))

(defn team-id [s]
  (let [text (fold s)
        [_ base state] (re-matches #"(.*?)\s*-\s*(ac|al|ap|am|ba|ce|df|es|go|ma|mt|ms|mg|pa|pb|pr|pe|pi|rj|rn|rs|ro|rr|sc|sp|se|to)" text)
        clean #(-> % (str/replace #"[^a-z0-9]+" " ") str/trim)
        full (clean text)]
    (or (team-aliases full)
        (when base
          (let [base (clean base)]
            (if (contains? #{"america" "atletico" "botafogo" "santos" "portuguesa"
                             "operario" "rio branco" "nacional" "santa cruz"} base)
              (if (contains? #{["santos" "sp"] ["portuguesa" "sp"] ["santa cruz" "pe"]} [base state])
                base full)
              (get team-aliases base base))))
        full)))

(defn competition-id [s]
  (case (fold s)
    ("serie a" "brasileirao" "brasileirao serie a" "campeonato brasileiro" "serie-a") "Brasileirão Série A"
    ("serie b" "brasileirao serie b" "serie-b") "Brasileirão Série B"
    ("serie c" "brasileirao serie c" "serie-c") "Brasileirão Série C"
    ("copa do brasil" "brazilian cup") "Copa do Brasil"
    ("copa libertadores" "libertadores") "Copa Libertadores"
    s))

(def brazilian-date
  (.withResolverStyle (DateTimeFormatter/ofPattern "d/M/uuuu") ResolverStyle/STRICT))

(defn parse-date [s]
  (when-not (contains? #{nil "" "NA"} s)
    (let [date (first (str/split s #"[ T]" 2))]
      (try
        (if (str/includes? date "/")
          (LocalDate/parse date brazilian-date)
          (LocalDate/parse date))
        (catch DateTimeParseException _
          (throw (ex-info (str "Invalid date: " s) {:date s})))))))

(defn number-value [s]
  (when (and s (re-matches #"-?\d+(?:\.\d+)?" s))
    (if (str/includes? s ".")
      (let [n (parse-double s)] (if (== n (long n)) (long n) n))
      (parse-long s))))

(def files
  ["Brasileirao_Matches.csv" "Brazilian_Cup_Matches.csv" "Libertadores_Matches.csv"
   "novo_campeonato_brasileiro.csv" "BR-Football-Dataset.csv" "fifa_data.csv"])

(defn read-rows [directory file]
  (with-open [reader (io/reader (io/file directory file) :encoding "UTF-8")]
    (let [[header & rows] (csv/read-csv reader)]
      (mapv #(zipmap header %) rows))))

(def cup-finals
  {2012 6, 2013 8, 2014 8, 2015 8, 2016 7, 2017 8, 2018 8, 2019 8, 2020 8})

(def extended-finals
  {"2021-12-12" 2021, "2021-12-16" 2021, "2022-10-13" 2022,
   "2022-10-20" 2022, "2023-09-17" 2023, "2023-09-24" 2023})

(def extended-stats
  ["home_corner" "away_corner" "home_attack" "away_attack" "home_shots" "away_shots"
   "ht_diff" "at_diff" "ht_result" "at_result" "total_corners"])

(defn match-row [source row]
  (let [historical? (= source "novo_campeonato_brasileiro.csv")
        extended? (= source "BR-Football-Dataset.csv")
        competition (competition-id
                     (case source
                       "Brazilian_Cup_Matches.csv" "Copa do Brasil"
                       "Libertadores_Matches.csv" "Copa Libertadores"
                       "BR-Football-Dataset.csv" (row "tournament")
                       "Serie A"))
        home (or (row "home_team") (row "Equipe_mandante") (row "home"))
        away (or (row "away_team") (row "Equipe_visitante") (row "away"))
        date (parse-date (or (row "datetime") (row "Data") (row "date")))
        time (or (row "time") (second (str/split (or (row "datetime") "") #" " 2)))
        season (or (number-value (or (row "season") (row "Ano"))) (some-> date .getYear))
        round (number-value (or (row "round") (row "Rodada")))
        stage (or (row "stage")
                  (when (and (= competition "Copa do Brasil")
                             (if extended?
                               (= season (get extended-finals (str date) -1))
                               (and round (= round (cup-finals season)))))
                    "final"))]
    (cond-> {:date (some-> date str) :time time :season season :round round :stage stage
             :competition competition :home home :away away
             :home-id (team-id home) :away-id (team-id away)
             :home-goals (number-value (or (row "home_goal") (row "Gols_mandante")))
             :away-goals (number-value (or (row "away_goal") (row "Gols_visitante")))
             :home-state (or (row "home_team_state") (row "Mandante_UF"))
             :away-state (or (row "away_team_state") (row "Visitante_UF"))
             :sources [source]}
      historical? (assoc :stadium (row "Arena") :source-id (row "ID") :notes (row "OBS"))
      extended? (assoc :extended-statistics
                       (into {} (keep (fn [key]
                                        (let [value (row key)]
                                          (when-not (str/blank? value)
                                            [key (or (number-value value) value)]))))
                             extended-stats)))))

(defn fixture-key [match]
  ((juxt :competition :home-id :away-id) match))

(defn merge-fixture [old match]
  (-> (merge (into {} (remove (comp nil? val)) match)
             (into {} (remove (comp nil? val)) old))
      (assoc :sources (into (:sources old) (:sources match)))))

(defn distance [first-date second-date]
  (if (and first-date second-date)
    (abs (- (.toEpochDay (LocalDate/parse first-date))
            (.toEpochDay (LocalDate/parse second-date))))
    Long/MAX_VALUE))

(defn consolidate [matches]
  (->> matches
       (reduce
        (fn [fixtures match]
          (let [key (fixture-key match)
                candidates (get fixtures key [])
                league? (= "Brasileirão Série A" (:competition match))
                index (->> candidates
                           (keep-indexed
                            (fn [index candidate]
                              (when-not (some #{(first (:sources match))} (:sources candidate))
                                (let [days (distance (:date candidate) (:date match))]
                                  (when (or (<= days 2)
                                            (and league? (= (:season candidate) (:season match))
                                                 ;; The 2020 season ran into February 2021.
                                                 (or (:round match)
                                                     (not (re-find #"^2021-0[12]" (or (:date match) ""))))))
                                    [days index])))))
                           sort first second)]
            (assoc fixtures key (if (some? index)
                                  (update candidates index merge-fixture match)
                                  (conj candidates match)))))
        {})
       vals (mapcat identity)
       (sort-by (juxt :date :competition :home-id :away-id :time)
                #(compare %2 %1)) vec))

(defn expected-serie-a-matches [season]
  (case season
    (2003 2004) 552
    2005 462
    (when (and season (>= season 2006)) 380)))

(defn exclude-unmatched-league-rows [fixtures]
  (let [extended "BR-Football-Dataset.csv"
        league (filter #(= "Brasileirão Série A" (:competition %)) fixtures)
        complete-seasons (into #{}
                               (keep (fn [[season games]]
                                       (when (= (count games) (expected-serie-a-matches season))
                                         season)))
                               (group-by :season (remove #(= [extended] (:sources %)) league)))]
    (filterv #(not (and (= "Brasileirão Série A" (:competition %))
                        (= [extended] (:sources %))
                        (contains? complete-seasons (:season %))))
             fixtures)))

(defn load-data
  ([] (load-data "data/kaggle"))
  ([directory]
   (let [matches (into {} (for [file (butlast files)]
                            [file (mapv #(match-row file %) (read-rows directory file))]))
         combined (exclude-unmatched-league-rows (consolidate (mapcat matches (butlast files))))
         players (->> (read-rows directory (last files))
                      (mapv (fn [row]
                              {:id (number-value (row "ID")) :name (row "Name")
                               :age (number-value (row "Age")) :nationality (row "Nationality")
                               :club (row "Club") :club-id (team-id (row "Club"))
                               :position (row "Position") :overall (number-value (row "Overall"))
                               :potential (number-value (row "Potential"))
                               :attributes (into {} (keep (fn [[key value]]
                                                            (when (and (not (str/blank? value))
                                                                       (not (str/includes? key "\uFEFF")))
                                                              [key (or (number-value value) value)]))) row)}))
                      (sort-by (juxt (comp - #(or % 0) :overall) :name :id)) vec)]
     {:matches combined :sources matches :players players
      :domestic-clubs (into #{} (mapcat (juxt :home-id :away-id))
                           (remove #(= "Copa Libertadores" (:competition %)) combined))})))
