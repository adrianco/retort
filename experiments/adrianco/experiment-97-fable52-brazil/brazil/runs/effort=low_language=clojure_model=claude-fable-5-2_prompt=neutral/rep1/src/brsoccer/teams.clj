(ns brsoccer.teams
  "Team-name normalisation.

  The datasets spell the same club many ways (\"Palmeiras-SP\", \"Palmeiras - SP\",
  \"Palmeiras\", \"Sao Paulo\", \"São Paulo\", \"Atletico Mineiro\", \"Atlético - MG\").
  Every raw name is parsed to a folded `:base` plus an optional state/country
  `:state`; `team-key` then turns that into one canonical key per club."
  (:require [clojure.string :as str])
  (:import (java.text Normalizer Normalizer$Form)))

(defn strip-accents [s]
  (-> (Normalizer/normalize (str s) Normalizer$Form/NFD)
      (str/replace #"\p{M}+" "")))

(defn fold
  "Lower-case, accent-free, trimmed form used for all comparisons."
  [s]
  (-> (str s) strip-accents str/lower-case str/trim))

(def states
  #{"AC" "AL" "AP" "AM" "BA" "CE" "DF" "ES" "GO" "MA" "MT" "MS" "MG" "PA"
    "PB" "PR" "PE" "PI" "RJ" "RN" "RS" "RO" "RR" "SC" "SP" "SE" "TO"})

(def ^:private aliases
  "Folded full name -> [base state]."
  {"atletico mineiro"                ["atletico" "MG"]
   "atletico goianiense"             ["atletico" "GO"]
   "atletico paranaense"             ["athletico" "PR"]
   "athletico paranaense"            ["athletico" "PR"]
   "vasco da gama"                   ["vasco" "RJ"]
   "cr vasco da gama"                ["vasco" "RJ"]
   "sport recife"                    ["sport" "PE"]
   "sport club do recife"            ["sport" "PE"]
   "america mineiro"                 ["america" "MG"]
   "america minas gerais"            ["america" "MG"]
   "america natal"                   ["america" "RN"]
   "red bull bragantino"             ["bragantino" "SP"]
   "rb bragantino"                   ["bragantino" "SP"]
   "nautico capibaribe"              ["nautico" "PE"]
   "portuguesa desportos"            ["portuguesa" "SP"]
   "cs alagoano"                     ["csa" "AL"]
   "clube do remo"                   ["remo" "PA"]
   "ceara sporting club"             ["ceara" "CE"]
   "brasil de pelotas"               ["brasil" "RS"]
   "gremio novorizontino"            ["novorizontino" "SP"]
   "gremio barueri"                  ["barueri" "SP"]
   "sport club corinthians paulista" ["corinthians" "SP"]
   "corinthians paulista"            ["corinthians" "SP"]
   "cr flamengo"                     ["flamengo" "RJ"]
   "clube de regatas do flamengo"    ["flamengo" "RJ"]
   "flamengo do piaui"               ["flamengo" "PI"]
   "moto clube"                      ["moto club" "MA"]
   "moto club de sao luis"           ["moto club" "MA"]
   "xv piracicaba"                   ["xv de piracicaba" "SP"]
   "operario ferroviario esporte c"  ["operario" "PR"]
   "operario ferroviario"            ["operario" "PR"]
   "se palmeiras"                    ["palmeiras" "SP"]
   "sao paulo futebol clube"         ["sao paulo" "SP"]})

(def ^:private default-state
  "Home state assumed when a well-known club name appears without a suffix."
  {"flamengo" "RJ" "fluminense" "RJ" "botafogo" "RJ" "vasco" "RJ"
   "santos" "SP" "guarani" "SP" "palmeiras" "SP" "corinthians" "SP"
   "sao paulo" "SP" "portuguesa" "SP" "bragantino" "SP"
   "internacional" "RS" "juventude" "RS" "gremio" "RS"
   "vitoria" "BA" "bahia" "BA" "santa cruz" "PE" "sport" "PE" "nautico" "PE"
   "athletico" "PR" "parana" "PR" "coritiba" "PR" "cruzeiro" "MG"
   "fortaleza" "CE" "ceara" "CE" "goias" "GO" "avai" "SC" "criciuma" "SC"
   "chapecoense" "SC" "figueirense" "SC" "csa" "AL" "crb" "AL"})

(def ^:private display-override
  {"athletico" "Athletico-PR" "vasco" "Vasco da Gama" "sport" "Sport Recife"
   "atletico-mg" "Atlético-MG" "atletico-go" "Atlético-GO"
   "america-mg" "América-MG" "america-rn" "América-RN"
   "bragantino" "Red Bull Bragantino" "csa" "CSA" "crb" "CRB" "abc" "ABC"
   "asa" "ASA"})

(def ^:private noise-tokens #{"fc" "ec"})
(def ^:private leading-noise #{"ad" "ae" "ca" "ce" "se" "ge" "cs" "sc"})

(defn- join-initials
  "\"c r b\" -> \"crb\": runs of two or more single-letter tokens are acronyms."
  [tokens]
  (->> (partition-by #(= 1 (count %)) tokens)
       (mapcat (fn [grp] (if (and (= 1 (count (first grp))) (> (count grp) 1))
                           [(apply str grp)]
                           grp)))))

(defn- clean-base [s]
  (let [tokens (-> (fold s)
                   (str/replace "." " ")
                   (str/replace #"[^a-z0-9]+" " ")
                   str/trim
                   (str/split #"\s+"))
        joined (str/join " " (join-initials tokens))]
    (or (aliases joined)
        (let [s2     (-> joined
                         (str/replace #"\b(futebol|esporte) clube\b" "")
                         str/trim)
              toks   (remove noise-tokens (str/split s2 #"\s+"))
              toks   (if (and (next toks) (leading-noise (first toks))) (rest toks) toks)
              final  (str/join " " toks)]
          (or (aliases final) [(if (str/blank? final) joined final) nil])))))

(defn- split-suffix
  "Returns [name state-or-country] by peeling a trailing \"-SP\", \" - SP\",
  \" SP\", \"(URU)\" or \"-URU\" marker."
  [s lenient?]
  (let [s (str/trim (str s))
        hy (re-matches #"(?s)^(.*?)\s*-\s*([A-Za-z]{2})$" s)
        sp (re-matches (if lenient? #"(?s)^(.*\S)\s+([A-Za-z]{2})$" #"(?s)^(.*\S)\s+([A-Z]{2})$") s)
        co (or (re-matches #"(?s)^(.*?)\s*\(([A-Z]{3})\)$" s)
               (re-matches #"(?s)^(.*?\S)-([A-Z]{3})$" s))]
    (cond
      (and hy (states (str/upper-case (hy 2)))) [(hy 1) (str/upper-case (hy 2))]
      (and sp (states (str/upper-case (sp 2)))) [(sp 1) (str/upper-case (sp 2))]
      co                                        [(co 1) (co 2)]
      :else                                     [s nil])))

(defn parse
  "Parse a raw team name into {:base folded-name :state code-or-nil :label display}.
  `hint-state` is used when the name itself carries no suffix (e.g. a UF column)."
  ([raw] (parse raw nil false))
  ([raw hint-state] (parse raw hint-state false))
  ([raw hint-state lenient?]
   (let [[nm st]        (split-suffix raw lenient?)
         label          (-> nm (str/replace #"\s*\([^)]*\)" "") str/trim)
         [base alias-st] (clean-base nm)
         ;; UF columns contain typos (Bahia tagged "BH", Vitória tagged "ES"),
         ;; so a hint never overrides a well-known club's home state.
         st             (or st alias-st
                            (when-not (or (str/blank? hint-state) (default-state base))
                              hint-state))
         base           (if (and (= base "atletico") (= st "PR")) "athletico" base)]
     {:base base :state st :label label :aliased? (boolean alias-st)})))

(defn build-index
  "From every parsed name in the data, remember bases that only ever occur with
  one state, so \"Londrina\" and \"Londrina - PR\" collapse to the same club."
  [parsed]
  (let [by-base (reduce (fn [m {:keys [base state]}]
                          (if state (update m base (fnil conj #{}) state) m))
                        {} parsed)]
    {:single (into {} (keep (fn [[b sts]] (when (= 1 (count sts)) [b (first sts)]))) by-base)}))

(defn key-suffix
  "State/country discriminator needed to tell this club from its namesakes, or nil."
  [index {:keys [base state]}]
  (let [dflt (or (default-state base) (get (:single index) base))]
    (when (and state (not= state dflt)) state)))

(defn team-key [index parsed]
  (if-let [sfx (key-suffix index parsed)]
    (str (:base parsed) "-" (str/lower-case sfx))
    (:base parsed)))

(defn display-name
  "Pick the nicest spelling seen for a key: prefer accented forms, then the most common."
  [index k parsed-names]
  (or (display-override k)
      (let [own    (remove :aliased? parsed-names)
            exact  (filter #(= (:base %) (first (clean-base (:label %)))) own)
            exact' (filter #(= (:base %) (str/replace (fold (:label %)) #"[^a-z0-9]+" " ")) exact)
            freqs  (frequencies (map :label (first (filter seq [exact' exact own parsed-names]))))
            accent (fn [s] (count (remove #(< (int %) 128) s)))
            best   (first (apply max-key (fn [[l n]] (+ (* 100000 (accent l)) n)) (seq freqs)))
            sfx    (key-suffix index (first parsed-names))]
        (if sfx (str best "-" sfx) best))))

(def derbies
  "Traditional rivalries as [key-a key-b name]."
  [["flamengo" "fluminense" "Fla-Flu"]
   ["flamengo" "vasco" "Clássico dos Milhões"]
   ["flamengo" "botafogo" "Clássico da Rivalidade"]
   ["fluminense" "vasco" "Clássico dos Gigantes"]
   ["fluminense" "botafogo" "Clássico Vovô"]
   ["botafogo" "vasco" "Clássico da Amizade"]
   ["corinthians" "palmeiras" "Derby Paulista"]
   ["corinthians" "sao paulo" "Majestoso"]
   ["palmeiras" "sao paulo" "Choque-Rei"]
   ["corinthians" "santos" "Clássico Alvinegro"]
   ["palmeiras" "santos" "Clássico da Saudade"]
   ["santos" "sao paulo" "San-São"]
   ["gremio" "internacional" "Grenal"]
   ["atletico-mg" "cruzeiro" "Clássico Mineiro"]
   ["bahia" "vitoria" "Ba-Vi"]
   ["athletico" "coritiba" "Atletiba"]
   ["sport" "nautico" "Clássico dos Clássicos"]
   ["sport" "santa cruz" "Clássico das Multidões"]
   ["nautico" "santa cruz" "Clássico das Emoções"]
   ["ceara" "fortaleza" "Clássico-Rei"]
   ["goias" "vila nova" "Derby do Cerrado"]
   ["avai" "figueirense" "Clássico de Florianópolis"]
   ["remo" "paysandu" "Re-Pa"]
   ["crb" "csa" "Clássico das Multidões (AL)"]])

(def derby-index
  (into {} (map (fn [[a b n]] [#{a b} n])) derbies))
