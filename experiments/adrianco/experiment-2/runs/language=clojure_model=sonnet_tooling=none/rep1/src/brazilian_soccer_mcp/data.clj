(ns brazilian-soccer-mcp.data
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]))

;;; ─── Helpers ────────────────────────────────────────────────────────────────

(defn- remove-accents
  "Strip diacritics from a string (ã->a, ê->e, etc.)."
  [s]
  (when s
    (-> (java.text.Normalizer/normalize s java.text.Normalizer$Form/NFD)
        (str/replace #"\p{M}" ""))))

(defn- normalize-for-search
  "Lower-case and remove accents for fuzzy matching."
  [s]
  (when (seq s)
    (-> s remove-accents str/lower-case)))

(defn- normalize-team-name
  "Strip state suffix (e.g. 'Palmeiras-SP' -> 'Palmeiras') and trim."
  [name]
  (when (seq name)
    (-> name
        str/trim
        (str/replace #"\s*-\s*[A-Z]{2}$" "")   ; remove -SP, -RJ etc.
        (str/replace #"\s+\(.*?\)$" "")          ; remove parenthetical suffixes
        str/trim)))

(defn- team-matches?
  "Returns true if query (case-insensitive, accent-insensitive) appears in team name."
  [query team]
  (when (and (seq query) (seq team))
    (str/includes? (normalize-for-search (normalize-team-name team))
                   (normalize-for-search query))))

(defn- parse-int [s]
  (try (Integer/parseInt (str/trim (str s))) (catch Exception _ nil)))

(defn- parse-year [s]
  (when (seq (str s))
    (try (Integer/parseInt (re-find #"\d{4}" (str s))) (catch Exception _ nil))))

(defn- parse-date
  "Returns a normalised YYYY-MM-DD string, or the original if not parseable."
  [s]
  (let [s (str/trim (str s))]
    (cond
      (re-matches #"\d{4}-\d{2}-\d{2}.*" s) (subs s 0 10)
      (re-matches #"\d{2}/\d{2}/\d{4}" s)
      (let [[d m y] (str/split s #"/")]
        (str y "-" m "-" d))
      :else s)))

(defn- read-csv-file
  "Read a UTF-8 CSV file, returning a seq of maps keyed by header strings."
  [path]
  (try
    (with-open [rdr (io/reader path :encoding "UTF-8")]
      (let [rows (csv/read-csv rdr)
            ;; Strip BOM if present on first header
            headers (map #(str/replace % #"^\uFEFF" "") (first rows))]
        (mapv (fn [row] (zipmap headers row))
              (rest rows))))
    (catch Exception e
      (println "WARN: could not load" path "-" (.getMessage e))
      [])))

;;; ─── Data loading ────────────────────────────────────────────────────────────

(def data-dir
  (let [candidates ["data/kaggle"
                    "../data/kaggle"
                    "../../data/kaggle"]]
    (or (first (filter #(.isDirectory (io/file %)) candidates))
        "data/kaggle")))

(defonce ^:private loaded-data (atom nil))

(defn load-all-data!
  "Load all CSV files and cache the result. Safe to call multiple times."
  []
  (when-not @loaded-data
    (reset! loaded-data
            {:brasileirao   (read-csv-file (str data-dir "/Brasileirao_Matches.csv"))
             :copa-brasil   (read-csv-file (str data-dir "/Brazilian_Cup_Matches.csv"))
             :libertadores  (read-csv-file (str data-dir "/Libertadores_Matches.csv"))
             :br-football   (read-csv-file (str data-dir "/BR-Football-Dataset.csv"))
             :historico     (read-csv-file (str data-dir "/novo_campeonato_brasileiro.csv"))
             :fifa          (read-csv-file (str data-dir "/fifa_data.csv"))}))
  @loaded-data)

(defn get-data [] (load-all-data!))

;;; ─── Unified match representation ───────────────────────────────────────────

(defn- brasileirao-row->match [row]
  {:competition "Brasileirão Serie A"
   :date        (parse-date (get row "datetime"))
   :home-team   (normalize-team-name (get row "home_team"))
   :away-team   (normalize-team-name (get row "away_team"))
   :home-goals  (parse-int (get row "home_goal"))
   :away-goals  (parse-int (get row "away_goal"))
   :season      (parse-int (get row "season"))
   :round       (get row "round")
   :raw-home    (get row "home_team")
   :raw-away    (get row "away_team")})

(defn- copa-brasil-row->match [row]
  {:competition "Copa do Brasil"
   :date        (parse-date (get row "datetime"))
   :home-team   (normalize-team-name (get row "home_team"))
   :away-team   (normalize-team-name (get row "away_team"))
   :home-goals  (parse-int (get row "home_goal"))
   :away-goals  (parse-int (get row "away_goal"))
   :season      (parse-int (get row "season"))
   :round       (get row "round")
   :raw-home    (get row "home_team")
   :raw-away    (get row "away_team")})

(defn- libertadores-row->match [row]
  {:competition "Copa Libertadores"
   :date        (parse-date (get row "datetime"))
   :home-team   (normalize-team-name (get row "home_team"))
   :away-team   (normalize-team-name (get row "away_team"))
   :home-goals  (parse-int (get row "home_goal"))
   :away-goals  (parse-int (get row "away_goal"))
   :season      (parse-int (get row "season"))
   :stage       (get row "stage")
   :raw-home    (get row "home_team")
   :raw-away    (get row "away_team")})

(defn- br-football-row->match [row]
  (let [date-str (parse-date (get row "date"))]
    {:competition  (get row "tournament" "Brazilian Football")
     :date         date-str
     :home-team    (normalize-team-name (get row "home"))
     :away-team    (normalize-team-name (get row "away"))
     :home-goals   (parse-int (get row "home_goal"))
     :away-goals   (parse-int (get row "away_goal"))
     :home-corners (parse-int (get row "home_corner"))
     :away-corners (parse-int (get row "away_corner"))
     :home-shots   (parse-int (get row "home_shots"))
     :away-shots   (parse-int (get row "away_shots"))
     :season       (parse-year date-str)
     :raw-home     (get row "home")
     :raw-away     (get row "away")}))

(defn- historico-row->match [row]
  {:competition "Brasileirão Serie A"
   :date        (parse-date (get row "Data"))
   :home-team   (normalize-team-name (get row "Equipe_mandante"))
   :away-team   (normalize-team-name (get row "Equipe_visitante"))
   :home-goals  (parse-int (get row "Gols_mandante"))
   :away-goals  (parse-int (get row "Gols_visitante"))
   :season      (parse-int (get row "Ano"))
   :round       (get row "Rodada")
   :stadium     (get row "Arena")
   :raw-home    (get row "Equipe_mandante")
   :raw-away    (get row "Equipe_visitante")})

(defn all-matches
  "Return all matches from all sources as normalised maps."
  []
  (let [d (get-data)]
    (concat
     (map brasileirao-row->match (:brasileirao d))
     (map copa-brasil-row->match (:copa-brasil d))
     (map libertadores-row->match (:libertadores d))
     (map br-football-row->match (:br-football d))
     (map historico-row->match (:historico d)))))

;;; ─── Match queries ───────────────────────────────────────────────────────────

(defn search-matches
  "Search matches with optional filters:
   :team      - team name substring (matches either side)
   :home-team - home team name substring
   :away-team - away team name substring
   :season    - integer year
   :competition - competition name substring
   :limit     - max results (default 50)"
  [{:keys [team home-team away-team season competition limit]
    :or {limit 50}}]
  (let [matches (all-matches)
        filtered
        (filter
         (fn [m]
           (and
            (or (nil? team)
                (team-matches? team (:home-team m))
                (team-matches? team (:away-team m)))
            (or (nil? home-team)
                (team-matches? home-team (:home-team m)))
            (or (nil? away-team)
                (team-matches? away-team (:away-team m)))
            (or (nil? season)
                (= season (:season m)))
            (or (nil? competition)
                (str/includes?
                 (normalize-for-search (str (:competition m)))
                 (normalize-for-search competition)))))
         matches)]
    (sort-by :date (take limit filtered))))

(defn head-to-head
  "All matches between team-a and team-b (in either direction)."
  [team-a team-b]
  (let [matches (all-matches)]
    (->> matches
         (filter (fn [m]
                   (or (and (team-matches? team-a (:home-team m))
                            (team-matches? team-b (:away-team m)))
                       (and (team-matches? team-b (:home-team m))
                            (team-matches? team-a (:away-team m))))))
         (sort-by :date))))

(defn head-to-head-stats
  "Summary stats for team-a vs team-b."
  [team-a team-b]
  (let [matches (head-to-head team-a team-b)
        count-a-wins
        (count (filter (fn [m]
                         (let [ah (team-matches? team-a (:home-team m))
                               hg (or (:home-goals m) 0)
                               ag (or (:away-goals m) 0)]
                           (if ah (> hg ag) (> ag hg))))
                       matches))
        count-b-wins
        (count (filter (fn [m]
                         (let [bh (team-matches? team-b (:home-team m))
                               hg (or (:home-goals m) 0)
                               ag (or (:away-goals m) 0)]
                           (if bh (> hg ag) (> ag hg))))
                       matches))
        draws (count (filter #(= (or (:home-goals %) 0) (or (:away-goals %) 0)) matches))]
    {:total-matches (count matches)
     :team-a-wins   count-a-wins
     :team-b-wins   count-b-wins
     :draws         draws}))

;;; ─── Team statistics ─────────────────────────────────────────────────────────

(defn team-stats
  "Compute win/draw/loss/goals for a team, optionally filtered by season and competition."
  [{:keys [team season competition]}]
  (let [matches (search-matches {:team team :season season :competition competition :limit 10000})]
    (reduce
     (fn [acc m]
       (let [home? (team-matches? team (:home-team m))
             gf    (if home? (:home-goals m 0) (:away-goals m 0))
             ga    (if home? (:away-goals m 0) (:home-goals m 0))
             gf    (or gf 0)
             ga    (or ga 0)
             result (cond (> gf ga) :win (= gf ga) :draw :else :loss)]
         (-> acc
             (update :matches inc)
             (update result inc)
             (update :goals-for + gf)
             (update :goals-against + ga)
             (cond-> home? (update :home-matches inc))
             (cond-> (not home?) (update :away-matches inc))
             (cond-> (and home? (= result :win)) (update :home-wins inc))
             (cond-> (and (not home?) (= result :win)) (update :away-wins inc)))))
     {:matches 0 :win 0 :draw 0 :loss 0
      :goals-for 0 :goals-against 0
      :home-matches 0 :away-matches 0
      :home-wins 0 :away-wins 0
      :team team :season season :competition competition}
     matches)))

(defn team-points
  "Points using standard 3-1-0 system."
  [stats]
  (+ (* 3 (:win stats 0)) (:draw stats 0)))

;;; ─── Standings ───────────────────────────────────────────────────────────────

(defn competition-standings
  "Calculate standings table for a competition and season."
  [{:keys [season competition]}]
  (let [matches (search-matches {:season season :competition competition :limit 100000})
        teams   (into #{} (mapcat (fn [m] [(:home-team m) (:away-team m)]) matches))
        stats   (map (fn [t] (team-stats {:team t :season season :competition competition})) teams)]
    (->> stats
         (sort-by (juxt #(- (team-points %)) #(- (:goals-for % 0))))
         (map-indexed (fn [i s] (assoc s :position (inc i)))))))

;;; ─── Biggest wins ────────────────────────────────────────────────────────────

(defn biggest-wins
  "Return matches with the largest goal difference, optionally filtered."
  [{:keys [team season competition limit] :or {limit 20}}]
  (let [matches (search-matches {:team team :season season :competition competition :limit 100000})]
    (->> matches
         (filter (fn [m] (and (some? (:home-goals m)) (some? (:away-goals m)))))
         (sort-by #(- (Math/abs (- (:home-goals % 0) (:away-goals % 0)))))
         (take limit))))

;;; ─── Player queries ──────────────────────────────────────────────────────────

(defn- player-row->player [row]
  {:id           (get row "ID")
   :name         (get row "Name")
   :age          (parse-int (get row "Age"))
   :nationality  (get row "Nationality")
   :overall      (parse-int (get row "Overall"))
   :potential    (parse-int (get row "Potential"))
   :club         (get row "Club")
   :position     (get row "Position")
   :jersey       (get row "Jersey Number")
   :height       (get row "Height")
   :weight       (get row "Weight")
   :value        (get row "Value")
   :wage         (get row "Wage")})

(defn search-players
  "Search FIFA player data.
   :name        - name substring
   :nationality - nationality substring
   :club        - club substring
   :min-overall - minimum overall rating
   :position    - position substring
   :limit       - max results (default 50)"
  [{:keys [name nationality club min-overall position limit]
    :or {limit 50}}]
  (let [rows    (:fifa (get-data))
        players (map player-row->player rows)]
    (->> players
         (filter
          (fn [p]
            (and
             (or (nil? name)
                 (str/includes? (str/lower-case (str (:name p)))
                                (str/lower-case name)))
             (or (nil? nationality)
                 (str/includes? (str/lower-case (str (:nationality p)))
                                (str/lower-case nationality)))
             (or (nil? club)
                 (str/includes? (str/lower-case (str (:club p)))
                                (str/lower-case club)))
             (or (nil? min-overall)
                 (>= (or (:overall p) 0) min-overall))
             (or (nil? position)
                 (str/includes? (str/lower-case (str (:position p)))
                                (str/lower-case position))))))
         (sort-by #(- (or (:overall %) 0)))
         (take limit))))

;;; ─── Statistics ──────────────────────────────────────────────────────────────

(defn global-stats
  "Return aggregate statistics across all matches."
  [{:keys [competition season]}]
  (let [matches (search-matches {:competition competition :season season :limit 100000})
        valid   (filter #(and (some? (:home-goals %)) (some? (:away-goals %))) matches)
        n       (count valid)]
    (if (zero? n)
      {:total-matches 0}
      (let [total-goals (reduce + (map #(+ (:home-goals % 0) (:away-goals % 0)) valid))
            home-wins   (count (filter #(> (:home-goals % 0) (:away-goals % 0)) valid))
            away-wins   (count (filter #(< (:home-goals % 0) (:away-goals % 0)) valid))
            draws       (count (filter #(= (:home-goals % 0) (:away-goals % 0)) valid))]
        {:total-matches      n
         :total-goals        total-goals
         :avg-goals-per-match (double (/ total-goals n))
         :home-wins          home-wins
         :away-wins          away-wins
         :draws              draws
         :home-win-rate      (double (/ home-wins n))
         :away-win-rate      (double (/ away-wins n))
         :draw-rate          (double (/ draws n))}))))
