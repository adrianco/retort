(ns brazilian-soccer.normalize
  "=============================================================================
   normalize.clj — Team / text normalization helpers
   -----------------------------------------------------------------------------
   Context:
     The provided datasets use several naming conventions for the same team:
       * with a state suffix      -> \"Palmeiras-SP\", \"Flamengo-RJ\"
       * with a spaced suffix     -> \"América - MG\"
       * with a country code      -> \"Nacional (URU)\", \"Barcelona-EQU\"
       * full / verbose names     -> \"Sport Club Corinthians Paulista\"
     Match queries therefore need a stable, accent-insensitive key so that a
     user typing \"sao paulo\", \"São Paulo\" or \"Sao Paulo-SP\" all resolve to
     the same club.

   This namespace provides:
     * display-name  — a human readable name with the state/country tag removed
     * match-key     — a lowercase, accent-stripped, punctuation-free key used
                       for substring matching
     * matches?      — does a normalized query substring-match a team name
   ============================================================================="
  (:require [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]))

(defn strip-accents
  "Remove diacritics so \"São\" -> \"Sao\", \"Grêmio\" -> \"Gremio\"."
  [^String s]
  (when s
    (-> (Normalizer/normalize s Normalizer$Form/NFD)
        (str/replace #"\p{InCombiningDiacriticalMarks}+" ""))))

(defn display-name
  "Strip a trailing state abbreviation or country code from a raw team name.
   Examples:
     \"Palmeiras-SP\"      -> \"Palmeiras\"
     \"América - MG\"      -> \"América\"
     \"Nacional (URU)\"    -> \"Nacional\"
     \"Barcelona-EQU\"     -> \"Barcelona\""
  [raw]
  (when raw
    (-> raw
        str/trim
        ;; trailing \" (XXX)\" country code, e.g. Nacional (URU)
        (str/replace #"\s*\([A-Za-z]{2,4}\)\s*$" "")
        ;; trailing \"-SP\" / \" - MG\" state or \"-EQU\" country code
        (str/replace #"\s*-\s*[A-Za-z]{2,3}\s*$" "")
        str/trim)))

(defn match-key
  "Lowercase, accent-stripped, alphanumeric-only key for fuzzy matching."
  [raw]
  (when raw
    (-> raw
        display-name
        strip-accents
        str/lower-case
        (str/replace #"[^a-z0-9]+" ""))))

(defn matches?
  "True when `query` substring-matches `team-name` after normalization.
   Empty / nil query never matches."
  [query team-name]
  (let [q (match-key query)
        t (match-key team-name)]
    (boolean (and q t (seq q) (str/includes? t q)))))
