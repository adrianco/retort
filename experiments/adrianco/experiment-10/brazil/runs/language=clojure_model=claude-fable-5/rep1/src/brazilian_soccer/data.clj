(ns brazilian-soccer.data
  "CONTEXT
  =======
  Data layer for the Brazilian Soccer MCP server.

  Loads the six Kaggle CSV files from data/kaggle/ into a single in-memory
  database with a unified match schema and a player table:

    match:  {:competition :source :date (LocalDate) :season :round :stage
             :home-raw :away-raw :home :away (canonical ids)
             :home-goals :away-goals :extra}
    player: {:name :norm-name :age :nationality :overall :potential
             :club :norm-club :position :jersey :height :weight :value :wage}

  The five match files overlap (e.g. Serie A 2014-2019 appears in three
  files), use different team-name conventions (\"Palmeiras-SP\", \"Palmeiras\",
  \"Sport Club Corinthians Paulista\") and different date formats (ISO,
  DD/MM/YYYY, with/without time).  This namespace:

    * normalizes team names to canonical ids (accent-stripping, state-suffix
      handling, an alias table for known variants such as
      \"Vasco da Gama\" -> \"vasco\" and \"Atletico Mineiro\" -> \"atletico-mg\")
    * parses all date formats into java.time.LocalDate
    * de-duplicates overlapping matches across files (league matches by
      [competition season home away], cup matches additionally by date),
      preferring rows that have final scores

  Entry point: (db) returns the lazily-loaded, cached database map
    {:matches [...] :players [...] :file-counts {...} :display-names {...}}.

  Data directory defaults to \"data/kaggle\"; override with the
  BRAZILIAN_SOCCER_DATA environment variable."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str])
  (:import (java.text Normalizer Normalizer$Form)
           (java.time LocalDate)
           (java.time.format DateTimeFormatter)))

;; ---------------------------------------------------------------------------
;; Generic parsing helpers

(defn parse-long* "Parse a long, tolerating floats like \"1.0\"; nil on failure."
  [s]
  (when (and s (not (str/blank? s)))
    (let [t (str/trim s)]
      (try
        (Long/parseLong t)
        (catch Exception _
          (try
            (long (Double/parseDouble t))
            (catch Exception _ nil)))))))

(def ^:private iso-date (DateTimeFormatter/ofPattern "yyyy-MM-dd"))
(def ^:private br-date (DateTimeFormatter/ofPattern "dd/MM/yyyy"))

(defn parse-date
  "Parse \"2023-09-24\", \"2012-05-19 18:30:00\" or \"29/03/2003\" into a
  LocalDate; nil when unparseable (e.g. \"NA\")."
  [s]
  (when (and s (not (str/blank? s)))
    (let [t (str/trim s)
          d (if (>= (count t) 10) (subs t 0 10) t)]
      (or (try (LocalDate/parse d iso-date) (catch Exception _ nil))
          (try (LocalDate/parse d br-date) (catch Exception _ nil))))))

(defn strip-accents [s]
  (-> (Normalizer/normalize s Normalizer$Form/NFD)
      (str/replace #"\p{M}" "")))

;; ---------------------------------------------------------------------------
;; Team-name normalization
;;
;; Raw names vary across files: "Flamengo-RJ", "Flamengo", "Flamengo - RJ",
;; "Atletico Mineiro", "Atlético - MG", "Vasco da Gama RJ", "Vasco",
;; "Nacional (URU)", "Barcelona-EQU" ...  We reduce every raw name to a
;; canonical id so the same club gets the same id in every file.

(def ^:private br-states
  #{"ac" "al" "ap" "am" "ba" "ce" "df" "es" "go" "ma" "mt" "ms" "mg" "pa"
    "pb" "pr" "pe" "pi" "rj" "rn" "rs" "ro" "rr" "sc" "sp" "se" "to"})

;; Full normalized base names that map straight to a canonical id, applied
;; before any state-suffix logic.  Keys must be accent-free and lowercase.
(def ^:private fullname-aliases
  {"atletico mineiro"               "atletico-mg"
   "atletico goianiense"            "atletico-go"
   "atletico paranaense"            "athletico-pr"
   "athletico paranaense"           "athletico-pr"
   "athletico"                      "athletico-pr"
   "america mineiro"                "america-mg"
   "america natal"                  "america-rn"
   "america de natal"               "america-rn"
   "vasco da gama"                  "vasco"
   "vasco"                          "vasco"
   "sport recife"                   "sport-pe"
   "sport club do recife"           "sport-pe"
   "sport club corinthians paulista" "corinthians"
   "sociedade esportiva palmeiras"  "palmeiras"
   "red bull bragantino"            "bragantino-sp"
   "flamengo do piaui"              "flamengo-pi"
   "atletico cearense"              "atletico-ce"
   "gremio novorizontino"           "novorizontino"
   "novorizontino"                  "novorizontino"})

;; Bases where a state suffix distinguishes different clubs, so the state is
;; kept as part of the canonical id ("botafogo-rj" vs "botafogo-pb").
(def ^:private keep-state-bases
  #{"america" "atletico" "athletico" "botafogo" "bragantino" "flamengo"
    "fluminense" "santos" "juventude" "internacional" "nacional" "sport"
    "operario" "ferroviario" "guarani" "sao raimundo" "river" "central"})

;; Default canonical id for a kept-state base appearing without a state.
;; The bare name in these datasets always refers to the famous top-flight club.
(def ^:private bare-defaults
  {"atletico"      "atletico"        ; genuinely ambiguous, keep as-is
   "america"       "america"
   "botafogo"      "botafogo-rj"
   "flamengo"      "flamengo-rj"
   "fluminense"    "fluminense-rj"
   "santos"        "santos-sp"
   "juventude"     "juventude-rs"
   "internacional" "internacional-rs"
   "bragantino"    "bragantino-sp"
   "sport"         "sport-pe"
   "guarani"       "guarani-sp"})

(defn- parse-team
  "Split a raw team name into a normalized base and an optional qualifier
  (Brazilian state or 3-letter country code)."
  [raw]
  (let [s        (strip-accents (str raw))
        ;; capture a parenthesized country code, e.g. \"Nacional (URU)\"
        country  (some-> (re-find #"\(([A-Za-z]{3})\)" s) second str/lower-case)
        s        (str/replace s #"\([^)]*\)" " ")
        s        (str/lower-case s)
        s        (str/replace s #"[^a-z0-9]+" " ")
        tokens   (-> s str/trim (str/split #"\s+"))
        ;; drop club-form noise tokens: "EC Bahia", "Fortaleza FC", "America FC Natal"
        tokens   (let [t (remove #{"ec" "fc"} tokens)]
                   (if (seq t) (vec t) (vec tokens)))
        last-tok (peek tokens)
        state?   (and (> (count tokens) 1) (contains? br-states last-tok))
        country? (and (> (count tokens) 1) (nil? country)
                      (re-matches #"[a-z]{3}" (or last-tok ""))
                      (contains? #{"arg" "uru" "chi" "col" "equ" "ecu" "par"
                                   "per" "bol" "ven" "mex" "bra"} last-tok))
        qual     (cond state? last-tok
                       country? last-tok
                       :else country)
        base     (str/join " " (if (or state? country?) (pop tokens) tokens))]
    {:base base :qual qual}))

;; Applied to the assembled canonical id as a last step, for clubs whose
;; state-suffixed form still differs across files.
(def ^:private final-aliases
  {"atletico-pr" "athletico-pr"})

(defn canonical-team
  "Canonical id for a raw team name; same club -> same id across all files."
  [raw]
  (let [{:keys [base qual]} (parse-team raw)
        canon (or (get fullname-aliases base)
                  (when (and qual (contains? keep-state-bases base))
                    (str base "-" qual))
                  (when (and qual (not (contains? br-states qual)))
                    ;; foreign clubs keep their country, e.g. nacional-uru
                    (str base "-" qual))
                  (get bare-defaults base)
                  base)]
    (get final-aliases canon canon)))

;; ---------------------------------------------------------------------------
;; CSV loading

(defn data-dir []
  (or (System/getenv "BRAZILIAN_SOCCER_DATA") "data/kaggle"))

(defn read-csv
  "Read a CSV file into a vector of {column-name value} maps (string keys).
  Strips a UTF-8 BOM from the first header cell if present."
  [file]
  (with-open [r (io/reader file :encoding "UTF-8")]
    (let [[header & rows] (csv/read-csv r)
          header (mapv #(str/replace % "﻿" "") header)]
      (mapv #(zipmap header %) rows))))

(def source-priority
  "When de-duplicating, lower wins (after 'has final score' ranking)."
  {:brasileirao 0 :cup 1 :libertadores 2 :historical 3 :extended 4})

(defn- ->match [source competition row {:keys [date season round stage home away
                                               home-goals away-goals extra]}]
  (let [d (parse-date date)]
    {:source source
     :competition competition
     :date d
     :season (or (parse-long* season) (some-> d .getYear))
     :round round
     :stage stage
     :home-raw home
     :away-raw away
     :home (canonical-team home)
     :away (canonical-team away)
     :home-goals (parse-long* home-goals)
     :away-goals (parse-long* away-goals)
     :extra (or extra {})
     :row row}))

(defn load-brasileirao [dir]
  (for [r (read-csv (io/file dir "Brasileirao_Matches.csv"))]
    (->match :brasileirao "Brasileirão Série A" nil
             {:date (r "datetime") :season (r "season") :round (r "round")
              :home (r "home_team") :away (r "away_team")
              :home-goals (r "home_goal") :away-goals (r "away_goal")
              :extra {:home-state (r "home_team_state")
                      :away-state (r "away_team_state")}})))

(defn load-cup [dir]
  (for [r (read-csv (io/file dir "Brazilian_Cup_Matches.csv"))]
    (->match :cup "Copa do Brasil" nil
             {:date (r "datetime") :season (r "season") :round (r "round")
              :home (r "home_team") :away (r "away_team")
              :home-goals (r "home_goal") :away-goals (r "away_goal")})))

(defn load-libertadores [dir]
  (for [r (read-csv (io/file dir "Libertadores_Matches.csv"))]
    (->match :libertadores "Copa Libertadores" nil
             {:date (r "datetime") :season (r "season") :stage (r "stage")
              :home (r "home_team") :away (r "away_team")
              :home-goals (r "home_goal") :away-goals (r "away_goal")})))

(defn load-historical [dir]
  (for [r (read-csv (io/file dir "novo_campeonato_brasileiro.csv"))]
    (->match :historical "Brasileirão Série A" nil
             {:date (r "Data") :season (r "Ano") :round (r "Rodada")
              :home (r "Equipe_mandante") :away (r "Equipe_visitante")
              :home-goals (r "Gols_mandante") :away-goals (r "Gols_visitante")
              :extra {:arena (r "Arena") :winner (r "Vencedor")
                      :home-state (r "Mandante_UF") :away-state (r "Visitante_UF")}})))

(def ^:private extended-competitions
  {"Serie A" "Brasileirão Série A"
   "Serie B" "Brasileirão Série B"
   "Serie C" "Brasileirão Série C"
   "Copa do Brasil" "Copa do Brasil"})

(defn- league-season
  "Season for a league match identified only by date.  The Brasileirão runs
  April-December (the COVID-delayed 2020 season finished in February 2021),
  so league matches dated January-March belong to the previous season."
  [date league?]
  (when date
    (if (and league? (<= (.getMonthValue ^LocalDate date) 3))
      (dec (.getYear ^LocalDate date))
      (.getYear ^LocalDate date))))

(defn load-extended [dir]
  (for [r (read-csv (io/file dir "BR-Football-Dataset.csv"))]
    (->match :extended
             (get extended-competitions (r "tournament") (r "tournament"))
             nil
             {:date (r "date")
              :season (str (league-season (parse-date (r "date"))
                                          (str/starts-with? (str (r "tournament")) "Serie")))
              :home (r "home") :away (r "away")
              :home-goals (r "home_goal") :away-goals (r "away_goal")
              :extra {:home-corners (parse-long* (r "home_corner"))
                      :away-corners (parse-long* (r "away_corner"))
                      :home-shots   (parse-long* (r "home_shots"))
                      :away-shots   (parse-long* (r "away_shots"))
                      :ht-result    (r "ht_result")
                      :kickoff      (r "time")}})))

(defn load-players [dir]
  (for [r (read-csv (io/file dir "fifa_data.csv"))]
    {:name        (r "Name")
     :norm-name   (str/lower-case (strip-accents (str (r "Name"))))
     :age         (parse-long* (r "Age"))
     :nationality (r "Nationality")
     :overall     (parse-long* (r "Overall"))
     :potential   (parse-long* (r "Potential"))
     :club        (r "Club")
     :norm-club   (str/lower-case (strip-accents (str (r "Club"))))
     :position    (r "Position")
     :jersey      (parse-long* (r "Jersey Number"))
     :height      (r "Height")
     :weight      (r "Weight")
     :value       (r "Value")
     :wage        (r "Wage")}))

;; ---------------------------------------------------------------------------
;; De-duplication of overlapping match files

(defn- league? [m] (str/starts-with? (str (:competition m)) "Brasileirão"))

(defn dedupe-key
  "League seasons are round-robin: an ordered home/away pairing occurs once a
  season, so [comp season home away] identifies a match across files even
  when the recorded dates disagree.  Cups can repeat pairings, so include the
  date there."
  [m]
  (if (league? m)
    [(:competition m) (:season m) (:home m) (:away m)]
    [(:competition m) (:season m) (:home m) (:away m) (:date m)]))

(defn dedupe-matches
  "Collapse matches recorded in several files.  Within each dedupe-key group,
  keep every row from the single best source (most rows with final scores,
  then source priority) — a fixture can legitimately repeat under one key
  (e.g. Botafogo hosted Flamengo twice in 2009), so we never drop same-source
  rows, only other files' copies."
  [matches]
  (let [scored? #(and (:home-goals %) (:away-goals %))]
    (->> matches
         (group-by dedupe-key)
         vals
         (mapcat (fn [rows]
                   (if (= 1 (count rows))
                     rows
                     (->> (group-by :source rows)
                          (sort-by (fn [[src rs]]
                                     [(- (count (filter scored? rs)))
                                      (source-priority src 9)]))
                          first
                          val
                          ;; the source files themselves contain occasional
                          ;; doubled rows (same fixture and score, dates a day
                          ;; or two apart) — keep the earliest
                          (sort-by #(or (:date %) LocalDate/MIN))
                          (reduce (fn [acc m]
                                    (let [k [(:home-goals m) (:away-goals m)]]
                                      (if (contains? (:seen acc) k)
                                        acc
                                        (-> acc
                                            (update :seen conj k)
                                            (update :out conj m)))))
                                  {:seen #{} :out []})
                          :out))))
         (sort-by #(or (:date %) LocalDate/MIN)))))

;; ---------------------------------------------------------------------------
;; Display names: most frequent raw spelling per canonical id, preferring
;; spellings without a trailing state/country suffix ("Flamengo" over
;; "Flamengo-RJ").

(defn- suffixed? [raw]
  (boolean (re-find #"[-–]\s*[A-Z]{2,3}\s*$" (str raw))))

(defn build-display-names [matches]
  (let [freqs (frequencies (mapcat (fn [m] [[(:home m) (:home-raw m)]
                                            [(:away m) (:away-raw m)]])
                                   matches))
        by-canon (group-by ffirst freqs)]
    (into {}
          (map (fn [[canon entries]]
                 (let [best (apply max-key
                                   (fn [[[_ raw] n]]
                                     (+ n (if (suffixed? raw) 0 100000)))
                                   entries)]
                   [canon (second (first best))])))
          by-canon)))

;; ---------------------------------------------------------------------------
;; Database

(defn load-db [dir]
  (let [brasileirao  (load-brasileirao dir)
        cup          (load-cup dir)
        libertadores (load-libertadores dir)
        historical   (load-historical dir)
        extended     (load-extended dir)
        all          (concat brasileirao cup libertadores historical extended)
        matches      (vec (dedupe-matches all))
        players      (vec (load-players dir))]
    {:matches matches
     :players players
     :display-names (build-display-names matches)
     :file-counts {:brasileirao (count brasileirao)
                   :cup (count cup)
                   :libertadores (count libertadores)
                   :historical (count historical)
                   :extended (count extended)
                   :players (count players)}}))

(defonce ^:private db* (atom nil))

(defn db
  "The loaded database; loads once on first call."
  []
  (or @db*
      (let [loaded (load-db (data-dir))]
        (reset! db* loaded)
        loaded)))

(defn display-name [canon]
  (get (:display-names (db)) canon canon))
