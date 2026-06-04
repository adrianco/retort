;; =============================================================================
;; brazilian-soccer.normalize
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   Brazilian soccer data arrives from six CSV files that use inconsistent
;;   conventions for the SAME real-world entity:
;;     * Team names: "Palmeiras-SP", "Palmeiras", "Sport Club ... Paulista"
;;     * State/country suffixes: "-SP", " - RJ", "(URU)", "-EQU"
;;     * Accents/cedilla: "São Paulo", "Grêmio", "Avaí", "Fortaleza"
;;     * Dates: "2023-09-24", "2012-05-19 18:30:00", "29/03/2003"
;;
;;   This namespace centralises the normalisation rules so every other namespace
;;   matches, groups and de-duplicates entities consistently.
;;
;; KEY IDEAS
;;   - `team-key`  : an accent-free, lower-cased matching key. The state suffix is
;;                   DROPPED for most clubs ("Palmeiras-SP" -> "palmeiras") but
;;                   PRESERVED for the handful of clubs whose state is part of
;;                   their identity (Atlético-MG vs Atlético-PR, América-MG ...),
;;                   so distinct clubs never collapse together.
;;   - `display-name` : a clean human-readable label (suffix stripped, spacing
;;                   tidied) used in formatted answers.
;;   - `iso-date`  : best-effort parse of the three date formats into "yyyy-MM-dd".
;; =============================================================================
(ns brazilian-soccer.normalize
  (:require [clojure.string :as str])
  (:import (java.text Normalizer Normalizer$Form)))

;; Clubs that share a base name and are distinguished only by their state.
;; For these we keep the "-uf" part in the matching key.
(def ^:private ambiguous-bases
  #{"atletico" "america"})

(defn strip-accents
  "Remove diacritical marks: \"São Paulo\" -> \"Sao Paulo\", \"Grêmio\" -> \"Gremio\"."
  [s]
  (when s
    (-> (Normalizer/normalize s Normalizer$Form/NFD)
        (.replaceAll "\\p{InCombiningDiacriticalMarks}+" ""))))

(defn- collapse-ws [s]
  (-> s (str/replace #"\s+" " ") str/trim))

(def ^:private suffix-re
  ;; trailing state/country marker: " - SP", "-RJ", " (URU)", "-EQU"
  #"(?i)\s*(?:-\s*|\(\s*)([a-z]{2,3})\)?\s*$")

(defn split-suffix
  "Return [base-name uf-or-nil] by stripping a trailing state/country suffix.
   \"Palmeiras-SP\" -> [\"Palmeiras\" \"SP\"], \"Nacional (URU)\" -> [\"Nacional\" \"URU\"],
   \"Flamengo\" -> [\"Flamengo\" nil]."
  [raw]
  (let [s (collapse-ws (or raw ""))
        m (re-find suffix-re s)]
    (if m
      [(collapse-ws (subs s 0 (- (count s) (count (first m)))))
       (str/upper-case (second m))]
      [s nil])))

(defn team-key
  "Stable matching/grouping key for a raw team name. Accent-free and lower-cased.
   Drops the state suffix except for ambiguous bases (atletico, america)."
  [raw]
  (when (and raw (not (str/blank? raw)))
    (let [[base uf] (split-suffix raw)
          base*     (-> base strip-accents str/lower-case collapse-ws)]
      (if (and uf (contains? ambiguous-bases base*))
        (str base* "-" (str/lower-case uf))
        base*))))

(defn display-name
  "Clean, human-readable team label (state suffix stripped, spacing tidied).
   Ambiguous clubs keep their state, e.g. \"Atletico-MG\"."
  [raw]
  (when raw
    (let [[base uf] (split-suffix raw)
          base      (collapse-ws base)]
      (if (and uf (contains? ambiguous-bases (-> base strip-accents str/lower-case)))
        (str base "-" uf)
        base))))

(defn norm-text
  "Generic accent-free, lower-cased, whitespace-collapsed text key for free-text
   matching (player names, nationalities, clubs, competitions)."
  [s]
  (when s
    (-> s strip-accents str/lower-case collapse-ws)))

(defn iso-date
  "Best-effort conversion of the dataset date formats into \"yyyy-MM-dd\".
   Handles \"2012-05-19 18:30:00\", \"2023-09-24\" and \"29/03/2003\".
   Returns nil for blank/unparseable input."
  [raw]
  (when (and raw (not (str/blank? raw)))
    (let [s (str/trim raw)]
      (cond
        ;; ISO with optional time component
        (re-matches #"\d{4}-\d{2}-\d{2}([ T].*)?" s)
        (subs s 0 10)

        ;; Brazilian DD/MM/YYYY
        (re-matches #"\d{1,2}/\d{1,2}/\d{4}" s)
        (let [[d m y] (str/split s #"/")]
          (format "%s-%02d-%02d" y (Integer/parseInt m) (Integer/parseInt d)))

        :else nil))))

(defn ->int
  "Parse an integer from messy CSV cells (\"2\", \"2.0\", \" 3 \"). nil on failure."
  [v]
  (cond
    (integer? v) v
    (number? v)  (int v)
    (and (string? v) (not (str/blank? v)))
    (try
      (int (Double/parseDouble (str/trim v)))
      (catch Exception _ nil))
    :else nil))

(defn ->double
  "Parse a double from messy CSV cells. nil on failure."
  [v]
  (cond
    (number? v) (double v)
    (and (string? v) (not (str/blank? v)))
    (try (Double/parseDouble (str/trim v)) (catch Exception _ nil))
    :else nil))

(defn blank->nil [s]
  (when (and s (not (str/blank? s))) (str/trim s)))
