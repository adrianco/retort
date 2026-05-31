(ns brazilian-soccer.normalize
  "Context
  =======
  Brazilian soccer datasets use wildly inconsistent team-name conventions:

    * State suffixes      \"Palmeiras-SP\", \"America-MG\", \"América - MG\"
    * Country codes        \"Nacional (URU)\", \"Barcelona-EQU\"
    * Accented variants    \"Gremio\" vs \"Grêmio\", \"Avai\" vs \"Avaí\"
    * Corporate words      \"EC Bahia\", \"Fortaleza FC\", \"Sport Recife\"
    * Trailing city/state  \"Botafogo RJ\", \"Vasco Da Gama RJ\"
    * Ambiguous shorthand  \"Atlético\" (Mineiro) vs \"Athletico\" (Paranaense)

  This namespace produces a stable *canonical key* per club used for equality,
  grouping (standings) and fuzzy query matching, while keeping genuinely
  different clubs apart. All input is treated as UTF-8.

  Strategy:
    1. Normalise to accent-free, lower-case, dash->space, collapsed whitespace.
    2. Consult an explicit alias table for the handful of clubs whose variants
       can't be reconciled mechanically (the Atlético/Athletico family, Vasco,
       América, corporate-name reductions, …).
    3. Otherwise apply a generic cleanup that drops trailing state codes and
       corporate tokens."
  (:require [clojure.string :as str])
  (:import (java.text Normalizer Normalizer$Form)))

(defn strip-accents
  "Remove diacritics (São -> Sao, Grêmio -> Gremio)."
  [^String s]
  (when s
    (-> (Normalizer/normalize s Normalizer$Form/NFD)
        (str/replace #"\p{InCombiningDiacriticalMarks}+" ""))))

(def ^:private state-codes
  #{"ac" "al" "ap" "am" "ba" "ce" "df" "es" "go" "ma" "mt" "ms" "mg" "pa"
    "pb" "pr" "pe" "pi" "rj" "rn" "rs" "ro" "rr" "sc" "se" "sp" "to"})

(def ^:private corporate-tokens
  #{"fc" "ec" "sc" "ac" "cf" "fbc" "afc" "sport"})

(defn strip-suffix
  "Drop a trailing state/country qualifier from a display name."
  [^String s]
  (when s
    (-> s
        (str/replace #"\s*\([A-Za-z]{2,3}\)\s*$" "")
        (str/replace #"\s*-\s*[A-Za-z]{2,3}\s*$" "")
        (str/trim))))

(defn display-name
  "Tidy display form: state/country suffix removed, whitespace collapsed,
  original accents kept. nil for blank input."
  [s]
  (when s
    (let [d (-> s strip-suffix (str/replace #"\s+" " ") str/trim)]
      (when-not (str/blank? d) d))))

(defn- normalize-base
  "accent-free, lower-case, dashes->spaces, collapsed whitespace."
  [s]
  (some-> s
          strip-accents
          str/lower-case
          (str/replace #"-" " ")
          (str/replace #"[().]" " ")
          (str/replace #"\s+" " ")
          str/trim))

;; Explicit alias table: normalized variant -> canonical key. Resolves the
;; cases generic rules can't (ambiguous shorthands, multi-word reductions).
(def ^:private aliases
  (let [m {;; Atlético family — must stay distinct from one another.
           "athletico paranaense" :athletico-pr
           "atletico paranaense"  :athletico-pr
           "athletico"            :athletico-pr ; the 'h' spelling = Paranaense
           "atletico pr"          :athletico-pr
           "atletico mineiro"     :atletico-mg
           "atletico"             :atletico-mg ; bare/accented form = Mineiro
           "atletico mg"          :atletico-mg
           "atletico goianiense"  :atletico-go
           "atletico go"          :atletico-go
           ;; Vasco
           "vasco"                :vasco
           "vasco da gama"        :vasco
           "vasco da gama rj"     :vasco
           ;; América (Minas) — collapse the common Serie A variants.
           "america"              :america-mg
           "america mg"           :america-mg
           "america fc minas gerais" :america-mg
           ;; Corporate / city reductions.
           "ec bahia"             :bahia
           "bahia"                :bahia
           "fortaleza fc"         :fortaleza
           "fortaleza"            :fortaleza
           "sport recife"         :sport-recife
           "sport club do recife" :sport-recife
           "sport"                :sport-recife
           "ec juventude"         :juventude
           "juventude"            :juventude
           "santa cruz fc"        :santa-cruz
           "santa cruz"           :santa-cruz
           "red bull bragantino"  :bragantino
           "rb bragantino"        :bragantino
           "bragantino"           :bragantino
           "botafogo rj"          :botafogo
           "botafogo"             :botafogo}]
    m))

(defn- generic-key
  "Fallback canonicalisation: strip trailing state codes and corporate tokens."
  [base]
  (let [tokens (-> base (str/split #"\s") vec)
        ;; drop trailing state codes (e.g. \"coritiba pr\" -> \"coritiba\")
        tokens (loop [t tokens]
                 (if (and (> (count t) 1) (state-codes (peek t)))
                   (recur (subvec t 0 (dec (count t))))
                   t))
        ;; drop corporate tokens anywhere (but never empty the name)
        kept (vec (remove corporate-tokens tokens))
        kept (if (seq kept) kept tokens)]
    (str/join " " kept)))

(defn match-key
  "Canonical key for a team name. Equal keys == same club.

    (match-key \"Grêmio-RS\")        => \"gremio\"
    (match-key \"Atlético\")         => \"atletico-mg\"
    (match-key \"Athletico-PR\")     => \"athletico-pr\"
    (match-key \"Vasco Da Gama RJ\") => \"vasco\""
  [s]
  (let [base (normalize-base s)            ; suffix kept as tokens: "atletico pr"
        stripped (normalize-base (strip-suffix s))] ; suffix removed: "nacional"
    (when (and base (seq base))
      (cond
        ;; Alias on the full form first so the -PR/-MG/-GO suffix can
        ;; disambiguate the Atlético clubs before it is discarded.
        (aliases base)     (name (aliases base))
        (aliases stripped) (name (aliases stripped))
        ;; Otherwise clean up the suffix-stripped form (handles 2/3-letter
        ;; country codes like URU/EQU and parenthesised codes via strip-suffix).
        :else (generic-key (or stripped base))))))

(defn team-matches?
  "True when `candidate` refers to the same team as the user's `query`.
  Exact canonical-key equality, or shorter key contained in the longer one
  (so \"corinthians\" matches \"Sport Club Corinthians Paulista\")."
  [query candidate]
  (let [q (match-key query)
        c (match-key candidate)]
    (boolean
     (and (seq q) (seq c)
          (or (= q c)
              (str/includes? c q)
              (str/includes? q c))))))
