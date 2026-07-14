(ns soccer-mcp.data
  "CSV loading and normalization for Brazilian soccer datasets.

   Loads the six provided CSV files and produces two indexed in-memory collections:
     :matches  — unified match records across all sources
     :players  — FIFA player records (Brazilian focus)

   Each match record has shape:
     {:competition :brasileirao | :copa-do-brasil | :libertadores
                   | :brasileirao-historical | :other
      :date YYYY-MM-DD
      :datetime original datetime string
      :home  normalized team display name (state suffix stripped)
      :home-raw original team name
      :home-state two-letter state code or nil
      :away / :away-raw / :away-state ...
      :home-goal long
      :away-goal long
      :season long
      :round string or nil
      :stage string or nil      ; libertadores
      :stadium string or nil    ; historical brasileirão
      :source-file string}

   Team-name normalization strips a trailing \"-XX\" state suffix, collapses
   whitespace, and exposes both a display name and an ASCII-lowercased
   canonical key for fuzzy matching."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str])
  (:import (java.text Normalizer Normalizer$Form)))

;; ----------------------------------------------------------------------------
;; Generic helpers

(defn- strip-bom [^String s]
  (when s
    (if (and (pos? (.length s)) (= 0xFEFF (int (.charAt s 0))))
      (subs s 1)
      s)))

