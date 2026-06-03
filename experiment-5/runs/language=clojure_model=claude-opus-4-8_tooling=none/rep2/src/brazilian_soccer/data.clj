;; =============================================================================
;; brazilian-soccer.data
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   Part of the Brazilian Soccer MCP server (see brazilian-soccer-mcp-guide.md /
;;   TASK.md). This namespace is the data-access layer. It is responsible for:
;;     * Loading the six provided Kaggle CSV datasets from data/kaggle/.
;;     * Normalising the wildly inconsistent source schemas into a single,
;;       uniform "match" map and a uniform "player" map.
;;     * Normalising team names so that "Palmeiras-SP", "Palmeiras" and
;;       "São Paulo FC" can all be matched consistently (accent folding,
;;       state-/country-suffix stripping, parenthetical removal).
;;     * Parsing the several date formats present in the data into ISO strings.
;;
;;   Downstream:
;;     * brazilian-soccer.queries  — pure query/aggregation functions.
;;     * brazilian-soccer.mcp      — JSON-RPC/MCP stdio server exposing tools.
;;
;;   Data is loaded once and cached in the `matches` / `players` delays so that
;;   repeated tool calls are fast (well under the 2s/5s targets in the spec).
;; =============================================================================
(ns brazilian-soccer.data
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]))

;; -----------------------------------------------------------------------------
;; Configuration
;; -----------------------------------------------------------------------------

(def ^:dynamic *data-dir*
  "Directory containing the Kaggle CSV files. Overridable via the
   BR_SOCCER_DATA_DIR environment variable (used by tests / deployments)."
  (or (System/getenv "BR_SOCCER_DATA_DIR") "data/kaggle"))

;; -----------------------------------------------------------------------------
;; Small parsing helpers
;; -----------------------------------------------------------------------------

(def ^:private bom (char 0xFEFF))

(defn- strip-bom [s]
  (if (and s (pos? (count s)) (= bom (.charAt ^String s 0)))
    (subs s 1)
    s))

(defn to-int
  "Parse a value to a long, tolerating decimals like \"1.0\" and blanks."
  [v]
  (when v
    (let [s (str/trim (str v))]
      (when (seq s)
        (try
          (long (Double/parseDouble s))
          (catch Exception _ nil))))))

