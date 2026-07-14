;; =============================================================================
;; brazilian-soccer.normalize
;; -----------------------------------------------------------------------------
;; Team-name and text normalisation helpers.
;;
;; The Kaggle datasets use inconsistent naming conventions for the same team:
;;   - with a state suffix:        "Palmeiras-SP", "Flamengo-RJ"
;;   - with a spaced suffix:        "América - MG"
;;   - with a country code:         "Nacional (URU)", "Barcelona-EQU"
;;   - with accents / casing:       "São Paulo" vs "Sao Paulo"
;;   - with trailing descriptors:   "Boavista Sport Club (antigo ...) - RJ"
;;
;; To match teams across files we compute:
;;   display-name : a cleaned, human-readable label (suffix stripped, trimmed)
;;   match-key    : an accent-free, lower-case, punctuation-free key used for
;;                  equality / substring comparison during search.
;;
;; All input is treated as UTF-8 so Brazilian Portuguese characters survive.
;; =============================================================================
(ns brazilian-soccer.normalize
  (:require [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]))

(defn strip-accents
  "Remove diacritics (accents, cedilla) from `s` using Unicode NFD decomposition.
   \"São Paulo\" -> \"Sao Paulo\", \"Grêmio\" -> \"Gremio\"."
  [s]
  (when s
    (-> (Normalizer/normalize s Normalizer$Form/NFD)
        (str/replace #"\p{InCombiningDiacriticalMarks}+" ""))))

;; Trailing " - RJ", "-SP", " (URU)", "-EQU" style location suffixes.
(def ^:private state-suffix-re
  #"(?i)[\s\-–]*(?:\([A-Z]{2,3}\)|[\-–]\s*[A-Z]{2,3})\s*$")

;; Parenthetical descriptors such as "(antigo Esporte Clube Barreira)".
(def ^:private paren-descriptor-re
  #"\s*\([^)]*\)\s*")

(defn clean-team
  "Produce a human-readable display name for a raw team string.
   Strips a trailing state/country suffix and any parenthetical descriptor,
   then collapses whitespace.  Returns nil for blank input."
  [raw]
  (when (some? raw)
    (let [s (-> raw
                str/trim
                (str/replace state-suffix-re "")
                (str/replace paren-descriptor-re " ")
                (str/replace #"\s+" " ")
                str/trim)]
      (when-not (str/blank? s) s))))

(defn match-key
  "Accent-free, lower-case, alphanumeric key for fuzzy team matching.
   Built from the cleaned display name so suffixes do not affect it."
  [raw]
  (some-> (clean-team raw)
          strip-accents
          str/lower-case
          (str/replace #"[^a-z0-9]+" " ")
          str/trim
          (str/replace #"\s+" " ")))

(defn id-key
  "State-preserving identity key for a team. Unlike match-key this keeps the
   state/country code so genuinely different clubs that share a base name remain
   distinct: \"Atlético-MG\" -> \"atletico mg\", \"Atlético-GO\" -> \"atletico go\",
   \"Athletico-PR\" -> \"athletico pr\". Accent-folded, lower-case, punctuation
   collapsed to single spaces. Used for grouping (standings) and cross-file
   de-duplication; match-key remains the looser key for fuzzy user search."
  [raw]
  (when (some? raw)
    (let [k (-> raw
                str/trim
                (str/replace paren-descriptor-re " ")
                strip-accents
                str/lower-case
                (str/replace #"[^a-z0-9]+" " ")
                str/trim
                (str/replace #"\s+" " "))]
      (when-not (str/blank? k) k))))

(defn team-uid
  "Canonical team identity used for grouping (standings) and cross-file
   de-duplication. Built from the *stripped* base name plus an explicit state /
   UF code when the dataset supplies one in a dedicated column:

     (team-uid \"Flamengo-RJ\" \"RJ\") => \"flamengo rj\"
     (team-uid \"Flamengo\"    \"RJ\") => \"flamengo rj\"   ; aligns the two files
     (team-uid \"Atlético-MG\" \"MG\") => \"atletico mg\"
     (team-uid \"Atlético-GO\" \"GO\") => \"atletico go\"   ; stays distinct

   When no state column is available (Libertadores, Copa do Brasil, BR-Football)
   it falls back to id-key, which preserves a dash-style suffix embedded in the
   name (\"Barcelona-EQU\" => \"barcelona equ\")."
  [raw state]
  (let [state (some-> state strip-accents str/lower-case str/trim)]
    (if (and state (not (str/blank? state)) (match-key raw))
      ;; dataset supplies the state in its own column: stripped base + state
      (str (match-key raw) " " state)
      ;; no state column: keep any suffix embedded in the name itself
      (id-key raw))))

(defn matches-team?
  "True when a stored team `team-key` should be considered a match for a user
   `query` string.  Matching is symmetric-substring on the normalised keys so
   \"flamengo\" matches \"flamengo\", and \"sao paulo\" matches \"sao paulo fc\"."
  [team-key query]
  (let [q (match-key query)]
    (boolean
     (and team-key q (not (str/blank? q))
          (or (= team-key q)
              (str/includes? team-key q)
              (str/includes? q team-key))))))
