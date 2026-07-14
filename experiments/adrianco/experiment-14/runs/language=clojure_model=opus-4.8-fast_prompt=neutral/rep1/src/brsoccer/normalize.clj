;; =============================================================================
;; brsoccer.normalize
;;
;; Context:
;;   The bundled datasets describe the same real-world teams under many spellings
;;   ("Palmeiras-SP", "Palmeiras", "São Paulo", "Sao Paulo", "América - MG",
;;   "Nacional (URU)").  Every query in the system needs a single canonical key so
;;   that a user asking about "flamengo" matches rows stored as "Flamengo-RJ".
;;
;;   This namespace owns ALL string/value normalization:
;;     * team-key      -- accent/suffix/punctuation-insensitive matching key
;;     * strip-suffix  -- removes "-SP" / " - MG" / "(URU)" style suffixes
;;     * parse-date    -- accepts ISO, Brazilian (DD/MM/YYYY) and datetime forms
;;     * parse-int/num -- lenient numeric parsing for messy CSV cells
;;
;;   Keeping this logic in one place is what makes cross-file queries reliable.
;; =============================================================================
(ns brsoccer.normalize
  (:require [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]))

(defn strip-accents
  "Decompose accented characters and drop the combining marks.
   \"São Paulo\" -> \"Sao Paulo\", \"Grêmio\" -> \"Gremio\"."
  [^String s]
  (when s
    (-> (Normalizer/normalize s Normalizer$Form/NFD)
        (str/replace #"\p{M}+" ""))))

(def ^:private suffix-re
  ;; Trailing state/country tags: " - RJ", "-SP", " (URU)", " (EQU)".
  #"(?i)\s*(?:-\s*[a-z]{2}|\([a-z]{2,4}\))\s*$")

(defn strip-suffix
  "Remove a single trailing state/country suffix and surrounding whitespace.
   \"Palmeiras-SP\" -> \"Palmeiras\", \"Nacional (URU)\" -> \"Nacional\"."
  [s]
  (when s
    (-> s str/trim (str/replace suffix-re "") str/trim)))

;; Bases where the trailing STATE is the disambiguator: three different clubs
;; share the base "atletico"/"athletico" (Goianiense-GO, Mineiro-MG,
;; Paranaense-PR). For these we keep the state code rather than stripping it.
(def ^:private state-qualified-base #{"atletico" "athletico"})

;; Cross-dataset aliases: the same club is spelled in long form in some files
;; ("Atletico Mineiro", "EC Bahia", "Vasco da Gama RJ") and short form in others.
;; This table folds every observed variant onto one canonical key.
(def team-aliases
  {"atleticomineiro"      "atleticomg"
   "atleticogoianiense"   "atleticogo"
   "atleticoparanaense"   "atleticopr"
   "athleticoparanaense"  "atleticopr"
   "athletico"            "atleticopr"   ; bare "Athletico" in the 2003-2019 file = Paranaense
   "athleticopr"          "atleticopr"
   "ecbahia"              "bahia"
   "vascodagama"          "vasco"
   "vascodagamarj"        "vasco"
   "fortalezaec"          "fortaleza"
   "fortalezafc"          "fortaleza"
   "nauticocapibaribe"    "nautico"
   "santacruzfc"          "santacruz"
   "sportrecife"          "sport"
   "redbullbragantino"    "bragantino"
   "ecjuventude"          "juventude"
   "botafogorj"           "botafogo"
   "guaranisp"            "guarani"
   "portuguesadesportos"  "portuguesa"
   "americamg"            "america"})

(defn- alnum [s]
  (-> s strip-accents str/lower-case (str/replace #"[^a-z0-9]" "")))

(defn- trailing-state
  "Return the 2-letter state code in a \"Name-XX\" / \"Name XX\" string, else nil."
  [s]
  (some-> (re-find #"(?i)[-\s]([a-z]{2})\s*$" (strip-accents s)) second str/lower-case))

(defn team-key
  "Canonical matching key for a team name. Strips the state/country suffix,
   accents, case and punctuation so \"São Paulo-SP\" and \"Sao Paulo\" both map to
   \"saopaulo\". For state-ambiguous bases (the three Atléticos) the state is kept
   (\"Atletico-MG\" -> \"atleticomg\"), and a cross-dataset alias table folds long
   and short spellings of the same club onto one key."
  [s]
  (when (and s (not (str/blank? s)))
    (let [base (alnum (strip-suffix s))
          k (if (and (state-qualified-base base) (trailing-state s))
              (str base (trailing-state s))
              base)]
      (when-not (str/blank? k)
        (get team-aliases k k)))))

(defn clean-name
  "Human-friendly display form: suffix stripped, BOM/whitespace trimmed."
  [s]
  (some-> s (str/replace "﻿" "") strip-suffix str/trim))

(defn parse-int
  "Lenient integer parse; returns nil on blank/garbage. Tolerates \"3.0\"."
  [s]
  (cond
    (integer? s) s
    (nil? s) nil
    :else (let [t (str/trim (str s))]
            (when-not (str/blank? t)
              (try
                (long (Double/parseDouble t))
                (catch Exception _ nil))))))

(defn parse-num
  "Lenient double parse; returns nil on blank/garbage."
  [s]
  (cond
    (number? s) (double s)
    (nil? s) nil
    :else (let [t (str/trim (str s))]
            (when-not (str/blank? t)
              (try (Double/parseDouble t) (catch Exception _ nil))))))

(defn parse-date
  "Normalize the many date formats in the datasets to an ISO \"yyyy-MM-dd\"
   string (sortable, comparable). Returns nil when no date can be found.
     \"2012-05-19 18:30:00\" -> \"2012-05-19\"
     \"29/03/2003\"          -> \"2003-03-29\"
     \"2023-09-24\"          -> \"2023-09-24\""
  [s]
  (when (and s (not (str/blank? (str s))))
    (let [t (str/trim (str s))]
      (or
        ;; ISO date possibly followed by a time component
        (when-let [m (re-find #"^(\d{4})-(\d{2})-(\d{2})" t)]
          (format "%s-%s-%s" (m 1) (m 2) (m 3)))
        ;; Brazilian DD/MM/YYYY
        (when-let [m (re-find #"^(\d{1,2})/(\d{1,2})/(\d{4})" t)]
          (format "%04d-%02d-%02d"
                  (Integer/parseInt (m 3))
                  (Integer/parseInt (m 2))
                  (Integer/parseInt (m 1))))))))

(defn year-of
  "Extract the 4-digit year from a normalized or raw date string."
  [s]
  (when s
    (when-let [m (re-find #"(\d{4})" (str s))]
      (Integer/parseInt (m 1)))))
