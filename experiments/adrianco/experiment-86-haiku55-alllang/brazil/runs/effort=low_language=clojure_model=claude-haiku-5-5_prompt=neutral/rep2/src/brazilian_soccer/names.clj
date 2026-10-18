(ns brazilian-soccer.names
  "Normalization of team and competition names across the datasets.
  Team variants such as 'Palmeiras-SP', 'Palmeiras', 'Sociedade Esportiva Palmeiras'
  and 'São Paulo' / 'Sao Paulo' resolve to one comparable key."
  (:require [clojure.string :as str]))

(def ^:private team-aliases
  "Maps normalized spellings to one canonical key. The Atlético clubs are
  separated by state code, see team-key."
  {"sport club corinthians paulista" "corinthians"
   "clube de regatas do flamengo" "flamengo"
   "sociedade esportiva palmeiras" "palmeiras"
   "sao paulo futebol clube" "sao paulo"
   "gremio foot-ball porto alegrense" "gremio"
   "sport club internacional" "internacional"
   "fortaleza fc" "fortaleza"
   "ec bahia" "bahia"
   "vasco" "vasco da gama"
   "vasco da gama rj" "vasco da gama"
   "botafogo rj" "botafogo"
   "atletico mineiro" "atletico-mg"
   "clube atletico mineiro" "atletico-mg"
   "atletico-mg" "atletico-mg"
   "atletico goianiense" "atletico-go"
   "atletico-go" "atletico-go"
   "atletico paranaense" "athletico-pr"
   "athletico paranaense" "athletico-pr"
   "athletico" "athletico-pr"
   "atletico-pr" "athletico-pr"})

(def ^:private competition-aliases
  {"serie a" "brasileirao"
   "brasileirao serie a" "brasileirao"
   "copa libertadores" "libertadores"
   "copa libertadores da america" "libertadores"})

(defn strip-accents [^String s]
  (str/replace (java.text.Normalizer/normalize s java.text.Normalizer$Form/NFD)
               #"\p{M}" ""))

(defn normalize-text
  "Lower-cased, accent-free, whitespace-collapsed text for comparisons."
  [s]
  (-> (strip-accents (str s))
      str/lower-case
      str/trim
      (str/replace #"\s+" " ")))

(defn base-name
  "Display form of a team name: drops parenthetical qualifiers and a trailing
  state code, e.g. 'Palmeiras-SP' -> 'Palmeiras', 'Nacional (URU)' -> 'Nacional'."
  [s]
  (-> (str s)
      (str/replace #"\([^)]*\)" "")
      (str/replace #"\s*-\s*[A-Za-z]{2}\s*$" "")
      str/trim
      (str/replace #"\s+" " ")))

(defn- state-code
  "Trailing state code of a team name, lower-cased, e.g. 'Atletico-MG' -> 'mg'."
  [s]
  (some-> (re-find #"-\s*([A-Za-z]{2})\s*$" (str/replace (str s) #"\([^)]*\)" ""))
          second
          str/lower-case))

(defn team-key
  "Comparable key for a team name, or nil when the name is blank.
  Clubs that share a base name are told apart by state: 'Atlético-MG' and
  'Atlético-GO' give 'atletico-mg' and 'atletico-go'. Other state codes are ignored."
  [s]
  (when-not (str/blank? s)
    (let [b (normalize-text (base-name s))
          st (state-code s)]
      (if (and (= b "atletico") st)
        (get team-aliases (str "atletico-" st) (str "atletico-" st))
        (get team-aliases b b)))))

(defn competition-key
  "Comparable key for a competition name such as 'Brasileirão', 'Serie A' or
  'Copa Libertadores'."
  [s]
  (when-not (str/blank? s)
    (let [b (normalize-text s)]
      (get competition-aliases b b))))
