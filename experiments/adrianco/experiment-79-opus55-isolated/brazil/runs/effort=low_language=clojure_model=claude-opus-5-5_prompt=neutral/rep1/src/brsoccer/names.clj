(ns brsoccer.names
  "Team and competition name normalisation.

  The six datasets spell the same club in many ways (\"Palmeiras-SP\",
  \"Palmeiras - SP\", \"Palmeiras\"; \"Atlético Mineiro\", \"Atletico-MG\";
  \"Sport Recife\", \"Sport-PE\" ...). `team-key` maps every spelling to one
  canonical lower-case, accent-free key so matches from different files can
  be joined."
  (:require [clojure.string :as str])
  (:import (java.text Normalizer Normalizer$Form)))

(defn fold
  "Lower-cases, strips accents and collapses whitespace."
  [s]
  (-> (Normalizer/normalize (str s) Normalizer$Form/NFD)
      (str/replace #"\p{InCombiningDiacriticalMarks}+" "")
      str/lower-case
      (str/replace #"\s+" " ")
      str/trim))

(def ^:private states
  #{"ac" "al" "ap" "am" "ba" "ce" "df" "es" "go" "ma" "mt" "ms" "mg" "pa"
    "pb" "pr" "pe" "pi" "rj" "rn" "rs" "ro" "rr" "sc" "sp" "se" "to"})

(def ^:private aliases
  "Folded spelling (state suffix rewritten as a trailing token) -> key."
  {"atletico mg" "atletico-mg"
   "atletico mineiro" "atletico-mg"
   "atletico pr" "athletico-pr"
   "athletico pr" "athletico-pr"
   "athletico" "athletico-pr"
   "athletico paranaense" "athletico-pr"
   "atletico paranaense" "athletico-pr"
   "atletico go" "atletico-go"
   "atletico goianiense" "atletico-go"
   "atletico ac" "atletico acreano"
   "atletico ce" "atletico cearense"
   "atletico ba" "atletico alagoinhas"
   "america mg" "america-mg"
   "america mineiro" "america-mg"
   "america fc (minas gerais)" "america-mg"
   "america rn" "america-rn"
   "america natal" "america-rn"
   "america de natal" "america-rn"
   "vasco da gama" "vasco"
   "sport recife" "sport"
   "sport club do recife" "sport"
   "nautico capibaribe" "nautico"
   "portuguesa desportos" "portuguesa"
   "red bull bragantino" "bragantino"
   "ceara sporting club" "ceara"
   "cs alagoano" "csa"
   "c s a" "csa"
   "c r b" "crb"
   "c r a c" "crac"
   "a b c" "abc"
   "a s a" "asa"
   "clube do remo" "remo"
   "gremio barueri" "barueri"
   "boavista sport club (antigo esporte clube barreira)" "boavista"
   "boavista sc saquarema" "boavista"
   "brasil" "brasil de pelotas"
   "ser caxias" "caxias"
   "moto clube" "moto club"
   "moto club de sao luis" "moto club"
   "operario ferroviario esporte c" "operario"
   "flamengo do piaui" "flamengo-pi"
   "iv de julho" "4 de julho"
   "tolima" "deportes tolima"
   "xv piracicaba" "xv de piracicaba"
   "uniao de rondonopolis" "uniao rondonopolis"
   "souza" "sousa"
   "palmas ltda" "palmas"
   "palmas fr" "palmas"
   "parnahyba s c" "parnahyba"
   "real noroeste capixaba" "real noroeste"
   "retro fc brasil" "retro"
   "sao paulo futebol clube" "sao paulo"
   "campinense clube" "campinense"
   "afogados da ingazeira" "afogados"
   "aguia de maraba" "aguia"
   "america fc natal" "america-rn"
   "cs sergipe" "sergipe"
   "guarany" "guarany de sobral"
   "gremio novorizontino" "novorizontino"
   "rondonopolis" "uniao rondonopolis"
   "uniao" "uniao rondonopolis"
   "s francisco" "sao francisco-pa"
   "vitoria f c" "vitoria-es"
   "serra f c" "serra"
   "desportiva" "desportiva ferroviaria"
   "7 de setembro" "sete de setembro"
   "esportivo" "esportivo bento goncalves"
   "delfin equ" "delfin"
   "libertad par" "libertad"
   "river plate uru" "river plate-uru"
   "olimpia par" "olimpia"
   "barcelona equ" "barcelona-equ"})

(def ^:private homonyms
  "Base names shared by clubs from several states, with the state of the
  club a bare name refers to (nil when there is no obvious default). The
  other clubs keep their state in the key, e.g. \"flamengo-pi\"."
  {"flamengo" "rj" "fluminense" "rj" "botafogo" "rj" "santos" "sp"
   "internacional" "rs" "juventude" "rs" "nautico" "pe" "portuguesa" "sp"
   "santa cruz" "pe" "vitoria" "ba" "guarani" "sp" "fortaleza" "ce"
   "operario" "pr" "ypiranga" "rs" "comercial" "ms" "sao jose" "rs"
   "bragantino" "sp" "independente" "pa" "river" "pi"
   "america" nil "atletico" nil "rio branco" nil "sao raimundo" nil
   "sao francisco" nil "river plate" nil "real" nil "nacional" nil})

(def ^:private club-prefixes #{"ec" "fc" "ad" "ae" "ca" "se" "sc" "ge" "ce"})
(def ^:private club-suffixes #{"ec" "fc" "sc"})

(defn- strip-club-tokens [tokens]
  (let [tokens (if (and (> (count tokens) 1) (club-prefixes (first tokens)))
                 (rest tokens)
                 tokens)
        tokens (cond
                 (and (> (count tokens) 2)
                      (= ["futebol" "clube"] (take-last 2 tokens)))
                 (drop-last 2 tokens)
                 (and (> (count tokens) 1) (club-suffixes (last tokens)))
                 (butlast tokens)
                 :else tokens)]
    (vec tokens)))

(defn- split-state
  "\"palmeiras sp\" -> [\"palmeiras\" \"sp\"]; no state -> [s nil]."
  [s]
  (let [tokens (str/split s #" ")]
    (if (and (> (count tokens) 1) (states (peek tokens)))
      [(str/join " " (pop tokens)) (peek tokens)]
      [s nil])))

(defn team-key
  "Canonical key for any spelling of a team name."
  [raw]
  (let [s (-> (fold raw)
              (str/replace "." " ")
              (str/replace #"\s*\(([a-z]{2,3})\)\s*$" " $1")
              (str/replace #"\s*-\s*([a-z]{2,3})$" " $1")
              (str/replace #"\s+" " ")
              str/trim)]
    (or (aliases s)
        (let [[base uf] (split-state s)
              base (str/join " " (strip-club-tokens (str/split base #" ")))
              base (if (and (nil? uf) (contains? aliases base)) (aliases base) base)]
          (cond
            (and uf (aliases (str base " " uf))) (aliases (str base " " uf))
            (contains? homonyms base) (if (or (nil? uf) (= uf (homonyms base)))
                                        base
                                        (str base "-" uf))
            :else (get aliases base base))))))

(def ^:private display-names
  {"atletico-mg" "Atlético-MG" "athletico-pr" "Athletico-PR"
   "atletico-go" "Atlético-GO" "america-mg" "América-MG"
   "america-rn" "América-RN" "vasco" "Vasco da Gama" "sport" "Sport Recife"
   "bragantino" "Red Bull Bragantino" "sao paulo" "São Paulo"
   "gremio" "Grêmio" "goias" "Goiás" "ceara" "Ceará" "cuiaba" "Cuiabá"
   "avai" "Avaí" "vitoria" "Vitória" "nautico" "Náutico" "parana" "Paraná"
   "criciuma" "Criciúma" "csa" "CSA" "crb" "CRB" "abc" "ABC" "asa" "ASA"
   "botafogo" "Botafogo" "boavista" "Boavista" "4 de julho" "4 de Julho" "operario" "Operário-PR"})

(defn display-name
  "Human readable name for a team, derived from one of its raw spellings."
  [raw key]
  (or (display-names key)
      (let [base (-> (str raw)
                     str/trim
                     (str/replace #"\s*\(([A-Za-z]{2,3})\)\s*$" "")
                     (str/replace #"\s*-\s*[A-Z]{2,3}$" ""))
            [_ stem uf] (re-matches #"(.*)-([a-z]{2})" key)]
        (if (and uf (contains? homonyms stem))
          (str (str/replace base (re-pattern (str "(?i)\\s+" uf "$")) "")
               "-" (str/upper-case uf))
          base))))

;; ---------------------------------------------------------------------------
;; Competitions

(def serie-a "Brasileirão Série A")
(def serie-b "Brasileirão Série B")
(def serie-c "Brasileirão Série C")
(def copa-do-brasil "Copa do Brasil")
(def libertadores "Copa Libertadores")

(def competitions [serie-a serie-b serie-c copa-do-brasil libertadores])

(defn competition
  "Resolves a free-text competition name, or nil when it is not recognised."
  [q]
  (let [f (fold q)]
    (cond
      (str/blank? f) nil
      (str/includes? f "libertadores") libertadores
      (re-find #"copa do brasil|brazilian cup|brazil cup" f) copa-do-brasil
      (re-find #"serie b|second division" f) serie-b
      (re-find #"serie c|third division" f) serie-c
      (re-find #"brasileir|serie a$|serie a\b|first division" f) serie-a
      :else nil)))

;; ---------------------------------------------------------------------------
;; Rivalries

(def derbies
  "Traditional rivalries as [team-key team-key derby-name]."
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
   ["athletico-pr" "coritiba" "Atletiba"]
   ["sport" "nautico" "Clássico dos Clássicos"]
   ["sport" "santa cruz" "Clássico das Multidões"]
   ["ceara" "fortaleza" "Clássico-Rei"]
   ["goias" "vila nova" "Derby do Cerrado"]
   ["avai" "figueirense" "Clássico de Florianópolis"]
   ["remo" "paysandu" "Re-Pa"]])

(def ^:private derby-index
  (into {} (map (fn [[a b n]] [#{a b} n])) derbies))

(defn derby-name
  "Name of the derby played between two team keys, or nil."
  [a b]
  (derby-index (hash-set a b)))
