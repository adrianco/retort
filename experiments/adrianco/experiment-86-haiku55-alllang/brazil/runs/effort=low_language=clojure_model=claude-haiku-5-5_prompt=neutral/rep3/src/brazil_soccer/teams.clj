(ns brazil-soccer.teams
  "Normalizes team and club names and competition labels so that variants such as
  \"Palmeiras-SP\", \"Palmeiras\" and \"Sociedade Esportiva Palmeiras\" resolve to one key."
  (:require [clojure.string :as str]))

(defn fold
  "Lower-cases `s` and strips accents and extra whitespace: \"São Paulo\" -> \"sao paulo\"."
  [s]
  (-> (java.text.Normalizer/normalize (str s) java.text.Normalizer$Form/NFD)
      (str/replace #"\p{InCombiningDiacriticalMarks}+" "")
      str/lower-case
      str/trim
      (str/replace #"\s+" " ")))

(def ^:private brazilian-states
  #{"ac" "al" "ap" "am" "ba" "ce" "df" "es" "go" "ma" "mt" "ms" "mg" "pa" "pb"
    "pr" "pe" "pi" "rj" "rn" "rs" "ro" "rr" "sc" "sp" "se" "to"})

(def ^:private foreign-codes
  "Country codes used to disambiguate foreign clubs, e.g. Nacional (URU) vs Nacional (PAR)."
  #{"par" "uru" "equ" "arg" "chi" "col" "per" "bol" "ven"})

(def ^:private ambiguous-bases
  "Club names shared by several Brazilian cities; their state code is part of the key."
  #{"atletico" "america" "guarani"})

(def ^:private aliases
  "Variant spellings (already folded) mapped to the canonical key."
  {"athletico" "athletico pr"
   "athletico paranaense" "athletico pr"
   "atletico paranaense" "athletico pr"
   "atletico pr" "athletico pr"
   "atletico mineiro" "atletico mg"
   "atletico goianiense" "atletico go"
   "america fc" "america mg"
   "america mineiro" "america mg"
   "sao paulo fc" "sao paulo"
   "ec bahia" "bahia"
   "ec juventude" "juventude"
   "santa cruz fc" "santa cruz"
   "sport club do recife" "sport"
   "sport recife" "sport"
   "sport club corinthians paulista" "corinthians"
   "corinthians paulista" "corinthians"
   "red bull bragantino" "bragantino"
   "fortaleza ec" "fortaleza"
   "fortaleza fc" "fortaleza"
   "ceara sc" "ceara"
   "ceara sporting club" "ceara"
   "avai sc" "avai"
   "parana clube" "parana"
   "vasco" "vasco da gama"
   "inter" "internacional"
   "brasilia fc" "brasilia"
   "goias ec" "goias"})

(def brazilian-clubs
  "Canonical keys of clubs based in Brazil (used for 'Brazilian clubs' queries)."
  #{"flamengo" "palmeiras" "santos" "sao paulo" "corinthians" "gremio" "internacional"
    "atletico mg" "cruzeiro" "fluminense" "vasco da gama" "botafogo" "bahia" "sport"
    "fortaleza" "athletico pr" "ceara" "coritiba" "goias" "chapecoense" "avai" "vitoria"
    "atletico go" "csa" "bragantino" "america mg" "america rn" "ponte preta" "figueirense"
    "parana" "nautico" "santa cruz" "joinville" "criciuma" "juventude" "cuiaba"
    "brasiliense" "portuguesa" "paysandu" "guarani" "ipatinga" "barueri" "santo andre"
    "sao caetano" "gremio prudente" "brasilia"})

(defn- split-code
  "Splits a trailing state or country code off a folded name: \"vasco da gama rj\" ->
  [\"vasco da gama\" \"rj\"]. Other trailing words (\"fc\", \"sc\") are left alone."
  [s]
  (if-let [[_ base code] (re-find #"^(.*?)(?:\s*-\s*|\s*\(\s*|\s+)([a-z]{2,3})\)?$" s)]
    (if (or (brazilian-states code) (foreign-codes code))
      [(str/trim base) code]
      [s nil])
    [s nil]))

(defn team-key
  "Canonical lower-case key for a raw team or club name, independent of accents,
  state suffixes, parenthetical notes and common variant spellings."
  [raw]
  (let [[base code] (split-code (fold raw))
        base (-> base
                 (str/replace #"\(.*?\)" "")
                 (str/replace #"[^a-z0-9 ]" " ")
                 (str/replace #"\s+" " ")
                 str/trim)
        qualified (cond
                    (nil? code) base
                    (foreign-codes code) (str base " " code)
                    (ambiguous-bases base) (str base " " code)
                    :else base)]
    (get aliases qualified (get aliases base qualified))))

(defn brazilian-club?
  "True when the raw club name refers to a club based in Brazil."
  [raw]
  (contains? brazilian-clubs (team-key raw)))

(defn display-name
  "Human-readable form of a team key: \"sao paulo\" -> \"Sao Paulo\"."
  [key]
  (->> (str/split (str key) #" ")
       (map str/capitalize)
       (str/join " ")))

(def competition-names
  {:serie-a "Brasileirão Série A"
   :serie-b "Brasileirão Série B"
   :serie-c "Brasileirão Série C"
   :copa-do-brasil "Copa do Brasil"
   :libertadores "Copa Libertadores"})

(def league-competitions #{:serie-a :serie-b :serie-c})

(defn competition-of
  "Maps a free-form competition label (\"Serie A\", \"Brasileirão\", \"Libertadores\", ...)
  to its keyword, or nil when it is not recognised."
  [raw]
  (let [s (fold raw)]
    (cond
      (str/includes? s "libertadores") :libertadores
      (str/includes? s "copa do brasil") :copa-do-brasil
      (re-find #"serie b" s) :serie-b
      (re-find #"serie c" s) :serie-c
      (re-find #"serie a|brasileirao|brasileiro" s) :serie-a)))
