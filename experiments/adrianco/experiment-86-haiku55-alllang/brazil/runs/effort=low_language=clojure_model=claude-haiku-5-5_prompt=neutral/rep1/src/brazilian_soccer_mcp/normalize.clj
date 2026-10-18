(ns brazilian-soccer-mcp.normalize
  "Team-name and date normalization for the heterogeneous Kaggle sources.

  Team names appear as \"Palmeiras-SP\", \"Palmeiras - SP\", \"Nacional (URU)\",
  \"Boavista Sport Club (antigo ...) - RJ\" or plain \"Sao Paulo\" depending on
  the file. Matching uses a base key (accent-free, lower-case, decorations
  removed) plus an optional state/country suffix that tells apart clubs such as
  Atletico-MG and Atletico-GO when the suffix is present on both sides."
  (:require [clojure.string :as str])
  (:import (java.text Normalizer Normalizer$Form)
           (java.time LocalDate)
           (java.time.format DateTimeFormatter)))

(def ^:private aliases
  "Alternative and former club names mapped to the base key used by the main name."
  {"sport club corinthians paulista" "corinthians"
   "sociedade esportiva palmeiras" "palmeiras"
   "clube de regatas do flamengo" "flamengo"
   "sao paulo futebol clube" "sao paulo"
   "sport club internacional" "internacional"
   "gremio foot-ball porto alegrense" "gremio"
   "vasco da gama" "vasco"
   "clube atletico mineiro" "atletico"
   "atletico mineiro" "atletico"
   "athletico paranaense" "athletico"
   "atletico paranaense" "athletico"
   "ec bahia" "bahia"
   "fortaleza fc" "fortaleza"
   ;; Atletico-PR is "Atletico" plus a PR suffix in some files, so the state is needed to tell it from Atletico-MG.
   "atletico-pr" "athletico"})

(def ^:private parenthetical #"\([^)]*\)")

(def ^:private uf-suffix
  "A trailing Brazilian state code written without a hyphen, e.g. \"Botafogo RJ\" or \"Atletico pr\"."
  #"(?i)\s+((?:AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO))$")

(defn- strip-accents [s]
  (str/replace (Normalizer/normalize s Normalizer$Form/NFD) #"\p{M}" ""))

(defn normalize-text
  "Lower-cased, accent-free, whitespace-collapsed text for case-insensitive comparison."
  [s]
  (-> (or s "") strip-accents str/lower-case str/trim (str/replace #"\s+" " ")))

(defn- without-decorations
  "Removes parenthetical notes and trailing state suffixes (\"-SP\", \" - RJ\", \" RJ\"), keeping accents."
  [s]
  (-> s
      (str/replace parenthetical " ")
      (str/replace #"\s+-\s*[A-Za-z]{2,3}$" "")
      (str/replace #"-[A-Za-z]{2,3}$" "")
      (str/replace uf-suffix "")
      (str/replace #"\s+" " ")
      str/trim))

(defn- suffix-of
  "Lower-cased state/country suffix of a team name, or nil. Unhyphenated suffixes
  must be known state codes so ordinary words are not mistaken for states."
  [s]
  (let [t (str/replace s parenthetical " ")
        m (or (re-find #"(?:\s+-\s*|-)([A-Za-z]{2,3})$" t)
              (re-find uf-suffix t))]
    (some-> m second str/lower-case)))

(defn display-name
  "Team name as a person would write it, e.g. \"Palmeiras\" for \"Palmeiras-SP\"."
  [s]
  (without-decorations (or s "")))

(defn team-key
  "Matching key for a team name: {:base \"palmeiras\" :state \"sp\"}, state may be nil.
  Aliases are tried with the state first (\"atletico-pr\") and then without it (\"vasco da gama\")."
  [s]
  (let [base (normalize-text (without-decorations (or s "")))
        state (suffix-of (or s ""))
        qualified (if state (str base "-" state) base)]
    {:base (or (aliases qualified) (aliases base) base)
     :state state}))

(defn same-team?
  "True when two team keys refer to the same club. A missing state on either side matches any state."
  [a b]
  (and (= (:base a) (:base b))
       (or (nil? (:state a)) (nil? (:state b)) (= (:state a) (:state b)))))

(def ^:private brazilian-date (DateTimeFormatter/ofPattern "dd/MM/yyyy"))

(defn parse-date
  "Parses ISO (\"2023-09-24\", \"2012-05-19 18:30:00\") or Brazilian (\"29/03/2003\") dates.
  Returns a LocalDate, or nil when the text is not a valid date."
  ^LocalDate [s]
  (let [s (str/trim (or s ""))]
    (try
      (cond
        (re-matches #"\d{4}-\d{2}-\d{2}.*" s) (LocalDate/parse (subs s 0 10))
        (re-matches #"\d{2}/\d{2}/\d{4}" s) (LocalDate/parse s brazilian-date)
        :else nil)
      (catch java.time.DateTimeException _ nil))))