(defn parse-date
  "Normalise the assorted source date formats into an ISO \"YYYY-MM-DD\" string.
   Handles:
     * \"2012-05-19 18:30:00\" / \"2023-09-24\"  (ISO, optional time)
     * \"29/03/2003\"                            (Brazilian DD/MM/YYYY)
   Returns the ISO date string (sortable lexicographically) or nil."
  [s]
  (when s
    (let [s (str/trim (str s))]
      (cond
        (str/blank? s) nil
        (re-find #"^\d{4}-\d{2}-\d{2}" s) (subs s 0 10)
        (re-find #"^\d{1,2}/\d{1,2}/\d{4}" s)
        (let [datepart (first (str/split s #"\s+"))
              [d m y] (str/split datepart #"/")]
          (format "%04d-%02d-%02d" (to-int y) (to-int m) (to-int d)))
        :else s))))

;; -----------------------------------------------------------------------------
;; Team-name normalisation
;; -----------------------------------------------------------------------------

(defn strip-accents
  "Fold diacritics: \"São Paulo\" -> \"Sao Paulo\", \"Grêmio\" -> \"Gremio\"."
  [s]
  (-> (Normalizer/normalize (str s) Normalizer$Form/NFD)
      (str/replace #"\p{InCombiningDiacriticalMarks}+" "")))

(defn clean-name
  "Produce a human-readable team display name by removing parenthetical notes
   (country codes / historical names) and normalising the state/country suffix
   spacing. The suffix is KEPT, because it disambiguates same-named clubs in
   different states (Atlético-MG vs Atlético-PR vs Atlético-GO):
     \"Palmeiras-SP\"            -> \"Palmeiras-SP\"
     \"América - MG\"            -> \"América-MG\"
     \"Nacional (URU)\"          -> \"Nacional\"
     \"Boavista ... (x) - RJ\"   -> \"Boavista ...-RJ\""
  [s]
  (when s
    (-> (str s)
        (str/replace #"\([^)]*\)" " ")            ; drop (URU), (antigo ...) etc.
        (str/replace #"\s*-\s*([A-Z]{2,3})\s*$" "-$1") ; tidy trailing -SP / - MG
        (str/replace #"\s+" " ")
        str/trim)))

(defn team-key
  "Canonical lookup key for a team: cleaned, accent-folded, lower-cased,
   non-alphanumerics collapsed to single spaces. Retains the state suffix so
   distinct same-named clubs get distinct keys, while fuzzy matching (see
   `team-matches?`) still lets the bare name match the suffixed variant."
  [s]
  (-> (clean-name s)
      strip-accents
      str/lower-case
      (str/replace #"[^a-z0-9]+" " ")
      str/trim))

(defn base-key
  "Like `team-key` but with the trailing state/country suffix removed, so that
   \"Flamengo-RJ\" and \"Flamengo\" share the base key \"flamengo\". Used to
   reconcile the same fixture appearing in two datasets that differ only in
   whether they append the state. NOT used for distinctness (that needs the
   suffix — see `team-key`)."
  [s]
  (-> (clean-name s)
      (str/replace #"-[A-Z]{2,3}$" "")
      strip-accents
      str/lower-case
      (str/replace #"[^a-z0-9]+" " ")
      str/trim))

(defn team-matches?
  "True when query string `q` refers to team `team-name`. Matching is fuzzy:
   the normalised keys must share a containment relationship, e.g. query
   \"sao paulo fc\" matches team \"São Paulo\", and \"Flamengo\" matches
   \"Flamengo-RJ\"."
  [q team-name]
  (let [qk (team-key q)
        tk (team-key team-name)]
    (and (seq qk) (seq tk)
         (or (= qk tk)
             (str/includes? tk qk)
             (str/includes? qk tk)))))

;; -----------------------------------------------------------------------------
;; CSV reading
;; -----------------------------------------------------------------------------

(defn- read-csv-maps
  "Read a CSV file (relative to *data-dir*) into a seq of maps keyed by the
   header row (BOM-stripped, trimmed). Returns [] when the file is absent."
  [filename]
  (let [f (io/file *data-dir* filename)]
    (if-not (.exists f)
      []
      (with-open [r (io/reader f :encoding "UTF-8")]
        (let [rows (csv/read-csv r)
              header (mapv (comp str/trim strip-bom) (first rows))]
          (doall
           (for [row (rest rows)
                 :when (seq row)]
             (zipmap header row))))))))

;; -----------------------------------------------------------------------------
;; Match loaders — each produces the uniform match map:
;;   {:competition :season :date :round :stage
;;    :home :away :home-raw :away-raw :home-key :away-key
;;    :home-goal :away-goal :source}
;; -----------------------------------------------------------------------------

(defn- ->match
  [{:keys [competition season date round stage home away home-goal away-goal source]}]
  {:competition competition
   :season      (to-int season)
   :date        (parse-date date)
   :round       (when round (str/trim (str round)))
   :stage       stage
   :home        (clean-name home)
   :away        (clean-name away)
   :home-raw    home
   :away-raw    away
   :home-key    (team-key home)
   :away-key    (team-key away)
   :home-goal   (to-int home-goal)
   :away-goal   (to-int away-goal)
   :source      source})

(defn- load-brasileirao []
  (for [m (read-csv-maps "Brasileirao_Matches.csv")]
    (->match {:competition "Brasileirão Série A"
              :season   (get m "season")
              :date     (get m "datetime")
              :round    (get m "round")
              :home     (get m "home_team")
              :away     (get m "away_team")
              :home-goal (get m "home_goal")
              :away-goal (get m "away_goal")
              :source   "Brasileirao_Matches.csv"})))

(defn- load-cup []
  (for [m (read-csv-maps "Brazilian_Cup_Matches.csv")]
    (->match {:competition "Copa do Brasil"
              :season   (get m "season")
              :date     (get m "datetime")
              :round    (get m "round")
              :home     (get m "home_team")
              :away     (get m "away_team")
              :home-goal (get m "home_goal")
              :away-goal (get m "away_goal")
              :source   "Brazilian_Cup_Matches.csv"})))

(defn- load-libertadores []
  (for [m (read-csv-maps "Libertadores_Matches.csv")]
    (->match {:competition "Copa Libertadores"
              :season   (get m "season")
              :date     (get m "datetime")
              :stage    (get m "stage")
              :home     (get m "home_team")
              :away     (get m "away_team")
              :home-goal (get m "home_goal")
              :away-goal (get m "away_goal")
              :source   "Libertadores_Matches.csv"})))

(defn- load-br-football []
  (for [m (read-csv-maps "BR-Football-Dataset.csv")]
    (->match {:competition (let [t (str/trim (str (get m "tournament")))]
                             (if (seq t) t "Unknown"))
              :date     (get m "date")
              :home     (get m "home")
              :away     (get m "away")
              :home-goal (get m "home_goal")
              :away-goal (get m "away_goal")
              :source   "BR-Football-Dataset.csv"})))

(defn- load-novo []
  (for [m (read-csv-maps "novo_campeonato_brasileiro.csv")]
    (->match {:competition "Brasileirão Série A"
              :season   (get m "Ano")
              :date     (get m "Data")
              :round    (get m "Rodada")
              :home     (get m "Equipe_mandante")
              :away     (get m "Equipe_visitante")
              :home-goal (get m "Gols_mandante")
              :away-goal (get m "Gols_visitante")
              :source   "novo_campeonato_brasileiro.csv"})))

(defn- valid-match? [m]
  (and (seq (:home m)) (seq (:away m))
       (some? (:home-goal m)) (some? (:away-goal m))))

(defn- load-all-matches []
  (vec (filter valid-match?
               (concat (load-brasileirao)
                       (load-cup)
                       (load-libertadores)
                       (load-br-football)
                       (load-novo)))))

;; -----------------------------------------------------------------------------
;; Player loader (FIFA dataset)
;; -----------------------------------------------------------------------------

(defn- ->player [m]
  {:id        (to-int (get m "ID"))
   :name      (str/trim (str (get m "Name")))
   :age       (to-int (get m "Age"))
   :nationality (str/trim (str (get m "Nationality")))
   :overall   (to-int (get m "Overall"))
   :potential (to-int (get m "Potential"))
   :club      (str/trim (str (get m "Club")))
   :position  (str/trim (str (get m "Position")))
   :jersey    (to-int (get m "Jersey Number"))
   :height    (str/trim (str (get m "Height")))
   :weight    (str/trim (str (get m "Weight")))
   :foot      (str/trim (str (get m "Preferred Foot")))
   :value     (str/trim (str (get m "Value")))})

(defn- load-all-players []
  (vec (for [m (read-csv-maps "fifa_data.csv")
             :let [p (->player m)]
             :when (seq (:name p))]
         p)))

;; -----------------------------------------------------------------------------
;; Public, cached accessors. Caching is keyed on *data-dir* so that pointing
;; the var at a fixture directory (in tests) transparently loads fresh data
;; while production calls stay memoised.
;; -----------------------------------------------------------------------------

(def ^:private match-cache  (atom {}))
(def ^:private player-cache (atom {}))

(defn all-matches
  "All matches (uniform maps) for the current *data-dir*, cached per directory."
  []
  (if-let [v (get @match-cache *data-dir*)]
    v
    (let [v (load-all-matches)]
      (swap! match-cache assoc *data-dir* v)
      v)))

(defn all-players
  "All FIFA players (uniform maps) for the current *data-dir*, cached per dir."
  []
  (if-let [v (get @player-cache *data-dir*)]
    v
    (let [v (load-all-players)]
      (swap! player-cache assoc *data-dir* v)
      v)))

(defn reset-cache!
  "Clear the per-directory caches. Intended for tests."
  []
  (reset! match-cache {})
  (reset! player-cache {}))
