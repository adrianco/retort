;; =============================================================================
;; soccer.normalize — Team-name and date normalization
;; -----------------------------------------------------------------------------
;; Project: brazilian-soccer-mcp
;;
;; Context:
;;   The provided datasets use several different naming conventions for teams:
;;     - with a state suffix       : "Palmeiras-SP", "Flamengo-RJ"
;;     - with a spaced state token : "America MG", "Boavista RJ"
;;     - with a country code        : "Nacional (URU)", "Barcelona-EQU"
;;     - full club names            : "Sport Club Corinthians Paulista"
;;     - ASCII vs accented          : "Sao Paulo" vs "São Paulo"
;;   Dates appear as ISO ("2023-09-24"), ISO+time ("2012-05-19 18:30:00") and
;;   Brazilian ("29/03/2003").
;;
;; Responsibility:
;;   Provide pure helpers to (a) produce a stable canonical display name for a
;;   team, (b) produce an accent-insensitive match key used for comparisons,
;;   and (c) parse the various date formats into java.time.LocalDate.
;;
;; This namespace has no I/O and no external dependencies beyond java.time.
;; =============================================================================
(ns soccer.normalize
  (:require [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]
           [java.time LocalDate]
           [java.time.format DateTimeFormatter DateTimeParseException]))

(defn strip-accents
  "Remove diacritics from `s` (São -> Sao, Grêmio -> Gremio)."
  [s]
  (when s
    (-> (Normalizer/normalize s Normalizer$Form/NFD)
        (str/replace #"\p{InCombiningDiacriticalMarks}+" ""))))

;; Brazilian state abbreviations + neighbouring-country codes that appear as
;; suffixes in the datasets.  Used to strip "...-SP" / "... (URU)" style tags.
(def ^:private location-codes
  #{"AC" "AL" "AP" "AM" "BA" "CE" "DF" "ES" "GO" "MA" "MT" "MS" "MG" "PA" "PB"
    "PR" "PE" "PI" "RJ" "RN" "RS" "RO" "RR" "SC" "SP" "SE" "TO"
    "URU" "ARG" "EQU" "PAR" "CHI" "COL" "BOL" "PER" "VEN" "MEX" "USA" "BRA"})

(defn- strip-suffix
  "Drop a trailing state/country location token from a team name.
   Handles 'Palmeiras-SP', 'America MG', 'America - MG' and '(URU)' forms."
  [s]
  (let [s (str/trim s)
        ;; remove any parenthetical group, e.g. "Nacional (URU)" or
        ;; "Boavista (antigo ...) - RJ"
        s (-> s (str/replace #"\([^)]*\)" "") str/trim)
        ;; remove trailing " - XX", "-XX" or " XX" where XX is a location code
        s (str/replace s #"(?i)[\s-]+([A-Z]{2,3})$"
                       (fn [[whole code]]
                         (if (location-codes (str/upper-case code)) "" whole)))]
    (str/trim s)))

;; Canonical display names for the major clubs.  The key is the accent-stripped,
;; lower-cased, suffix-free form; the value is the preferred display spelling.
;; This unifies cross-dataset spelling variants (e.g. "Atletico Mineiro",
;; "Atletico-MG", "Atlético MG" all collapse to "Atlético Mineiro").
(def ^:private canonical-aliases
  {"flamengo"               "Flamengo"
   "fluminense"             "Fluminense"
   "palmeiras"              "Palmeiras"
   "santos"                 "Santos"
   "corinthians"            "Corinthians"
   "sport club corinthians paulista" "Corinthians"
   "sao paulo"              "São Paulo"
   "sao paulo fc"           "São Paulo"
   "gremio"                 "Grêmio"
   "internacional"          "Internacional"
   "cruzeiro"               "Cruzeiro"
   "atletico mineiro"       "Atlético Mineiro"
   "atletico mg"            "Atlético Mineiro"
   "clube atletico mineiro" "Atlético Mineiro"
   "atletico goianiense"    "Atlético Goianiense"
   "atletico go"            "Atlético Goianiense"
   "atletico paranaense"    "Athletico Paranaense"
   "athletico paranaense"   "Athletico Paranaense"
   "atletico pr"            "Athletico Paranaense"
   "athletico pr"           "Athletico Paranaense"
   "csa"                    "CSA"
   "csa al"                 "CSA"
   "botafogo"               "Botafogo"
   "vasco"                  "Vasco da Gama"
   "vasco da gama"          "Vasco da Gama"
   "bahia"                  "Bahia"
   "fortaleza"              "Fortaleza"
   "ceara"                  "Ceará"
   "sport"                  "Sport Recife"
   "sport recife"           "Sport Recife"
   "coritiba"               "Coritiba"
   "goias"                  "Goiás"
   "chapecoense"            "Chapecoense"
   "avai"                   "Avaí"
   "cuiaba"                 "Cuiabá"
   "america mineiro"        "América Mineiro"
   "america mg"             "América Mineiro"
   "red bull bragantino"    "Red Bull Bragantino"
   "bragantino"             "Red Bull Bragantino"
   "juventude"              "Juventude"
   "portuguesa"             "Portuguesa"})

(defn- norm-key
  "Lowercase, accent-stripped, punctuation-as-space, space-collapsed key."
  [s]
  (-> s strip-accents str/lower-case
      (str/replace #"[^a-z0-9]+" " ")
      str/trim
      (str/replace #"\s+" " ")))

(defn canonical-name
  "Return a stable, human-readable canonical name for a raw team string.
   Maps known spelling/suffix variants to one form by checking the alias table
   first against the full name (so 'America MG' -> 'América Mineiro') and then
   against the suffix-stripped name (so 'Palmeiras-SP' -> 'Palmeiras')."
  [raw]
  (when (and raw (not (str/blank? raw)))
    (let [base (strip-suffix raw)]
      (or (canonical-aliases (norm-key raw))
          (canonical-aliases (norm-key base))
          ;; default: keep the (suffix-stripped) original spelling
          base))))

(defn match-key
  "Accent-insensitive, punctuation-free key used to compare two team names.
   e.g. (match-key \"São Paulo FC\") => \"saopaulo\""
  [raw]
  (when (and raw (not (str/blank? raw)))
    (-> (canonical-name raw)
        strip-accents
        str/lower-case
        (str/replace #"[^a-z0-9]" ""))))

(defn same-team?
  "True when two raw team names refer to the same club."
  [a b]
  (let [ka (match-key a) kb (match-key b)]
    (boolean (and ka kb (= ka kb)))))

(defn name-matches?
  "True when `query` matches `team` exactly (by key) or as a substring.
   Lets a user type 'Atletico' and find 'Atlético Mineiro'."
  [query team]
  (let [kq (match-key query)
        kt (match-key team)]
    (boolean (and kq kt (or (= kq kt)
                            (str/includes? kt kq)
                            (str/includes? kq kt))))))

;; --- Date parsing ----------------------------------------------------------

(def ^:private iso-date    (DateTimeFormatter/ofPattern "yyyy-MM-dd"))
(def ^:private br-date     (DateTimeFormatter/ofPattern "dd/MM/yyyy"))
(def ^:private dot-date    (DateTimeFormatter/ofPattern "yyyy.MM.dd"))

(defn- try-parse [^String s ^DateTimeFormatter fmt]
  (try (LocalDate/parse s fmt)
       (catch DateTimeParseException _ nil)))

(defn parse-date
  "Parse a date string in any of the formats used by the datasets into a
   java.time.LocalDate, or nil if it cannot be parsed.
   Accepts: 'yyyy-MM-dd', 'yyyy-MM-dd HH:mm:ss', 'dd/MM/yyyy', 'yyyy.MM.dd'."
  [s]
  (when (and s (not (str/blank? s)) (not= "NA" (str/trim s)))
    (let [s (str/trim s)
          ;; keep only the date portion if a time is present
          d (first (str/split s #"[ T]"))]
      (or (try-parse d iso-date)
          (try-parse d br-date)
          (try-parse d dot-date)))))