(defn parse-long-safe
  "Parse `s` as a long. Accepts plain ints, decimal strings like \"1.0\",
   strings with whitespace, or numeric values. Returns nil on failure or
   blank input."
  [s]
  (cond
    (nil? s) nil
    (number? s) (long s)
    :else
    (let [t (str/trim (str s))]
      (when-not (str/blank? t)
        (try
          (if-let [m (re-matches #"-?\d+" t)]
            (Long/parseLong m)
            ;; allow decimal like "1.0"
            (when (re-matches #"-?\d+\.\d+" t)
              (long (Double/parseDouble t))))
          (catch Exception _ nil))))))

(defn ascii-fold
  "Lowercase `s` and strip diacritics for canonical matching."
  [s]
  (when s
    (-> (Normalizer/normalize (str s) Normalizer$Form/NFD)
        (str/replace #"\p{InCombiningDiacriticalMarks}+" "")
        str/lower-case
        str/trim
        (str/replace #"\s+" " "))))

(def ^:private state-suffix-re
  ;; matches a trailing " - XX" or "-XX" with two-letter state code
  #"\s*[-–—]\s*([A-Z]{2})\s*$")

(defn split-state-suffix
  "Split a team name like \"Palmeiras-SP\" into [base state]. If no state
   suffix is present, returns [name nil]."
  [team]
  (if-let [m (and team (re-find state-suffix-re team))]
    [(str/trim (subs team 0 (- (count team) (count (first m)))))
     (second m)]
    [(when team (str/trim team)) nil]))

(defn normalize-team
  "Display-name normalization: trim whitespace and collapse interior runs.
   The state suffix is preserved here so that teams with the same base name
   from different states (e.g. \"Atletico-MG\" vs \"Atletico-PR\") remain
   distinguishable when grouping. Use team-key when you want a state-less
   canonical form for fuzzy matching."
  [team]
  (when team
    (-> team str/trim (str/replace #"\s+" " "))))

(defn team-key
  "Canonical key for team-name matching: ASCII-folded, state suffix stripped,
   whitespace collapsed."
  [team]
  (when team
    (let [[base _] (split-state-suffix team)]
      (when base
        (ascii-fold base)))))

(defn team-matches?
  "True when query string `q` matches team name `team` (case- and
   accent-insensitive, substring)."
  [team q]
  (when (and team q)
    (let [tk (team-key team)
          qk (ascii-fold q)]
      (and tk qk (str/includes? tk qk)))))

;; ----------------------------------------------------------------------------
;; Date helpers

(defn parse-iso-date
  "Return YYYY-MM-DD from an ISO datetime string or nil."
  [s]
  (when-let [t (and s (str/trim (str s)))]
    (when-let [m (re-find #"^(\d{4}-\d{2}-\d{2})" t)]
      (first m))))

(defn parse-br-date
  "Return YYYY-MM-DD from a Brazilian DD/MM/YYYY date string or nil."
  [s]
  (when-let [t (and s (str/trim (str s)))]
    (when-let [[_ d mo y] (re-matches #"(\d{1,2})/(\d{1,2})/(\d{4})" t)]
      (format "%04d-%02d-%02d"
              (Long/parseLong y)
              (Long/parseLong mo)
              (Long/parseLong d)))))

(defn normalize-date
  "Best-effort normalize a date or datetime string to YYYY-MM-DD."
  [s]
  (or (parse-iso-date s) (parse-br-date s)))

;; ----------------------------------------------------------------------------
;; CSV loading

(defn- read-csv-rows
  "Read a CSV resource and return a seq of row maps keyed by header."
  [path]
  (with-open [rdr (io/reader path)]
    (let [rows (csv/read-csv rdr)
          headers (mapv (comp str/trim strip-bom) (first rows))]
      (doall
       (map (fn [row]
              (zipmap headers (mapv str row)))
            (rest rows))))))

;; ----------------------------------------------------------------------------
;; Per-file row → match record

(defn- ->brasileirao-match [row]
  (let [home (get row "home_team")
        away (get row "away_team")]
    {:competition :brasileirao
     :date (normalize-date (get row "datetime"))
     :datetime (get row "datetime")
     :home (normalize-team home)
     :home-raw home
     :home-state (get row "home_team_state")
     :away (normalize-team away)
     :away-raw away
     :away-state (get row "away_team_state")
     :home-goal (parse-long-safe (get row "home_goal"))
     :away-goal (parse-long-safe (get row "away_goal"))
     :season (parse-long-safe (get row "season"))
     :round (get row "round")
     :stage nil
     :stadium nil
     :source-file "Brasileirao_Matches.csv"}))

(defn- ->cup-match [row]
  (let [home (get row "home_team")
        away (get row "away_team")
        [_ hs] (split-state-suffix home)
        [_ as] (split-state-suffix away)]
    {:competition :copa-do-brasil
     :date (normalize-date (get row "datetime"))
     :datetime (get row "datetime")
     :home (normalize-team home) :home-raw home :home-state hs
     :away (normalize-team away) :away-raw away :away-state as
     :home-goal (parse-long-safe (get row "home_goal"))
     :away-goal (parse-long-safe (get row "away_goal"))
     :season (parse-long-safe (get row "season"))
     :round (get row "round")
     :stage nil
     :stadium nil
     :source-file "Brazilian_Cup_Matches.csv"}))

(defn- ->libertadores-match [row]
  (let [home (get row "home_team")
        away (get row "away_team")
        [_ hs] (split-state-suffix home)
        [_ as] (split-state-suffix away)]
    {:competition :libertadores
     :date (normalize-date (get row "datetime"))
     :datetime (get row "datetime")
     :home (normalize-team home) :home-raw home :home-state hs
     :away (normalize-team away) :away-raw away :away-state as
     :home-goal (parse-long-safe (get row "home_goal"))
     :away-goal (parse-long-safe (get row "away_goal"))
     :season (parse-long-safe (get row "season"))
     :round nil
     :stage (get row "stage")
     :stadium nil
     :source-file "Libertadores_Matches.csv"}))

(defn- competition-from-tournament
  "Map a tournament name from the extended dataset to a competition keyword.
   These are kept distinct from the per-competition CSV keys (e.g.
   `:brasileirao-extended` not `:brasileirao`) so that the default per-
   competition aliases don't double-count overlapping matches."
  [t]
  (let [n (ascii-fold t)]
    (cond
      (or (str/includes? n "brasileirao")
          (str/includes? n "serie a"))  :brasileirao-extended
      (str/includes? n "serie b")       :serie-b-extended
      (str/includes? n "serie c")       :serie-c-extended
      (str/includes? n "copa do brasil") :copa-do-brasil-extended
      (str/includes? n "libertadores")   :libertadores-extended
      :else :other)))

(defn- ->extended-match [row]
  (let [home (get row "home")
        away (get row "away")
        [_ hs] (split-state-suffix home)
        [_ as] (split-state-suffix away)
        date (get row "date")
        time (get row "time")]
    {:competition (competition-from-tournament (get row "tournament"))
     :date (normalize-date date)
     :datetime (if (str/blank? time) date (str date " " time))
     :home (normalize-team home) :home-raw home :home-state hs
     :away (normalize-team away) :away-raw away :away-state as
     :home-goal (parse-long-safe (get row "home_goal"))
     :away-goal (parse-long-safe (get row "away_goal"))
     :season (some-> (parse-iso-date date) (subs 0 4) parse-long-safe)
     :round nil
     :stage nil
     :stadium nil
     :tournament (get row "tournament")
     :source-file "BR-Football-Dataset.csv"}))

(defn- ->historical-match [row]
  (let [home (get row "Equipe_mandante")
        away (get row "Equipe_visitante")]
    {:competition :brasileirao-historical
     :date (normalize-date (get row "Data"))
     :datetime (get row "Data")
     :home (normalize-team home)
     :home-raw home
     :home-state (get row "Mandante_UF")
     :away (normalize-team away)
     :away-raw away
     :away-state (get row "Visitante_UF")
     :home-goal (parse-long-safe (get row "Gols_mandante"))
     :away-goal (parse-long-safe (get row "Gols_visitante"))
     :season (parse-long-safe (get row "Ano"))
     :round (get row "Rodada")
     :stage nil
     :stadium (get row "Arena")
     :source-file "novo_campeonato_brasileiro.csv"}))

(defn- valid-match?
  "A match is queryable when we have both teams and a score."
  [m]
  (and (:home m) (:away m)
       (some? (:home-goal m)) (some? (:away-goal m))))

;; ----------------------------------------------------------------------------
;; Player loading

(defn- ->player [row]
  {:id          (parse-long-safe (get row "ID"))
   :name        (get row "Name")
   :age         (parse-long-safe (get row "Age"))
   :nationality (get row "Nationality")
   :overall     (parse-long-safe (get row "Overall"))
   :potential   (parse-long-safe (get row "Potential"))
   :club        (get row "Club")
   :position    (get row "Position")
   :jersey      (parse-long-safe (get row "Jersey Number"))
   :height      (get row "Height")
   :weight      (get row "Weight")
   :foot        (get row "Preferred Foot")})

(defn- valid-player? [p]
  (and (:name p) (not (str/blank? (:name p)))))

;; ----------------------------------------------------------------------------
;; Top-level loaders

(defn- safe-load [path xform]
  (if (.exists (io/file path))
    (->> (read-csv-rows path)
         (map xform)
         doall)
    []))

(defn load-matches
  "Load and unify all match CSVs from `data-dir` (default \"data/kaggle\")."
  ([] (load-matches "data/kaggle"))
  ([data-dir]
   (let [files [["Brasileirao_Matches.csv"        ->brasileirao-match]
                ["Brazilian_Cup_Matches.csv"      ->cup-match]
                ["Libertadores_Matches.csv"       ->libertadores-match]
                ["BR-Football-Dataset.csv"        ->extended-match]
                ["novo_campeonato_brasileiro.csv" ->historical-match]]]
     (->> files
          (mapcat (fn [[fname xform]]
                    (safe-load (str data-dir "/" fname) xform)))
          (filter valid-match?)
          vec))))

(defn load-players
  "Load FIFA player rows from `data-dir`."
  ([] (load-players "data/kaggle"))
  ([data-dir]
   (->> (safe-load (str data-dir "/fifa_data.csv") ->player)
        (filter valid-player?)
        vec)))

(defn load-all
  "Load both matches and players. Returns {:matches [...] :players [...]}."
  ([] (load-all "data/kaggle"))
  ([data-dir]
   {:matches (load-matches data-dir)
    :players (load-players data-dir)}))
