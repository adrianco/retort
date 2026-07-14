(ns brazilian-soccer-mcp.data
  "CSV loading and normalization for Brazilian soccer datasets.

  Provides a single in-memory dataset map containing normalized matches
  from multiple competitions plus FIFA player records. Team names are
  normalized so that variants such as \"Palmeiras-SP\", \"Palmeiras\" and
  \"Palmeiras - SP\" collapse to the same canonical key."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]))

(def ^:private default-data-dir "data/kaggle")

;; ---------------------------------------------------------------------------
;; Normalization helpers
;; ---------------------------------------------------------------------------

(defn- strip-accents [^String s]
  (when s
    (-> (java.text.Normalizer/normalize s java.text.Normalizer$Form/NFD)
        (str/replace #"\p{InCombiningDiacriticalMarks}+" ""))))

(def ^:private team-aliases
  "Canonical mapping for Brazilian clubs whose name appears in more than
  one form across the source CSVs (spelling, rebrand, abbreviation)."
  {"athletico-pr"        "atletico-pr"
   "vasco-rj"            "vasco da gama-rj"
   "atletico paranaense" "atletico-pr"
   "atletico mineiro"    "atletico-mg"
   "atletico goianiense" "atletico-go"
   "america mineiro"     "america-mg"
   "america-mg"          "america-mg"
   "gremio"              "gremio-rs"
   "internacional"       "internacional-rs"
   "corinthians"         "corinthians-sp"
   "palmeiras"           "palmeiras-sp"
   "sao paulo"           "sao paulo-sp"
   "santos"              "santos-sp"
   "flamengo"            "flamengo-rj"
   "fluminense"          "fluminense-rj"
   "botafogo"            "botafogo-rj"
   "vasco"               "vasco da gama-rj"
   "vasco da gama"       "vasco da gama-rj"
   "cruzeiro"            "cruzeiro-mg"})

(defn normalize-team
  "Canonical key for a team name.

  Strips accents, parenthetical country codes (e.g. \"Nacional (URU)\"),
  lowercases, and preserves the state suffix (\"-mg\") when present —
  that's what distinguishes Atletico-MG from Atletico-PR. Common
  spelling/alias variants of well-known Brazilian clubs are then
  collapsed to a canonical key via `team-aliases`."
  [s]
  (when (and s (string? s) (seq (str/trim s)))
    (let [stripped (-> s
                       str/trim
                       (str/replace #"\s*\(([A-Z]{2,4})\)\s*$" "")
                       strip-accents
                       str/lower-case)
          [_ stem suffix] (re-find #"^(.*?)(?:\s*-\s*([a-z]{2}))?\s*$" stripped)
          stem* (-> (or stem "")
                    (str/replace #"[^a-z0-9 ]" " ")
                    (str/replace #"\s+" " ")
                    str/trim)
          base  (if suffix (str stem* "-" suffix) stem*)]
      (get team-aliases base base))))

(defn team-key-matches?
  "True when the query key matches a record key, allowing a query
   without a state suffix to match a record that has one (e.g. the
   query \"palmeiras\" matches \"palmeiras-sp\"). An exact match always
   wins."
  [query-key record-key]
  (cond
    (or (nil? query-key) (nil? record-key)) false
    (= query-key record-key) true
    (re-find #"-[a-z]{2}$" query-key) false
    :else (str/starts-with? record-key (str query-key "-"))))

(defn display-team
  "Pick a human-friendly display form for a team name string."
  [s]
  (when s (str/trim s)))

;; ---------------------------------------------------------------------------
;; Date parsing
;; ---------------------------------------------------------------------------

(defn parse-int [s]
  (try
    (cond
      (nil? s) nil
      (number? s) (long s)
      (string? s) (let [t (str/trim s)]
                    (when (seq t)
                      (Long/parseLong (str/replace t #"\..*$" "")))))
    (catch Exception _ nil)))

(defn parse-double-safe [s]
  (try
    (cond
      (nil? s) nil
      (number? s) (double s)
      (string? s) (let [t (str/trim s)]
                    (when (seq t) (Double/parseDouble t))))
    (catch Exception _ nil)))

(defn parse-date
  "Parses ISO (yyyy-MM-dd), Brazilian (dd/MM/yyyy) and datetime forms.
  Returns a yyyy-MM-dd string, or nil if it cannot be parsed."
  [s]
  (when (and s (string? s) (seq (str/trim s)))
    (let [t (str/trim s)]
      (cond
        (re-matches #"\d{4}-\d{2}-\d{2}.*" t) (subs t 0 10)
        (re-matches #"\d{2}/\d{2}/\d{4}.*" t) (let [[d m y] (str/split (subs t 0 10) #"/")]
                                                (format "%s-%s-%s" y m d))
        :else nil))))

(defn season-of [date-str fallback]
  (or (parse-int fallback)
      (when date-str
        (parse-int (subs date-str 0 4)))))

;; ---------------------------------------------------------------------------
;; CSV utilities
;; ---------------------------------------------------------------------------

(defn- read-csv [path]
  (with-open [r (io/reader path :encoding "UTF-8")]
    (doall (csv/read-csv r))))

(defn- rows->maps [rows]
  (when (seq rows)
    (let [header (mapv #(-> % (str/replace #"^﻿" "") str/trim) (first rows))]
      (mapv (fn [row] (zipmap header row)) (rest rows)))))

(defn- read-csv-maps [path]
  (rows->maps (read-csv path)))

;; ---------------------------------------------------------------------------
;; Per-file loaders -> sequence of normalized match maps
;; Match shape:
;;   {:competition "Brasileirão"
;;    :season 2019
;;    :round "10"
;;    :date "2019-08-04"
;;    :home "Flamengo" :home-key "flamengo"
;;    :away "Grêmio"   :away-key "gremio"
;;    :home-goal 5 :away-goal 0
;;    :stage nil :arena nil :stats {...optional...}
;;    :source "Brasileirao_Matches.csv"}
;; ---------------------------------------------------------------------------

(defn- ->match
  [{:keys [competition source date season round home away hg ag stage arena stats]}]
  (let [hg (parse-int hg)
        ag (parse-int ag)]
    (when (and home away)
      {:competition competition
       :source      source
       :season      season
       :round       (when round (str round))
       :date        date
       :home        (display-team home)
       :away        (display-team away)
       :home-key    (normalize-team home)
       :away-key    (normalize-team away)
       :home-goal   hg
       :away-goal   ag
       :stage       stage
       :arena       arena
       :stats       stats
       :result      (cond
                      (or (nil? hg) (nil? ag)) nil
                      (> hg ag) :home
                      (< hg ag) :away
                      :else     :draw)})))

(defn- load-brasileirao [path]
  (let [rows (read-csv-maps path)]
    (keep (fn [r]
            (let [d (parse-date (get r "datetime"))]
              (->match {:competition "Brasileirão Série A"
                        :source      "Brasileirao_Matches.csv"
                        :date        d
                        :season      (season-of d (get r "season"))
                        :round       (get r "round")
                        :home        (get r "home_team")
                        :away        (get r "away_team")
                        :hg          (get r "home_goal")
                        :ag          (get r "away_goal")})))
          rows)))

(defn- load-cup [path]
  (let [rows (read-csv-maps path)]
    (keep (fn [r]
            (let [d (parse-date (get r "datetime"))]
              (->match {:competition "Copa do Brasil"
                        :source      "Brazilian_Cup_Matches.csv"
                        :date        d
                        :season      (season-of d (get r "season"))
                        :round       (get r "round")
                        :home        (get r "home_team")
                        :away        (get r "away_team")
                        :hg          (get r "home_goal")
                        :ag          (get r "away_goal")})))
          rows)))

(defn- load-libertadores [path]
  (let [rows (read-csv-maps path)]
    (keep (fn [r]
            (let [d (parse-date (get r "datetime"))]
              (->match {:competition "Copa Libertadores"
                        :source      "Libertadores_Matches.csv"
                        :date        d
                        :season      (season-of d (get r "season"))
                        :stage       (get r "stage")
                        :home        (get r "home_team")
                        :away        (get r "away_team")
                        :hg          (get r "home_goal")
                        :ag          (get r "away_goal")})))
          rows)))

(defn- load-br-extended [path]
  (let [rows (read-csv-maps path)]
    (keep (fn [r]
            (let [d (parse-date (get r "date"))]
              (->match {:competition (or (get r "tournament") "Unknown")
                        :source      "BR-Football-Dataset.csv"
                        :date        d
                        :season      (season-of d nil)
                        :home        (get r "home")
                        :away        (get r "away")
                        :hg          (get r "home_goal")
                        :ag          (get r "away_goal")
                        :stats       {:home-corner  (parse-double-safe (get r "home_corner"))
                                      :away-corner  (parse-double-safe (get r "away_corner"))
                                      :home-shots   (parse-double-safe (get r "home_shots"))
                                      :away-shots   (parse-double-safe (get r "away_shots"))
                                      :home-attack  (parse-double-safe (get r "home_attack"))
                                      :away-attack  (parse-double-safe (get r "away_attack"))
                                      :total-corners (parse-double-safe (get r "total_corners"))
                                      :ht-result    (get r "ht_result")
                                      :at-result    (get r "at_result")
                                      :time         (get r "time")}})))
          rows)))

(defn- with-state-suffix
  "Append \"-XX\" to a team name when it is missing and we have a state
  code, so this dataset's records line up with Brasileirao_Matches.csv
  (which already encodes the state)."
  [name state]
  (cond
    (or (str/blank? name) (str/blank? state)) name
    (re-find #"-\s*[A-Za-z]{2}\s*$" name)     name
    :else                                     (str (str/trim name) "-" (str/trim state))))

(defn- load-historical [path]
  (let [rows (read-csv-maps path)]
    (keep (fn [r]
            (let [d    (parse-date (get r "Data"))
                  home (with-state-suffix (get r "Equipe_mandante") (get r "Mandante_UF"))
                  away (with-state-suffix (get r "Equipe_visitante") (get r "Visitante_UF"))]
              (->match {:competition "Brasileirão Série A"
                        :source      "novo_campeonato_brasileiro.csv"
                        :date        d
                        :season      (season-of d (get r "Ano"))
                        :round       (get r "Rodada")
                        :arena       (get r "Arena")
                        :home        home
                        :away        away
                        :hg          (get r "Gols_mandante")
                        :ag          (get r "Gols_visitante")})))
          rows)))

;; ---------------------------------------------------------------------------
;; FIFA player loader
;; ---------------------------------------------------------------------------

(defn- ->player [r]
  (let [club (get r "Club")]
    {:id          (parse-int (get r "ID"))
     :name        (get r "Name")
     :age         (parse-int (get r "Age"))
     :nationality (get r "Nationality")
     :overall     (parse-int (get r "Overall"))
     :potential   (parse-int (get r "Potential"))
     :club        club
     :club-key    (normalize-team club)
     :position    (get r "Position")
     :jersey      (parse-int (get r "Jersey Number"))
     :height      (get r "Height")
     :weight      (get r "Weight")
     :foot        (get r "Preferred Foot")
     :value       (get r "Value")
     :wage        (get r "Wage")}))

(defn- load-players [path]
  (mapv ->player (read-csv-maps path)))

;; ---------------------------------------------------------------------------
;; Top-level loader
;; ---------------------------------------------------------------------------

(defn- file [dir name]
  (let [f (io/file dir name)]
    (when (.exists f) (.getPath f))))

(defn- dedup-matches
  "Collapse records that describe the same physical match.

  Two records are considered the same iff they share (date, home-key,
  away-key). Matches that are missing any of those three keys are
  passed through untouched (we have no safe way to merge them). When
  duplicates exist, the first one wins — the loaders are concat'd in
  the order [Brasileirão, Cup, Libertadores, Extended-stats, Historical]
  so we prefer the source-of-record CSVs over the secondary
  statistics dump."
  [matches]
  (let [seen (volatile! #{})]
    (reduce
      (fn [acc m]
        (let [k (when (and (:date m) (:home-key m) (:away-key m))
                  [(:date m) (:home-key m) (:away-key m)])]
          (cond
            (nil? k)             (conj acc m)
            (contains? @seen k)  acc
            :else                (do (vswap! seen conj k) (conj acc m)))))
      []
      matches)))

(defn load-dataset
  "Load all CSV files under `dir` (defaults to data/kaggle). Returns
   {:matches [...] :players [...] :teams #{...keys...} :competitions #{...}}.
   Missing files are skipped without error. Overlapping match records
   are de-duplicated by (date, home-team, away-team)."
  ([] (load-dataset default-data-dir))
  ([dir]
   (let [matches (dedup-matches
                   (concat
                     (when-let [p (file dir "Brasileirao_Matches.csv")]    (load-brasileirao p))
                     (when-let [p (file dir "Brazilian_Cup_Matches.csv")]  (load-cup p))
                     (when-let [p (file dir "Libertadores_Matches.csv")]   (load-libertadores p))
                     (when-let [p (file dir "BR-Football-Dataset.csv")]    (load-br-extended p))
                     (when-let [p (file dir "novo_campeonato_brasileiro.csv")] (load-historical p))))
         players (or (when-let [p (file dir "fifa_data.csv")] (load-players p)) [])
         teams   (into (sorted-set)
                   (filter some?
                     (mapcat (juxt :home-key :away-key) matches)))]
     {:matches      matches
        :players      players
        :teams        teams
        :competitions (into (sorted-set) (keep :competition matches))
        :sources      (into (sorted-set) (keep :source matches))})))

(defn dataset-summary
  "Quick counts useful for diagnostics."
  [{:keys [matches players teams competitions sources]}]
  {:matches      (count matches)
   :players      (count players)
   :teams        (count teams)
   :competitions (vec competitions)
   :sources      (vec sources)})
