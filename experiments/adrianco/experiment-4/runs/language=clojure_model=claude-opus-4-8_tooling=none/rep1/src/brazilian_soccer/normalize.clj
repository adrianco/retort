(ns brazilian-soccer.normalize
  "=============================================================================
   Brazilian Soccer MCP Server - Text & Value Normalization
   =============================================================================

   CONTEXT
     The provided Kaggle datasets are messy in three ways that this namespace
     exists to tame:

       1. Team names carry inconsistent suffixes:
            \"Palmeiras-SP\", \"América - MG\", \"Nacional (URU)\",
            \"Barcelona-EQU\", \"Sao Paulo\" vs \"São Paulo\".
          We need ONE canonical key per club so the same team in different
          files (and different query phrasings) resolves to the same node.

       2. Dates appear in several formats:
            ISO          \"2023-09-24\"
            ISO+time     \"2012-05-19 18:30:00\"
            Brazilian    \"29/03/2003\"
          We normalize every date to an ISO \"YYYY-MM-DD\" string for
          comparison and display.

       3. Numbers are sometimes ints (1), floats (\"1.0\") or quoted (\"2\").

   PUBLIC API
     canonical-key   - accent-folded, suffix-stripped lookup key for a team
     clean-team-name - human-friendly display name (suffix stripped, trimmed)
     fold-accents    - strip diacritics for accent-insensitive matching
     normalize-text  - fold-accents + lowercase + collapse whitespace
     parse-date      - any supported date string -> \"YYYY-MM-DD\" (or nil)
     parse-int       - lenient integer parse handling floats/quotes/blanks
     blank?          - nil-or-empty-after-trim test
   ============================================================================="
  (:require [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]))

(defn blank?
  "True when s is nil or contains only whitespace."
  [s]
  (or (nil? s) (str/blank? s)))

(defn fold-accents
  "Remove diacritical marks: \"São\" -> \"Sao\", \"Grêmio\" -> \"Gremio\".
   Returns \"\" for nil so it is always safe to compose with str ops."
  [s]
  (if (nil? s)
    ""
    (-> (Normalizer/normalize s Normalizer$Form/NFD)
        (str/replace #"\p{InCombiningDiacriticalMarks}+" ""))))

(defn normalize-text
  "Lower-cased, accent-folded, whitespace-collapsed form of any string.
   Used as the generic case/accent-insensitive comparison form."
  [s]
  (-> (fold-accents s)
      (str/lower-case)
      (str/replace #"\s+" " ")
      (str/trim)))

;; ----------------------------------------------------------------------------
;; Team name handling
;; ----------------------------------------------------------------------------

(def ^:private suffix-patterns
  "Trailing region/state/country markers we strip from a raw team name.
   Applied repeatedly so chained suffixes (rare) are all removed."
  [#"\s*\([A-Za-z]{2,4}\)\s*$"     ; \"Nacional (URU)\"
   #"\s*[-–]\s*[A-Za-z]{2,4}\s*$"]) ; \"Palmeiras-SP\", \"América - MG\", \"Barcelona-EQU\"

(defn clean-team-name
  "Strip state/country suffixes and surrounding whitespace, preserving accents
   and capitalization for display. \"América - MG\" -> \"América\"."
  [raw]
  (when raw
    (loop [s (str/trim raw)]
      (let [s' (reduce (fn [acc re] (str/replace acc re "")) s suffix-patterns)
            s' (str/trim s')]
        (if (or (= s' s) (str/blank? s'))
          ;; If stripping emptied the string, keep the previous value.
          (if (str/blank? s') s s')
          (recur s'))))))

(defn canonical-key
  "Lookup key uniquely identifying a club.

   IMPORTANT: unlike clean-team-name, this does NOT discard the state/country
   suffix, because several distinct clubs share a base name and are told apart
   only by it (e.g. Atlético-MG vs Atlético-PR vs Atlético-GO; América-MG vs
   América-RN; Botafogo-RJ vs Botafogo-PB). Dropping the suffix would wrongly
   merge them.

   The key folds accents, lower-cases, and turns any run of separator/punctuation
   characters into a single space, so the many spellings of one club collapse:
     \"Atlético-MG\", \"Atletico - MG\", \"atlético  mg\"  -> \"atletico mg\"
     \"Palmeiras-SP\"                                       -> \"palmeiras sp\"
     \"Nacional (URU)\"                                     -> \"nacional uru\"
   A query without a suffix (\"Palmeiras\" -> \"palmeiras\") still matches via the
   substring containment used by the query layer."
  [raw]
  (when raw
    (-> (fold-accents raw)
        (str/lower-case)
        (str/replace #"[^a-z0-9]+" " ")
        (str/trim)
        (str/replace #"\s+" " "))))

;; ----------------------------------------------------------------------------
;; Number parsing
;; ----------------------------------------------------------------------------

(defn parse-int
  "Lenient integer parse. Handles \"1\", \"1.0\", \" 2 \", 3, nil, \"\".
   Returns nil when the value is blank or non-numeric."
  [v]
  (cond
    (integer? v) v
    (number? v)  (long v)
    (blank? v)   nil
    :else (let [s (str/trim (str v))]
            (try
              (long (Double/parseDouble s))
              (catch Exception _ nil)))))

;; ----------------------------------------------------------------------------
;; Date parsing
;; ----------------------------------------------------------------------------

(defn parse-date
  "Normalize a date string to ISO \"YYYY-MM-DD\". Supports:
     \"2023-09-24\"            (ISO)
     \"2012-05-19 18:30:00\"   (ISO + time)
     \"29/03/2003\"            (Brazilian DD/MM/YYYY)
   Returns nil when the input is blank or unrecognized."
  [s]
  (when-not (blank? s)
    (let [s (str/trim s)]
      (cond
        ;; ISO date, optionally followed by a time component.
        (re-find #"^\d{4}-\d{2}-\d{2}" s)
        (subs s 0 10)

        ;; Brazilian DD/MM/YYYY (time, if any, ignored).
        (re-find #"^\d{1,2}/\d{1,2}/\d{4}" s)
        (let [[d m y] (-> (re-find #"^(\d{1,2})/(\d{1,2})/(\d{4})" s)
                          (rest))]
          (format "%s-%02d-%02d"
                  y (Integer/parseInt m) (Integer/parseInt d)))

        :else nil))))

(defn year-of
  "Extract the integer year from a normalized or raw date string, or nil."
  [s]
  (when-let [iso (parse-date s)]
    (parse-int (subs iso 0 4))))
