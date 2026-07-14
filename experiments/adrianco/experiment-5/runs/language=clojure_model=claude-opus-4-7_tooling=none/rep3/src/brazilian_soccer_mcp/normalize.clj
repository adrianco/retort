(ns brazilian-soccer-mcp.normalize
  "Team name normalization. Datasets use different conventions
   (with/without state suffix, full club names, accented characters).
   normalize returns a canonical lowercase ASCII key that preserves
   the state code (so Atlético-MG and Atlético-GO stay distinct), and
   normalize-bare drops it (so 'Flamengo' matches 'Flamengo-RJ' for
   fuzzy lookups).
   matches? uses normalize-bare with substring containment."
  (:require [clojure.string :as str]))

(def ^:private paren-tag-re
  #"\s*\([A-Z]{2,4}\)\s*$")

(def ^:private state-codes
  #{"ac" "al" "ap" "am" "ba" "ce" "df" "es" "go" "ma" "mt" "ms" "mg"
    "pa" "pb" "pr" "pe" "pi" "rj" "rn" "rs" "ro" "rr" "sc" "sp" "se" "to"})

(def ^:private accent-map
  {\á \a \à \a \â \a \ã \a \ä \a
   \é \e \è \e \ê \e \ë \e
   \í \i \ì \i \î \i \ï \i
   \ó \o \ò \o \ô \o \õ \o \ö \o
   \ú \u \ù \u \û \u \ü \u
   \ç \c \ñ \n
   \Á \a \À \a \Â \a \Ã \a \Ä \a
   \É \e \È \e \Ê \e \Ë \e
   \Í \i \Ì \i \Î \i \Ï \i
   \Ó \o \Ò \o \Ô \o \Õ \o \Ö \o
   \Ú \u \Ù \u \Û \u \Ü \u
   \Ç \c \Ñ \n})

(defn- strip-accents [^String s]
  (apply str (map #(get accent-map % %) s)))

(def ^:private base-aliases
  "Applied to the state-stripped lowercase base."
  {"vasco da gama" "vasco"
   "athletico"     "atletico"})

(defn- alias-base [base]
  (get base-aliases base base))

(defn- split-state
  "Return [base state] where state is one of the known UFs or nil."
  [s]
  (if-let [m (re-find #"(.+?)(?:\s*[-–—]\s*|\s+)([A-Za-z]{2})\s*$" s)]
    (let [base  (nth m 1)
          state (str/lower-case (nth m 2))]
      (if (state-codes state)
        [base state]
        [s nil]))
    [s nil]))

(defn- clean-base [s]
  (-> s
      (str/replace paren-tag-re "")
      strip-accents
      str/lower-case
      (str/replace #"[^a-z0-9 ]" " ")
      (str/replace #"\s+" " ")
      str/trim
      alias-base))

(defn normalize
  "Canonical form preserving any state suffix, so distinct clubs that
   share a base name (Atlético MG vs Atlético GO) stay distinct.
   Used for dedupe and standings keys."
  [name]
  (when (and name (not (str/blank? (str name))))
    (let [[base state] (split-state (str name))
          base*        (clean-base base)]
      (if state
        (str base* " " state)
        base*))))

(defn normalize-bare
  "Like normalize, but drops the state code — so 'Flamengo' and
   'Flamengo-RJ' compare equal for fuzzy matching."
  [name]
  (when (and name (not (str/blank? (str name))))
    (let [[base _] (split-state (str name))]
      (clean-base base))))

(defn matches?
  "Loose match between two team names. Equal after bare normalization,
   or one bare form contains the other (handles 'Flamengo' vs 'CR
   Flamengo')."
  [a b]
  (let [na (normalize-bare a)
        nb (normalize-bare b)]
    (cond
      (or (nil? na) (nil? nb))    false
      (= na nb)                   true
      (str/includes? na nb)       true
      (str/includes? nb na)       true
      :else                       false)))
