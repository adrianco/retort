(ns soccer.normalize
  "=============================================================================
   soccer.normalize — Team-name / date / number normalization helpers
   -----------------------------------------------------------------------------
   PURPOSE
     The provided Kaggle datasets use several naming and formatting conventions
     (see the 'Data Quality Notes' section of the spec). This namespace turns
     those raw strings into consistent values so that data from different files
     can be matched and aggregated together.

   KEY CONCEPTS
     display-name : a tidied full name that *keeps* the state/country suffix so
                    distinct clubs stay distinct, e.g.
                      \"América - MG\"  -> \"América-MG\"
                      \"Atletico-PR\"   -> \"Atletico-PR\"   (≠ Atletico-MG)
     team-key     : accent-folded, lower-cased, punctuation-free key built from
                    the display-name, used for *grouping* matches into teams,
                    e.g. \"São Paulo-SP\" -> \"sao paulo sp\"
     canonical    : the short display name with the suffix stripped, e.g.
                    \"Palmeiras-SP\" -> \"Palmeiras\" (handy for loose lookups)

   Distinct clubs that share a base name (Atlético-MG, Atlético-PR, Atlético-GO)
   keep separate team-keys; a bare user query (\"Flamengo\") still matches the
   suffixed name (\"Flamengo-RJ\") through the substring logic in team-matches?.

   PUBLIC API
     (display-name s)   -> tidied full name (suffix preserved)
     (canonical s)      -> short display name (suffix stripped)
     (team-key s)       -> normalized grouping key (suffix preserved)
     (team-matches? q t)-> does query q refer to team t? (substring on keys)
     (norm-date s)      -> ISO yyyy-MM-dd, handling ISO / BR / datetime inputs
     (->int s)          -> long or nil
     (->double s)       -> double or nil
   ============================================================================="
  (:require [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]))

(defn strip-accents
  "Fold accented characters to ASCII: \"Grêmio\" -> \"Gremio\"."
  [^String s]
  (when s
    (-> (Normalizer/normalize s Normalizer$Form/NFD)
        (str/replace #"\p{InCombiningDiacriticalMarks}+" ""))))

(defn display-name
  "Tidy a team name while keeping any state/country suffix so distinct clubs
   stay distinct: \"América - MG\" -> \"América-MG\", \"Atletico-PR\" unchanged."
  [s]
  (when s
    (-> (str s)
        (str/replace #"\s*-\s*([A-Za-z]{2})\s*$" "-$1") ; " - MG" -> "-MG"
        str/trim)))

(defn canonical
  "Strip a trailing state suffix (\"-SP\", \" - MG\") or country code
   (\" (URU)\") from a team name and trim. Returns the short display name."
  [s]
  (when s
    (-> (str s)
        (str/replace #"\s*\(([A-Za-z]{2,3})\)\s*$" "") ; (URU) (EQU) (PAR) ...
        (str/replace #"\s*-\s*[A-Z]{2}\s*$" "")        ; -SP   - MG
        str/trim)))

(defn team-key
  "Accent-folded, lower-cased, whitespace-collapsed grouping key built from the
   full display-name (suffix preserved): \"São Paulo-SP\" -> \"sao paulo sp\"."
  [s]
  (when s
    (-> (display-name s)
        strip-accents
        str/lower-case
        (str/replace #"[^a-z0-9]+" " ")
        str/trim)))

(defn team-matches?
  "True when query `q` plausibly refers to team `t`. Matching is done on the
   normalized team-keys and is symmetric/substring so that \"Flamengo\" matches
   \"Flamengo-RJ\" and \"Inter\" matches \"Internacional\"."
  [q t]
  (let [qk (team-key q)
        tk (team-key t)]
    (and (seq qk) (seq tk)
         (or (= qk tk)
             (str/includes? tk qk)
             (str/includes? qk tk)))))

(defn norm-date
  "Normalize the several date formats found in the data to ISO yyyy-MM-dd:
     \"2012-05-19 18:30:00\" -> \"2012-05-19\"
     \"2023-09-24\"          -> \"2023-09-24\"
     \"29/03/2003\"          -> \"2003-03-29\""
  [s]
  (let [s (some-> s str str/trim)]
    (cond
      (str/blank? s) nil
      (re-find #"^\d{4}-\d{2}-\d{2}" s) (subs s 0 10)
      (re-find #"^\d{2}/\d{2}/\d{4}" s) (let [[d m y] (str/split (subs s 0 10) #"/")]
                                          (str y "-" m "-" d))
      :else s)))

(defn ->double
  "Parse a possibly-blank numeric string to double, else nil."
  [s]
  (let [s (some-> s str str/trim)]
    (when-not (str/blank? s)
      (try (Double/parseDouble s) (catch Exception _ nil)))))

(defn ->int
  "Parse a possibly-blank numeric string (\"2\" or \"2.0\") to long, else nil."
  [s]
  (some-> (->double s) long))

(defn year-of
  "Extract the 4-digit year from a normalized ISO date string, or nil."
  [iso-date]
  (when (and iso-date (re-find #"^\d{4}" iso-date))
    (->int (subs iso-date 0 4))))
