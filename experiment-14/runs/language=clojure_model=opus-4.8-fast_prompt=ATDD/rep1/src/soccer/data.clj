(ns soccer.data
  "Loading and normalization of the Brazilian soccer datasets.

   Responsibilities:
   - Read every CSV in a data directory and turn it into a uniform in-memory
     model of `matches` and `players`, regardless of the per-file schema.
   - Normalize the messy real-world variations called out in the spec:
     team-name suffixes (\"Palmeiras-SP\", \"Nacional (URU)\"), multiple date
     formats (ISO, Brazilian DD/MM/YYYY, with time), float-encoded goals
     (\"1.0\"), and UTF-8 accented text.

   The rest of the system queries only this normalized model."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; Text / name normalization
;; ---------------------------------------------------------------------------

(defn strip-accents
  "Remove diacritics so accented and unaccented spellings compare equal."
  [s]
  (-> (java.text.Normalizer/normalize (str s) java.text.Normalizer$Form/NFD)
      (str/replace #"\p{M}+" "")))

(defn norm
  "Normalized matching key: accent-free, lower-case, single-spaced.

   The team's state/country suffix is intentionally *kept* so distinct clubs
   that differ only by suffix (Atletico-MG vs Atletico-PR) stay distinct.
   Substring matching against this key lets a bare query (\"flamengo\") find a
   suffixed record (\"flamengo-rj\")."
  [s]
  (-> (strip-accents s)
      str/lower-case
      (str/replace #"\s+" " ")
      str/trim))

(defn display-name
  "A clean, human-facing team name: parenthetical and trailing state/country
   codes removed (\"Flamengo-RJ\" -> \"Flamengo\", \"Nacional (URU)\" ->
   \"Nacional\")."
  [s]
  (-> (str s)
      (str/replace #"\s*\([^)]*\)" "")
      (str/replace #"\s*-\s*[A-Za-z]{2,4}\s*$" "")
      (str/replace #"\s+" " ")
      str/trim))

;; ---------------------------------------------------------------------------
;; Value parsing
;; ---------------------------------------------------------------------------

(defn parse-int-ish
  "Parse a goal/number cell that may be \"1\", \"1.0\", 1 or blank."
  [v]
  (cond
    (number? v) (long v)
    (nil? v) nil
    :else (let [s (str/trim (str v))]
            (when (seq s)
              (try (long (Math/round (Double/parseDouble s)))
                   (catch Exception _ nil))))))

(defn parse-date
  "Normalize a date cell to ISO \"yyyy-MM-dd\" (string), handling ISO,
   ISO-with-time and Brazilian DD/MM/YYYY formats."
  [v]
  (when v
    (let [s (str/trim (str v))]
      (cond
        (re-find #"^\d{4}-\d{2}-\d{2}" s) (subs s 0 10)
        (re-find #"^\d{2}/\d{2}/\d{4}" s)
        (let [[d m y] (str/split (subs s 0 10) #"/")]
          (str y "-" m "-" d))
        :else nil))))

(defn year-of [iso-date]
  (when (and iso-date (>= (count iso-date) 4))
    (parse-int-ish (subs iso-date 0 4))))

;; ---------------------------------------------------------------------------
;; CSV reading
;; ---------------------------------------------------------------------------

(defn read-csv-maps
  "Read a CSV file into a seq of {header-string value-string} maps (UTF-8)."
  [file]
  (with-open [r (io/reader file :encoding "UTF-8")]
    (let [[header & rows] (csv/read-csv r)
          ;; The FIFA file's first header carries a UTF-8 BOM; trim it.
          header (mapv #(str/replace % "﻿" "") header)]
      (doall (map #(zipmap header %) rows)))))

(defn header-of [file]
  (with-open [r (io/reader file :encoding "UTF-8")]
    (set (mapv #(str/replace % "﻿" "") (first (csv/read-csv r))))))

;; ---------------------------------------------------------------------------
;; Match construction
;; ---------------------------------------------------------------------------

(defn- mk-match
  [{:keys [competition season round stage date home away home-goal away-goal]}]
  (let [iso (parse-date date)]
    {:competition competition
     :season (or (parse-int-ish season) (year-of iso))
     :round (when (and round (seq (str round))) (str round))
     :stage (when (and stage (seq (str stage))) (str stage))
     :date iso
     :home home
     :away away
     :home-display (display-name home)
     :away-display (display-name away)
     :home-norm (norm home)
     :away-norm (norm away)
     ;; Canonical, suffix-free key used to merge the same club across files
     ;; that spell it differently ("Atletico-MG" vs "Atletico").
     :home-key (norm (display-name home))
     :away-key (norm (display-name away))
     :home-goal (parse-int-ish home-goal)
     :away-goal (parse-int-ish away-goal)}))

(defn- file->kind
  "Classify a CSV by its header columns."
  [cols]
  (cond
    (and (cols "Nationality") (cols "Overall") (cols "Name")) :players
    (and (cols "tournament") (cols "home") (cols "away")) :extended
    (cols "Equipe_mandante") :historical
    (cols "home_team_state") :brasileirao
    (cols "stage") :libertadores
    (and (cols "round") (cols "home_team")) :cup
    :else :unknown))

(defmulti ^:private load-matches (fn [kind _file] kind))
(defmethod load-matches :default [_ _] [])

(defmethod load-matches :brasileirao [_ file]
  (for [r (read-csv-maps file)]
    (mk-match {:competition "Brasileirão" :season (r "season")
               :round (r "round") :date (r "datetime")
               :home (r "home_team") :away (r "away_team")
               :home-goal (r "home_goal") :away-goal (r "away_goal")})))

(defmethod load-matches :historical [_ file]
  (for [r (read-csv-maps file)]
    (mk-match {:competition "Brasileirão" :season (r "Ano")
               :round (r "Rodada") :date (r "Data")
               :home (r "Equipe_mandante") :away (r "Equipe_visitante")
               :home-goal (r "Gols_mandante") :away-goal (r "Gols_visitante")})))

(defmethod load-matches :cup [_ file]
  (for [r (read-csv-maps file)]
    (mk-match {:competition "Copa do Brasil" :season (r "season")
               :round (r "round") :date (r "datetime")
               :home (r "home_team") :away (r "away_team")
               :home-goal (r "home_goal") :away-goal (r "away_goal")})))

(defmethod load-matches :libertadores [_ file]
  (for [r (read-csv-maps file)]
    (mk-match {:competition "Copa Libertadores" :season (r "season")
               :stage (r "stage") :date (r "datetime")
               :home (r "home_team") :away (r "away_team")
               :home-goal (r "home_goal") :away-goal (r "away_goal")})))

(defmethod load-matches :extended [_ file]
  (for [r (read-csv-maps file)]
    (mk-match {:competition (r "tournament") :date (r "date")
               :home (r "home") :away (r "away")
               :home-goal (r "home_goal") :away-goal (r "away_goal")})))

(defn- load-players [file]
  (for [r (read-csv-maps file)
        :let [name (r "Name")]
        :when (and name (seq (str/trim name)))]
    {:id (r "ID")
     :name name
     :age (parse-int-ish (r "Age"))
     :nationality (r "Nationality")
     :overall (or (parse-int-ish (r "Overall")) 0)
     :potential (parse-int-ish (r "Potential"))
     :club (or (r "Club") "")
     :position (r "Position")
     :jersey (r "Jersey Number")
     :name-norm (norm name)
     :nat-norm (norm (r "Nationality"))
     :club-norm (norm (or (r "Club") ""))}))

;; ---------------------------------------------------------------------------
;; Public entry point
;; ---------------------------------------------------------------------------

(defn- dedup-by-source
  "Several provided files overlap (e.g. the 2019 Brasileirão is in both its own
   file and the historical 2003-2019 file), with inconsistent team spellings
   that defeat row-by-row dedup.  Instead, for each (competition, season) keep
   only the single most complete source file; seasons unique to one file are
   untouched.  This removes cross-file double counting without losing data."
  [matches]
  (let [grouped (group-by (juxt :competition :season) matches)]
    (mapcat
     (fn [[[_ season] ms]]
       (if (nil? season)
         ms
         (let [by-src (group-by :source ms)
               ;; Prefer the source with the most matches; break ties by name.
               winner (->> (keys by-src)
                           (sort-by (juxt #(- (count (by-src %))) identity))
                           first)]
           (get by-src winner))))
     grouped)))

(defn load-dataset
  "Load every CSV under `data-dir` into {:matches [...] :players [...]}."
  [data-dir]
  (let [files (->> (.listFiles (io/file data-dir))
                   (filter #(str/ends-with? (.getName %) ".csv"))
                   sort)
        {:keys [matches players]}
        (reduce
         (fn [acc file]
           (let [kind (file->kind (header-of file))
                 src (.getName file)]
             (if (= kind :players)
               (update acc :players into (load-players file))
               (update acc :matches into
                       (map #(assoc % :source src) (load-matches kind file))))))
         {:matches [] :players []}
         files)]
    {:matches (vec (dedup-by-source matches)) :players players}))
