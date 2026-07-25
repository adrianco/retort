(ns brazilian-soccer.names
  "Team-name normalisation for the Brazilian soccer knowledge graph.

  CONTEXT
  -------
  The six Kaggle CSV files name the same club in many different ways:

      Brasileirao_Matches.csv        \"Atletico-MG\"        \"Sao Paulo-SP\"
      novo_campeonato_brasileiro.csv \"Atlético-MG\"        \"São Paulo\"
      Brazilian_Cup_Matches.csv      \"Atlético Mineiro - MG\"
      Libertadores_Matches.csv       \"Atlético-MG\"        \"São Paulo\"
      BR-Football-Dataset.csv        \"Atletico Mineiro\"   \"Sao Paulo\"
      fifa_data.csv (Club column)    \"Atlético Mineiro\"

  Every name is reduced to a canonical id of the form \"base|region\", e.g.
  \"atletico|mg\", \"sao paulo|sp\", \"nacional|uru\".  The pipeline is:

      raw  -> clean (strip accents / case / punctuation)
           -> whole-string alias lookup   (hand curated, exact matches)
           -> region suffix extraction    (\"-MG\", \" - MG\", \" (URU)\")
           -> club-word removal           (\"EC\", \"FC\", \"Esporte Clube\", ...)
           -> base alias lookup           (\"athletico paranaense\" -> atletico/pr)
           -> region defaulting           (curated, then data-driven inference)

  Region defaulting matters because bases like \"atletico\", \"america\",
  \"botafogo\" and \"santos\" are shared by several clubs; the region keeps them
  apart while still letting \"Flamengo\" (Libertadores) merge with
  \"Flamengo-RJ\" (Brasileirão).

  This namespace is pure: `parse-team-name` does steps 1-5 and callers supply
  the corpus-wide region index (built in `brazilian-soccer.data`) for step 6."
  (:require [clojure.string :as str])
  (:import (java.text Normalizer Normalizer$Form)))

;; ---------------------------------------------------------------------------
;; Region codes
;; ---------------------------------------------------------------------------

(def brazilian-states
  "Two letter abbreviations of the 26 Brazilian states plus the Federal District."
  #{"ac" "al" "ap" "am" "ba" "ce" "df" "es" "go" "ma" "mt" "ms" "mg" "pa" "pb"
    "pr" "pe" "pi" "rj" "rn" "rs" "ro" "rr" "sc" "sp" "se" "to"})

(def foreign-codes
  "Country codes used by the Libertadores file for non-Brazilian clubs."
  #{"arg" "uru" "par" "equ" "ecu" "per" "ven" "col" "chi" "bol" "mex" "pan"})

(defn region-code? [s]
  (let [s (str/lower-case (str s))]
    (boolean (or (brazilian-states s) (foreign-codes s)))))

;; ---------------------------------------------------------------------------
;; Cleaning
;; ---------------------------------------------------------------------------

(defn strip-accents
  "\"Grêmio\" -> \"Gremio\", \"São Paulo\" -> \"Sao Paulo\", \"Avaí\" -> \"Avai\"."
  [s]
  (-> (Normalizer/normalize (str s) Normalizer$Form/NFD)
      (str/replace #"\p{M}" "")))

(defn clean
  "Lower-case, accent-free, punctuation-free form with hyphens tightened so that
  \"América - MG\" and \"America-MG\" both become \"america-mg\"."
  [s]
  (-> (strip-accents s)
      str/lower-case
      (str/replace #"[.'`´\"()\[\],/&]" " ")
      (str/replace #"\s*-\s*" "-")
      (str/replace #"\s+" " ")
      str/trim))

;; ---------------------------------------------------------------------------
;; Curated aliases
;; ---------------------------------------------------------------------------

(def whole-name-aliases
  "Cleaned *whole* raw strings that generic rules cannot untangle.
  Values are [base region]."
  {"sport club do recife"                                            ["sport" "pe"]
   "sport recife"                                                    ["sport" "pe"]
   "nautico capibaribe"                                              ["nautico" "pe"]
   "ceara sporting club"                                             ["ceara" "ce"]
   "america fc minas gerais"                                         ["america" "mg"]
   "america fc natal"                                                ["america" "rn"]
   "america de natal-rn"                                             ["america" "rn"]
   "clube do remo"                                                   ["remo" "pa"]
   "moto club de sao luis"                                           ["moto" "ma"]
   "moto clube"                                                      ["moto" "ma"]
   "moto club-ma"                                                    ["moto" "ma"]
   "boavista sport club antigo esporte clube barreira-rj"            ["boavista" "rj"]
   "boavista sc saquarema"                                           ["boavista" "rj"]
   "portuguesa desportos"                                            ["portuguesa" "sp"]
   "gremio novorizontino"                                            ["novorizontino" "sp"]
   "red bull bragantino"                                             ["bragantino" "sp"]
   "red bull bragantino-sp"                                          ["bragantino" "sp"]
   "operario ferroviario esporte c-pr"                               ["operario" "pr"]
   "operario ferroviario"                                            ["operario" "pr"]
   "desportiva ferroviaria-es"                                       ["desportiva" "es"]
   "flamengo do piaui-pi"                                            ["flamengo" "pi"]
   "aquidauanense futebol clube-ms"                                  ["aquidauanense" "ms"]
   "parnahyba s c-pi"                                                ["parnahyba" "pi"]
   "gremio esportivo sapucaiense-rs"                                 ["sapucaiense" "rs"]
   "arapongas esporte clube-pr"                                      ["arapongas" "pr"]
   "santa quiteria futebol clube-ma"                                 ["santa quiteria" "ma"]
   "sao domingos futebol clube-se"                                   ["sao domingos" "se"]
   "paulista futebol clube-sp"                                       ["paulista" "sp"]
   "real noroeste capixaba-es"                                       ["real noroeste" "es"]
   "rio branco-vn-es"                                                ["rio branco" "es"]
   "uniao de rondonopolis-mt"                                        ["uniao" "mt"]
   "uniao rondonopolis"                                              ["uniao" "mt"]
   "independente de tucurui-pa"                                      ["independente tucurui" "pa"]
   "guarani de juazeiro-ce"                                          ["guarani juazeiro" "ce"]
   "guarani de juazeiro"                                             ["guarani juazeiro" "ce"]
   "guarany de sobral-ce"                                            ["guarany sobral" "ce"]
   "guarany de sobral"                                               ["guarany sobral" "ce"]
   "fluminense de feira-ba"                                          ["fluminense feira" "ba"]
   "fluminense de feira"                                             ["fluminense feira" "ba"]
   "bahia de feira"                                                  ["bahia feira" "ba"]
   "bahia de feira-ba"                                               ["bahia feira" "ba"]
   "sao jose-poa"                                                    ["sao jose" "rs"]
   "esportivo bento goncalves"                                       ["esportivo" "rs"]
   "ser caxias-rs"                                                   ["caxias" "rs"]
   "metropolitano maringa pr"                                        ["maringa" "pr"]
   "ind santa fe"                                                    ["independiente santa fe" "col"]
   "independiente del valle"                                         ["independiente del valle" "ecu"]
   "independiente delvalle"                                          ["independiente del valle" "ecu"]
   "junior de barranquilla"                                          ["junior" "col"]
   "universidad catolica"                                            ["universidad catolica" "chi"]
   "atletico nacional"                                               ["atletico nacional" "col"]
   "atletico tucuman"                                                ["atletico tucuman" "arg"]
   "nautico-rr"                                                      ["nautico" "rr"]})

(def base-aliases
  "Cleaned *base* names (after region extraction and club-word removal) that map
  onto another club identity.  Values are [base region-or-nil]."
  {"athletico"            ["atletico" "pr"]
   "athletico paranaense" ["atletico" "pr"]
   "atletico paranaense"  ["atletico" "pr"]
   "atletico mineiro"     ["atletico" "mg"]
   "atletico goianiense"  ["atletico" "go"]
   "atletico acreano"     ["atletico" "ac"]
   "atletico cearense"    ["atletico cearense" "ce"]
   "atletico alagoinhas"  ["atletico" "ba"]
   "vasco"                ["vasco da gama" "rj"]
   "vasco da gama"        ["vasco da gama" "rj"]
   "gremio prudente"      ["gremio prudente" "sp"]
   "gremio barueri"       ["barueri" "sp"]
   "barueri"              ["barueri" "sp"]
   "duque de caxias"      ["duque de caxias" "rj"]
   "inter de limeira"     ["inter de limeira" "sp"]
   "xv de piracicaba"     ["xv piracicaba" "sp"]
   "xv piracicaba"        ["xv piracicaba" "sp"]
   "sampaio correa"       ["sampaio correa" "ma"]
   "brasil de pelotas"    ["brasil" "rs"]
   "abc"                  ["abc" "rn"]
   "a b c"                ["abc" "rn"]
   "asa"                  ["asa" "al"]
   "a s a"                ["asa" "al"]
   "crb"                  ["crb" "al"]
   "c r b"                ["crb" "al"]
   "csa"                  ["csa" "al"]
   "c s a"                ["csa" "al"]
   "cs alagoano"          ["csa" "al"]
   "crac"                 ["crac" "go"]
   "c r a c"              ["crac" "go"]
   "urt"                  ["urt" "mg"]
   "pstc"                 ["pstc" "pr"]
   "nacional par"         ["nacional" "par"]
   "olimpia"              ["olimpia" "par"]
   "libertad"             ["libertad" "par"]
   "cerro porteno"        ["cerro porteno" "par"]
   "penarol"              ["penarol" "uru"]
   "nacional uru"         ["nacional" "uru"]
   "danubio"              ["danubio" "uru"]
   "defensor sporting"    ["defensor sporting" "uru"]
   "montevideo wanderers" ["montevideo wanderers" "uru"]
   "rentistas"            ["rentistas" "uru"]
   "universitario"        ["universitario" "per"]
   "sporting cristal"     ["sporting cristal" "per"]
   "alianza lima"         ["alianza lima" "per"]
   "delfin"               ["delfin" "equ"]
   "emelec"               ["emelec" "equ"]
   "ldu"                  ["ldu" "equ"]
   "barcelona"            ["barcelona" "equ"]
   "colo-colo"            ["colo colo" "chi"]
   "colo colo"            ["colo colo" "chi"]
   "boca juniors"         ["boca juniors" "arg"]
   "river plate"          ["river plate" "arg"]
   "san lorenzo"          ["san lorenzo" "arg"]
   "racing club"          ["racing club" "arg"]
   "velez sarsfield"      ["velez sarsfield" "arg"]
   "bolivar"              ["bolivar" "bol"]
   "the strongest"        ["the strongest" "bol"]
   "millonarios"          ["millonarios" "col"]
   "deportivo cali"       ["deportivo cali" "col"]
   "america de cali"      ["america de cali" "col"]
   "deportes tolima"      ["tolima" "col"]
   "tolima"               ["tolima" "col"]})

(def default-regions
  "Region assumed when a club is written without one.  Only clubs whose bare
  name is unambiguous *in practice* are listed here; everything else is
  inferred from the corpus (see `brazilian-soccer.data/build-team-index`)."
  {"flamengo"      "rj" "fluminense"  "rj" "botafogo"    "rj" "vasco da gama" "rj"
   "volta redonda" "rj" "bangu"       "rj" "madureira"   "rj" "resende"       "rj"
   "boavista"      "rj" "cabofriense" "rj" "nova iguacu" "rj" "macae"         "rj"
   "friburguense"  "rj" "americano"   "rj"
   "corinthians"   "sp" "palmeiras"   "sp" "santos"      "sp" "sao paulo"     "sp"
   "ponte preta"   "sp" "portuguesa"  "sp" "guarani"     "sp" "santo andre"   "sp"
   "sao caetano"   "sp" "ituano"      "sp" "oeste"       "sp" "mirassol"      "sp"
   "novorizontino" "sp" "sao bento"   "sp" "sao bernardo" "sp" "marilia"      "sp"
   "bragantino"    "sp"
   "linense"       "sp" "capivariano" "sp" "audax"       "sp" "ferroviaria"   "sp"
   "guaratingueta" "sp" "mogi mirim"  "sp" "votuporanguense" "sp" "noroeste"  "sp"
   "gremio"        "rs" "internacional" "rs" "juventude" "rs" "caxias"        "rs"
   "novo hamburgo" "rs" "lajeadense"  "rs" "avenida"     "rs" "veranopolis"   "rs"
   "aimore"        "rs" "sao luiz"    "rs" "esportivo"   "rs"
   "cruzeiro"      "mg" "tombense"    "mg" "tupi"        "mg" "uberlandia"    "mg"
   "caldense"      "mg" "villa nova"  "mg" "boa"         "mg" "athletic"      "mg"
   "democrata"     "mg" "pouso alegre" "mg" "ipatinga"   "mg" "betim"         "mg"
   "coritiba"      "pr" "parana"      "pr" "londrina"    "pr" "cianorte"      "pr"
   "toledo"        "pr" "maringa"     "pr" "cascavel"    "pr" "azuriz"        "pr"
   "chapecoense"   "sc" "avai"        "sc" "figueirense" "sc" "criciuma"      "sc"
   "joinville"     "sc" "brusque"     "sc" "tubarao"     "sc" "marcilio dias" "sc"
   "camboriu"      "sc"
   "bahia"         "ba" "vitoria"     "ba" "jacuipense"  "ba" "juazeirense"   "ba"
   "sport"         "pe" "nautico"     "pe" "santa cruz"  "pe" "salgueiro"     "pe"
   "retro"         "pe" "afogados"    "pe"
   "ceara"         "ce" "fortaleza"   "ce" "ferroviario" "ce" "floresta"      "ce"
   "icasa"         "ce" "caucaia"     "ce" "horizonte"   "ce" "iguatu"        "ce"
   "barbalha"      "ce" "uniclinic"   "ce" "guarany"     "ce"
   "goias"         "go" "vila nova"   "go" "aparecidense" "go" "anapolis"     "go"
   "anapolina"     "go" "goianesia"   "go" "jaragua"     "go"
   "cuiaba"        "mt" "luverdense"  "mt" "mixto"       "mt" "sinop"         "mt"
   "nova mutum"    "mt" "dom bosco"   "mt"
   "paysandu"      "pa" "remo"        "pa" "castanhal"   "pa" "tuna luso"     "pa"
   "aguia"         "pa" "paragominas" "pa" "parauapebas" "pa"
   "manaus"        "am" "fast clube"  "am" "princesa do solimoes" "am"
   "brasiliense"   "df" "gama"        "df" "ceilandia"   "df" "sobradinho"    "df"
   "luziania"      "df" "real brasilia" "df" "brasilia"   "df"
   "treze"         "pb" "campinense"  "pb" "sousa"       "pb" "souza"         "pb"
   "auto esporte"  "pb"
   "sampaio correa" "ma" "imperatriz" "ma" "moto"        "ma" "cordino"       "ma"
   "tuntum"        "ma" "maranhao"    "ma"
   "potiguar"      "rn" "globo"       "rn" "alecrim"     "rn"
   "sergipe"       "se" "confianca"   "se" "itabaiana"   "se" "lagarto"       "se"
   "estanciano"    "se" "frei paulistano" "se" "amadense" "se"
   "altos"         "pi" "parnahyba"   "pi" "picos"       "pi" "river"         "pi"
   "piaui"         "pi" "4 de julho"  "pi" "iv de julho" "pi"
   "galvez"        "ac" "rio branco"  "ac" "humaita"     "ac" "placido de castro" "ac"
   "genus"         "ro" "porto velho" "ro" "vilhena"     "ro" "vilhenense"    "ro"
   "ji-parana"     "ro" "rondoniense" "ro" "real ariquemes" "ro"
   "trem"          "ap" "oratorio"    "ap" "peixe da amazonia" "ap"
   "gurupi"        "to" "palmas"      "to" "interporto"  "to" "tocantinopolis" "to"
   "murici"        "al" "coruripe"    "al" "santa rita"  "al" "falcon"        "se"
   "comercial"     "ms" "corumbaense" "ms" "cene"        "ms" "naviraiense"   "ms"
   "aguia negra"   "ms" "ivinhema"    "ms" "novoperario" "ms" "costa rica"    "ms"
   "7 de setembro" "ms" "sete de setembro" "ms" "aquidauanense" "ms"
   "serra"         "es" "aracruz"     "es" "estrela do norte" "es" "desportiva" "es"
   "real noroeste" "es" "sao mateus"  "es" "nova venecia" "es"})

(def club-tokens
  "Standalone abbreviations for \"clube\" / \"futebol\" / \"esporte\" that carry no
  identity.  Region extraction runs first so state codes are never eaten here."
  #{"ec" "fc" "sc" "ac" "ad" "se" "ca" "ge" "cs" "cd" "cr" "sd" "gd" "ae" "aa"
    "cf" "fr" "ltda" "efc" "esporte" "esportivo" "futebol" "clube"})

(def ^:private club-phrases
  [#"\besporte clube\b" #"\bfutebol clube\b" #"\bsport club\b"
   #"\bsporting club\b" #"\bclube de futebol\b" #"\bgremio esportivo\b"
   #"\bassociacao atletica\b" #"\bassociacao desportiva\b" #"\besporte c\b"
   #"\bfutebol c\b" #"\bf c\b" #"\be c\b" #"\bs c\b"])

(defn- extract-region
  "Split a trailing state / country code off a cleaned name."
  [s]
  (if-let [[_ base code] (re-find #"^(.*[^-\s])[-\s]([a-z]{2,3})$" s)]
    (if (region-code? code) [base code] [s nil])
    [s nil]))

(defn- drop-club-words [s]
  (let [without-phrases (reduce (fn [acc re] (str/replace acc re " ")) s club-phrases)
        tokens          (remove club-tokens (str/split (str/trim without-phrases) #"\s+"))
        base            (str/trim (str/join " " tokens))]
    (if (str/blank? base) s base)))

(defn parse-team-name
  "Return {:base \"atletico\" :region \"mg\"} for a raw team string.
  `:region` is nil when the raw name carries no state / country hint and no
  curated default applies; callers may fill it in from corpus statistics."
  [raw]
  (let [cleaned (clean raw)]
    (if-let [[base region] (whole-name-aliases cleaned)]
      {:base base :region region :cleaned cleaned}
      (let [[stripped region] (extract-region cleaned)
            base              (drop-club-words stripped)
            ;; an explicit suffix in the raw name always wins over the region
            ;; carried by an alias: "River Plate" is Argentine, but
            ;; "River Plate-URU" is not
            [base region]     (if-let [[b r] (base-aliases base)]
                                [b (or region r)]
                                [base region])
            region            (or region (default-regions base))]
        {:base base :region region :cleaned cleaned}))))

(defn team-id
  "Canonical id, e.g. \"atletico|mg\" or \"tigres\" (no known region)."
  [base region]
  (if (str/blank? (str region)) base (str base "|" region)))

(defn id-base   [id] (first (str/split id #"\|")))
(defn id-region [id] (second (str/split id #"\|")))

(defn titlecase
  "Fallback display name: \"vila nova\" -> \"Vila Nova\"."
  [s]
  (->> (str/split (str s) #"\s+")
       (map (fn [w] (if (<= (count w) 2)
                      (str/upper-case w)
                      (str (str/upper-case (subs w 0 1)) (subs w 1)))))
       (str/join " ")))

;; ---------------------------------------------------------------------------
;; Curated display names for the clubs users actually ask about
;; ---------------------------------------------------------------------------

(def display-names
  {"flamengo|rj"      "Flamengo"          "fluminense|rj"    "Fluminense"
   "botafogo|rj"      "Botafogo"          "vasco da gama|rj" "Vasco da Gama"
   "corinthians|sp"   "Corinthians"       "palmeiras|sp"     "Palmeiras"
   "santos|sp"        "Santos"            "sao paulo|sp"     "São Paulo"
   "ponte preta|sp"   "Ponte Preta"       "portuguesa|sp"    "Portuguesa"
   "gremio|rs"        "Grêmio"            "internacional|rs" "Internacional"
   "juventude|rs"     "Juventude"         "cruzeiro|mg"      "Cruzeiro"
   "atletico|mg"      "Atlético Mineiro"  "atletico|pr"      "Athletico Paranaense"
   "atletico|go"      "Atlético Goianiense" "america|mg"     "América Mineiro"
   "america|rn"       "América de Natal"  "coritiba|pr"      "Coritiba"
   "parana|pr"        "Paraná"            "chapecoense|sc"   "Chapecoense"
   "avai|sc"          "Avaí"              "figueirense|sc"   "Figueirense"
   "criciuma|sc"      "Criciúma"          "joinville|sc"     "Joinville"
   "bahia|ba"         "Bahia"             "vitoria|ba"       "Vitória"
   "sport|pe"         "Sport Recife"      "nautico|pe"       "Náutico"
   "santa cruz|pe"    "Santa Cruz"        "ceara|ce"         "Ceará"
   "fortaleza|ce"     "Fortaleza"         "goias|go"         "Goiás"
   "cuiaba|mt"        "Cuiabá"            "bragantino|sp"    "Red Bull Bragantino"
   "csa|al"           "CSA"               "crb|al"           "CRB"
   "guarani|sp"       "Guarani"           "santo andre|sp"   "Santo André"
   "sao caetano|sp"   "São Caetano"       "paysandu|pa"      "Paysandu"
   "remo|pa"          "Remo"              "abc|rn"           "ABC"
   "brasiliense|df"   "Brasiliense"       "ipatinga|mg"      "Ipatinga"
   "barueri|sp"       "Grêmio Barueri"    "gremio prudente|sp" "Grêmio Prudente"
   "boca juniors|arg" "Boca Juniors"      "river plate|arg"  "River Plate"
   "nacional|uru"     "Nacional (URU)"    "penarol|uru"      "Peñarol"
   "olimpia|par"      "Olimpia"           "libertad|par"     "Libertad"
   "nacional|par"     "Nacional (PAR)"    "colo colo|chi"    "Colo-Colo"
   "bolivar|bol"      "Bolívar"           "the strongest|bol" "The Strongest"
   "atletico nacional|col" "Atlético Nacional"
   "independiente del valle|ecu" "Independiente del Valle"})
