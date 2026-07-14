(ns brazilian-soccer.normalize
  "Normalization helpers for the Brazilian Soccer knowledge graph.

  The provided datasets use inconsistent naming and formatting conventions:
    * Team names may carry a state suffix (\"Palmeiras-SP\"), a country code
      (\"Nacional (URU)\"), or a spaced suffix (\"Boavista Sport Club - RJ\").
    * Dates appear as ISO (\"2023-09-24\"), ISO with time
      (\"2012-05-19 18:30:00\") or Brazilian (\"29/03/2003\").
    * Numeric goal columns are sometimes floats (\"2.0\").
    * Text contains Portuguese diacritics (São, Grêmio, Avaí).

  This namespace turns those raw values into canonical forms so the rest of
  the system can match and compare teams reliably."
  (:require [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]
           [java.time LocalDate]
           [java.time.format DateTimeFormatter]))

(defn strip-accents
  "Remove diacritics from `s`, e.g. \"São Paulo\" -> \"Sao Paulo\"."
  [s]
  (when s
    (-> (Normalizer/normalize s Normalizer$Form/NFD)
        (str/replace #"\p{InCombiningDiacriticalMarks}+" ""))))

(defn clean-team
  "Strip state/country suffixes and surrounding whitespace from a team name.

  Handles \"Palmeiras-SP\", \"Nacional (URU)\", \"Barcelona-EQU\" and
  \"Boavista Sport Club - RJ\" while leaving plain names untouched."
  [s]
  (when s
    (-> s
        str/trim
        ;; \"Nacional (URU)\" -> \"Nacional\"
        (str/replace #"\s*\([A-Za-z]{2,4}\)\s*$" "")
        ;; \"Boavista Sport Club - RJ\" -> \"Boavista Sport Club\"
        (str/replace #"\s+-\s+[A-Za-z]{2,3}\s*$" "")
        ;; \"Palmeiras-SP\" / \"Barcelona-EQU\" -> base name
        (str/replace #"-[A-Za-z]{2,3}\s*$" "")
        str/trim)))

(defn- fold-spelling
  "Fold known orthographic variants onto a single spelling. Currently the
  Athletico/Atlético variant (Athletico Paranaense is written both ways across
  the datasets)."
  [s]
  (str/replace s "athletico" "atletico"))

(defn team-key
  "Canonical match key for a team: accent-folded, lower-cased, suffix-stripped."
  [s]
  (when s
    (-> s clean-team strip-accents str/lower-case str/trim fold-spelling)))

(defn strict-key
  "Identity key that *keeps* the state/country suffix, so clubs that differ
  only by state (Atlético-MG vs Atlético-GO) remain distinct. Accents, case and
  the various suffix spellings (\"(URU)\", \" - RJ\", \"-RJ\") are normalized."
  [s]
  (when s
    (-> s
        strip-accents
        str/lower-case
        str/trim
        fold-spelling
        (str/replace #"\s*\(([a-z]{2,4})\)\s*$" "-$1") ; "(uru)" -> "-uru"
        (str/replace #"\s+-\s+([a-z]{2,3})\s*$" "-$1")  ; " - rj" -> "-rj"
        (str/replace #"\s+" " ")
        str/trim)))

(defn team-suffix
  "Return the lowercased state/country suffix of a team name, or nil."
  [s]
  (when s
    (second (re-find #"-([a-z]{2,4})$" (strict-key s)))))

(defn same-team?
  "True when two raw team names refer to the same club."
  [a b]
  (and a b (= (team-key a) (team-key b))))

(def ^:private iso-datetime
  (DateTimeFormatter/ofPattern "yyyy-MM-dd HH:mm:ss"))

(def ^:private br-date
  (DateTimeFormatter/ofPattern "dd/MM/yyyy"))

(defn parse-date
  "Parse a match date string into a `java.time.LocalDate`, or nil when blank.

  Accepts ISO dates, ISO datetimes and Brazilian DD/MM/YYYY dates."
  [s]
  (when (and s (not (str/blank? s)))
    (let [s (str/trim s)]
      (cond
        (re-matches #"\d{4}-\d{2}-\d{2} .*" s)
        (LocalDate/parse (subs s 0 10))

        (re-matches #"\d{4}-\d{2}-\d{2}" s)
        (LocalDate/parse s)

        (re-matches #"\d{2}/\d{2}/\d{4}" s)
        (LocalDate/parse s br-date)

        :else nil))))

(defn parse-int
  "Parse an integer from a string that may look like a float (\"2.0\")."
  [s]
  (when (and s (not (str/blank? (str s))))
    (try
      (int (Math/round (Double/parseDouble (str/trim (str s)))))
      (catch NumberFormatException _ nil))))
