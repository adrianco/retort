(ns soccer.data
  "=============================================================================
   soccer.data — Load & unify the Kaggle CSV datasets into in-memory records
   -----------------------------------------------------------------------------
   PURPOSE
     Read the six provided CSV files from data/kaggle/ and turn them into two
     flat, normalized collections held in memory:

       MATCHES : a vector of unified match maps with the shape
         {:competition  \"Brasileirão Série A\"
          :season       2019
          :round        \"38\"            ; string or nil
          :date         \"2019-12-08\"    ; ISO yyyy-MM-dd
          :stage        \"final\"         ; or nil
          :home         \"Flamengo\"      ; canonical display name
          :away         \"Ceará\"
          :home-key     \"flamengo\"      ; normalized match key
          :away-key     \"ceara\"
          :home-goal    2
          :away-goal    1
          :home-state   \"RJ\"            ; or nil
          :away-state   \"CE\"            ; or nil
          :stats        {...}            ; extended stats or nil
          :source       \"Brasileirao_Matches.csv\"}

       PLAYERS : a vector of FIFA player maps with the shape
         {:id 158023 :name \"L. Messi\" :age 31 :nationality \"Argentina\"
          :overall 94 :potential 94 :club \"FC Barcelona\" :position \"RF\"
          :jersey 10 :height \"5'7\" :weight \"159lbs\" :skills {...}}

   CANONICAL SOURCE SELECTION
     The Brasileirão Série A appears in three files with overlapping years and
     inconsistent club spellings (\"Vasco\" vs \"Vasco da Gama\", \"Athletico\"
     vs \"Atletico\"), which makes row-by-row de-duplication unreliable.
     Instead, for each (competition, season) the loader keeps matches from a
     single highest-priority source:
       Brasileirao/Cup/Libertadores files (0)  >  novo_campeonato (1)  >  BR-Football (2)
     This yields exactly one clean copy of every season (e.g. 380 Série A
     matches in 2019) while still letting BR-Football extend coverage to
     competitions/seasons the dedicated files do not contain (Série B/C, etc.).

   PUBLIC API
     (load-all)         -> {:matches [...] :players [...]} (uncached)
     (db)               -> memoized {:matches ... :players ...}
     (set-data-dir! d)  -> point loader at a different data/kaggle directory
   ============================================================================="
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [soccer.normalize :as n]))

;; ---------------------------------------------------------------------------
;; Locating the data directory
;; ---------------------------------------------------------------------------

(def ^:private default-dirs
  ["data/kaggle"
   "../data/kaggle"
   (str (System/getProperty "user.dir") "/data/kaggle")])

(defonce ^:private data-dir (atom nil))

(defn set-data-dir!
  "Override the directory that holds the Kaggle CSV files."
  [dir]
  (reset! data-dir dir))

(defn- resolve-dir []
  (or @data-dir
      (some #(when (.isDirectory (io/file %)) %) default-dirs)
      (first default-dirs)))

(defn- file [name]
  (io/file (resolve-dir) name))

;; ---------------------------------------------------------------------------
;; CSV reading
;; ---------------------------------------------------------------------------

(defn- read-csv-maps
  "Read a CSV file into a lazy-realized vector of maps keyed by trimmed header."
  [f]
  (with-open [r (io/reader f :encoding "UTF-8")]
    (let [rows (csv/read-csv r)
          header (mapv #(str/trim (or % "")) (first rows))]
      (->> (rest rows)
           (mapv #(zipmap header %))))))

(defn- team-display
  "Full display name, appending a 2-letter state code from a separate column
   when the name does not already carry a suffix (needed for the `novo` file,
   which keeps the UF in its own column)."
  [name state]
  (let [d (n/display-name name)
        st (some-> state str/trim)]
    (if (and d st (re-matches #"[A-Za-z]{2}" st)
             (not (re-find #"-[A-Za-z]{2}$" d)))
      (str d "-" st)
      d)))

(defn- mk-match
  "Build a unified match map from already-parsed fields."
  [{:keys [competition season round date stage home away home-goal away-goal
           home-state away-state stats source]}]
  (let [home-d (team-display home home-state)
        away-d (team-display away away-state)]
    {:competition competition
     :season      season
     :round       (some-> round str str/trim not-empty)
     :date        (n/norm-date date)
     :stage       (some-> stage str/trim not-empty)
     :home        home-d
     :away        away-d
     :home-key    (n/team-key home-d)
     :away-key    (n/team-key away-d)
     :home-goal   home-goal
     :away-goal   away-goal
     :home-state  (some-> home-state str/trim not-empty)
     :away-state  (some-> away-state str/trim not-empty)
     :stats       stats
     :source      source}))

;; ---------------------------------------------------------------------------
;; Per-file loaders
;; ---------------------------------------------------------------------------

(defn- load-brasileirao []
  (for [r (read-csv-maps (file "Brasileirao_Matches.csv"))]
    (mk-match {:competition "Brasileirão Série A"
               :season      (n/->int (get r "season"))
               :round       (get r "round")
               :date        (get r "datetime")
               :home        (get r "home_team")
               :away        (get r "away_team")
               :home-goal   (n/->int (get r "home_goal"))
               :away-goal   (n/->int (get r "away_goal"))
               :home-state  (get r "home_team_state")
               :away-state  (get r "away_team_state")
               :source      "Brasileirao_Matches.csv"})))

(defn- load-cup []
  (for [r (read-csv-maps (file "Brazilian_Cup_Matches.csv"))]
    (mk-match {:competition "Copa do Brasil"
               :season      (n/->int (get r "season"))
               :round       (get r "round")
               :date        (get r "datetime")
               :home        (get r "home_team")
               :away        (get r "away_team")
               :home-goal   (n/->int (get r "home_goal"))
               :away-goal   (n/->int (get r "away_goal"))
               :source      "Brazilian_Cup_Matches.csv"})))

(defn- load-libertadores []
  (for [r (read-csv-maps (file "Libertadores_Matches.csv"))]
    (mk-match {:competition "Copa Libertadores"
               :season      (n/->int (get r "season"))
               :stage       (get r "stage")
               :date        (get r "datetime")
               :home        (get r "home_team")
               :away        (get r "away_team")
               :home-goal   (n/->int (get r "home_goal"))
               :away-goal   (n/->int (get r "away_goal"))
               :source      "Libertadores_Matches.csv"})))

(def ^:private tournament->competition
  {"Serie A"       "Brasileirão Série A"
   "Serie B"       "Brasileirão Série B"
   "Serie C"       "Brasileirão Série C"
   "Copa do Brasil" "Copa do Brasil"})

(defn- load-br-football []
  (for [r (read-csv-maps (file "BR-Football-Dataset.csv"))
        :let [date (n/norm-date (get r "date"))
              tour (str/trim (or (get r "tournament") ""))]]
    (mk-match {:competition (get tournament->competition tour tour)
               :season      (n/year-of date)
               :date        (get r "date")
               :home        (get r "home")
               :away        (get r "away")
               :home-goal   (n/->int (get r "home_goal"))
               :away-goal   (n/->int (get r "away_goal"))
               :stats       {:home-corner (n/->int (get r "home_corner"))
                             :away-corner (n/->int (get r "away_corner"))
                             :home-shots  (n/->int (get r "home_shots"))
                             :away-shots  (n/->int (get r "away_shots"))
                             :home-attack (n/->int (get r "home_attack"))
                             :away-attack (n/->int (get r "away_attack"))
                             :ht-result   (get r "ht_result")
                             :at-result   (get r "at_result")}
               :source      "BR-Football-Dataset.csv"})))

(defn- load-novo []
  (for [r (read-csv-maps (file "novo_campeonato_brasileiro.csv"))]
    (mk-match {:competition "Brasileirão Série A"
               :season      (n/->int (get r "Ano"))
               :round       (get r "Rodada")
               :date        (get r "Data")
               :home        (get r "Equipe_mandante")
               :away        (get r "Equipe_visitante")
               :home-goal   (n/->int (get r "Gols_mandante"))
               :away-goal   (n/->int (get r "Gols_visitante"))
               :home-state  (get r "Mandante_UF")
               :away-state  (get r "Visitante_UF")
               :source      "novo_campeonato_brasileiro.csv"})))

;; ---------------------------------------------------------------------------
;; Players
;; ---------------------------------------------------------------------------

(defn- load-players []
  (for [r (read-csv-maps (file "fifa_data.csv"))
        :let [id (n/->int (get r "ID"))]
        :when id]
    {:id          id
     :name        (str/trim (or (get r "Name") ""))
     :age         (n/->int (get r "Age"))
     :nationality (str/trim (or (get r "Nationality") ""))
     :overall     (n/->int (get r "Overall"))
     :potential   (n/->int (get r "Potential"))
     :club        (str/trim (or (get r "Club") ""))
     :position    (str/trim (or (get r "Position") ""))
     :jersey      (n/->int (get r "Jersey Number"))
     :height      (str/trim (or (get r "Height") ""))
     :weight      (str/trim (or (get r "Weight") ""))
     :foot        (str/trim (or (get r "Preferred Foot") ""))
     :value       (str/trim (or (get r "Value") ""))
     :skills      {:crossing  (n/->int (get r "Crossing"))
                   :finishing (n/->int (get r "Finishing"))
                   :dribbling (n/->int (get r "Dribbling"))
                   :pace      (n/->int (get r "SprintSpeed"))
                   :passing   (n/->int (get r "ShortPassing"))
                   :shooting  (n/->int (get r "ShotPower"))}}))

;; ---------------------------------------------------------------------------
;; Unification + canonical-source selection
;; ---------------------------------------------------------------------------

(defn- valid-match? [m]
  (and (:home-key m) (:away-key m)
       (seq (:home-key m)) (seq (:away-key m))
       (some? (:home-goal m)) (some? (:away-goal m))
       (some? (:season m))))

(def ^:private source-priority
  {"Brasileirao_Matches.csv"        0
   "Brazilian_Cup_Matches.csv"      0
   "Libertadores_Matches.csv"       0
   "novo_campeonato_brasileiro.csv" 1
   "BR-Football-Dataset.csv"        2})

(defn- select-canonical
  "For every (competition, season) keep only rows from the single highest
   priority source present, eliminating cross-file duplication."
  [matches]
  (->> (group-by (juxt :competition :season) matches)
       (mapcat (fn [[_ ms]]
                 (let [best (apply min (map #(get source-priority (:source %) 9) ms))]
                   (filter #(= best (get source-priority (:source %) 9)) ms))))
       ;; collapse any exact duplicate rows within a source
       (reduce (fn [acc m]
                 (assoc acc [(:competition m) (:season m) (:date m)
                             (:home-key m) (:away-key m)
                             (:home-goal m) (:away-goal m)] m))
               {})
       vals
       vec))

(defn load-all
  "Load and unify every dataset. Returns {:matches [...] :players [...]}.
   Uncached — prefer `db` for repeated access."
  []
  (let [matches (->> (concat (load-brasileirao)
                             (load-cup)
                             (load-libertadores)
                             (load-br-football)
                             (load-novo))
                     (filter valid-match?)
                     select-canonical)]
    {:matches matches
     :players (vec (load-players))}))

(def db
  "Memoized accessor for the full in-memory dataset."
  (memoize load-all))
