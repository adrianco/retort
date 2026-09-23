(ns soccer.query
  "Query and statistics functions over the loaded datasets. Every function takes
  the db map (from soccer.data/load-all) as its first argument."
  (:require [clojure.string :as str]
            [soccer.data :as d]))

;; ---------------------------------------------------------------- teams

(def all-team-keys (memoize (fn [db]
  (into #{} (mapcat (juxt :home-key :away-key)) (:matches db)))))

(defn resolve-team
  "Set of canonical team keys matching a user supplied team name."
  [db name]
  (let [q (d/team-key name) ks (all-team-keys db)]
    (cond (ks q) #{q}
          :else (into #{} (filter #(str/includes? % q)) ks))))

(def competition-aliases
  {"brasileirao" "Brasileirão" "serie a" "Brasileirão" "brasileirao serie a" "Brasileirão"
   "copa do brasil" "Copa do Brasil" "cup" "Copa do Brasil" "brazilian cup" "Copa do Brasil"
   "libertadores" "Copa Libertadores" "copa libertadores" "Copa Libertadores"
   "serie b" "Brasileirão Série B" "serie c" "Brasileirão Série C"})

(defn resolve-competition [c]
  (when (seq c)
    (let [k (str/lower-case (d/strip-accents c))]
      (or (competition-aliases k) c))))

;; ---------------------------------------------------------------- matches

(defn- epoch-day [date]
  (try (.toEpochDay (java.time.LocalDate/parse date)) (catch Exception _ nil)))

(defn dedupe-matches
  "The same fixture appears in several files (sometimes with dates shifted by a
  day or two due to time zones); keep the first per competition/home/away
  within a 3-day window."
  [ms]
  (second
   (reduce (fn [[seen out] m]
             (let [k [(:competition m) (:home-key m) (:away-key m)]
                   day (epoch-day (:date m))
                   days (get seen k #{})]
               (if (and day (some #(<= (Math/abs (- (long %) (long day))) 3) days))
                 [seen out]
                 [(assoc seen k (conj days (or day (hash m)))) (conj out m)])))
           [{} []] ms)))

(defn find-matches
  "Filters: :team :opponent :home-only :away-only :competition :season
  :date-from :date-to (ISO strings). Returns deduped matches, newest first."
  [db {:keys [team opponent home-only away-only competition season date-from date-to]}]
  (let [ts (when team (resolve-team db team))
        os (when opponent (resolve-team db opponent))
        comp (resolve-competition competition)
        season (if (string? season) (d/parse-int season) season)
        pred (fn [m]
               (and (or (nil? ts)
                        (cond home-only (ts (:home-key m))
                              away-only (ts (:away-key m))
                              :else (or (ts (:home-key m)) (ts (:away-key m)))))
                    (or (nil? os)
                        (and (or (os (:home-key m)) (os (:away-key m)))
                             (or (nil? ts)
                                 (and (ts (:home-key m)) (os (:away-key m)))
                                 (and (os (:home-key m)) (ts (:away-key m))))))
                    (or (nil? comp) (= comp (:competition m)))
                    (or (nil? season) (= season (:season m)))
                    (or (nil? date-from) (and (:date m) (>= (compare (:date m) date-from) 0)))
                    (or (nil? date-to) (and (:date m) (<= (compare (:date m) date-to) 0)))))]
    (->> (:matches db) (filter pred) dedupe-matches
         (sort-by #(or (:date %) "") #(compare %2 %1)) vec)))

(defn format-match [m]
  (str (or (:date m) "????-??-??") ": " (:home m) " " (:home-goal m) "-" (:away-goal m)
       " " (:away m) " (" (:competition m)
       (cond (:round m) (str " Round " (:round m))
             (:stage m) (str " " (:stage m)) :else "")
       ")"))

;; ---------------------------------------------------------------- records

(defn team-record
  "W/D/L/GF/GA for the team (set of keys) over the given matches.
  venue: :home, :away or nil (all)."
  [team-keys ms & [venue]]
  (reduce
   (fn [acc m]
     (let [home? (boolean (team-keys (:home-key m)))
           away? (boolean (team-keys (:away-key m)))]
       (if (or (and (= venue :home) (not home?)) (and (= venue :away) (not away?))
               (not (or home? away?)) (nil? (:result m)))
         acc
         (let [[gf ga] (if home? [(:home-goal m) (:away-goal m)] [(:away-goal m) (:home-goal m)])
               outcome (cond (> gf ga) :wins (< gf ga) :losses :else :draws)]
           (-> acc (update :matches inc) (update outcome inc)
               (update :goals-for + gf) (update :goals-against + ga))))))
   {:matches 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0}
   ms))

(defn with-rate [r]
  (assoc r :win-rate (if (pos? (:matches r)) (* 100.0 (/ (:wins r) (:matches r))) 0.0)))

(defn team-stats
  "Record for a team, optionally filtered by season/competition/venue."
  [db {:keys [team season competition venue]}]
  (let [ks (resolve-team db team)
        ms (find-matches db {:team team :season season :competition competition})]
    (with-rate (team-record ks ms (some-> venue keyword)))))

(defn format-record [title r]
  (str title ":\n- Matches: " (:matches r)
       "\n- Wins: " (:wins r) ", Draws: " (:draws r) ", Losses: " (:losses r)
       "\n- Goals For: " (:goals-for r) ", Goals Against: " (:goals-against r)
       (format "\n- Win rate: %.1f%%" (double (:win-rate r)))))

(defn head-to-head [db team-a team-b & [opts]]
  (let [a (resolve-team db team-a) b (resolve-team db team-b)
        ms (find-matches db (merge opts {:team team-a :opponent team-b}))
        ra (team-record a ms)]
    {:matches ms :team-a team-a :team-b team-b
     :a-wins (:wins ra) :b-wins (:losses ra) :draws (:draws ra)}))

(defn format-h2h [{:keys [matches team-a team-b a-wins b-wins draws]} & [limit]]
  (let [limit (or limit 20)]
    (str team-a " vs " team-b ":\n"
         (str/join "\n" (map #(str "- " (format-match %)) (take limit matches)))
         (when (> (count matches) limit) (str "\n- ... (" (- (count matches) limit) " more matches in dataset)"))
         "\n\nHead-to-head in dataset: " team-a " " a-wins " wins, " team-b " " b-wins
         " wins, " draws " draws")))

;; ---------------------------------------------------------------- standings

(defn league-matches
  "Brasileirão Série A matches for a season from a single source (avoids double counting)."
  [db season]
  (let [{:keys [brasileirao historical br-football]} (:sources db)
        pick (fn [src] (seq (filter #(= season (:season %)) src)))]
    (or (pick brasileirao) (pick historical)
        (pick (filter #(= "Brasileirão" (:competition %)) br-football)))))

(defn standings [db season]
  (let [season (if (string? season) (d/parse-int season) season)
        ms (league-matches db season)
        names (into {} (mapcat (fn [m] [[(:home-key m) (:home m)] [(:away-key m) (:away m)]])) ms)]
    (->> (keys names)
         (map (fn [k] (let [r (team-record #{k} ms)]
                        (assoc r :team (names k) :key k
                               :points (+ (* 3 (:wins r)) (:draws r))
                               :goal-diff (- (:goals-for r) (:goals-against r))))))
         (sort-by (juxt (comp - :points) (comp - :wins) (comp - :goal-diff) (comp - :goals-for)))
         vec)))

(defn format-standings [season table]
  (str season " Brasileirão Final Standings (calculated from matches):\n"
       (str/join "\n"
                 (map-indexed (fn [i r]
                                (str (inc i) ". " (:team r) " - " (:points r) " pts ("
                                     (:wins r) "W, " (:draws r) "D, " (:losses r) "L, GD "
                                     (:goal-diff r) ")"
                                     (cond (zero? i) " - Champion"
                                           (>= i (- (count table) 4)) " - Relegated" :else "")))
                              table))))

(defn champion [db season] (first (standings db season)))
(defn relegated [db season] (vec (take-last 4 (standings db season))))

(defn top-scoring-teams [db season]
  (->> (standings db season) (sort-by (comp - :goals-for)) vec))

;; ---------------------------------------------------------------- statistics

(defn summary-stats [ms]
  (let [ms (filter :result ms) n (count ms)
        goals (reduce + (map #(+ (:home-goal %) (:away-goal %)) ms))
        freq (frequencies (map :result ms))
        pct #(if (pos? n) (* 100.0 (/ (get freq % 0) n)) 0.0)]
    {:matches n :goals goals
     :avg-goals (if (pos? n) (double (/ goals n)) 0.0)
     :home-win-rate (pct :home) :away-win-rate (pct :away) :draw-rate (pct :draw)}))

(defn biggest-wins [ms n]
  (->> (filter :result ms) dedupe-matches
       (sort-by (juxt #(- (Math/abs (- (:home-goal %) (:away-goal %))))
                      #(- (+ (:home-goal %) (:away-goal %)))))
       (take n) vec))

(defn best-records
  "Teams ranked by win rate at a venue (:home/:away/nil), min-matches filter."
  [db {:keys [venue competition season min-matches] :or {min-matches 20}}]
  (let [ms (find-matches db {:competition competition :season season})
        names (into {} (mapcat (fn [m] [[(:home-key m) (:home m)] [(:away-key m) (:away m)]])) ms)
        by-team (group-by identity (mapcat (juxt :home-key :away-key) ms))]
    (->> (keys by-team)
         (map (fn [k] (assoc (with-rate (team-record #{k} ms (some-> venue keyword))) :team (names k))))
         (filter #(>= (:matches %) min-matches))
         (sort-by (juxt (comp - :win-rate) (comp - :matches)))
         vec)))

(defn team-competitions [db team]
  (let [ms (find-matches db {:team team})]
    (->> (group-by :competition ms)
         (map (fn [[c xs]] {:competition c :matches (count xs)
                            :seasons (vec (sort (distinct (keep :season xs))))}))
         (sort-by (comp - :matches)) vec)))

(defn cup-finals
  "Copa do Brasil finals (highest round per season) and Libertadores finals."
  [db competition]
  (let [cname (resolve-competition (or competition "Copa do Brasil"))
        ms (find-matches db {:competition cname})]
    (if (= cname "Copa Libertadores")
      (vec (filter #(= "final" (:stage %)) ms))
      (->> (filter #(and (:result %) (= "Brazilian_Cup_Matches.csv" (:source %))) ms)
           (group-by :season)
           (mapcat (fn [[_ xs]] (let [mx (apply max (keep (comp d/parse-int :round) xs))]
                                  (filter #(= mx (d/parse-int (:round %))) xs))))
           (sort-by :date #(compare %2 %1)) vec))))

(def rivalries
  #{#{"flamengo" "fluminense"} #{"flamengo" "vasco"} #{"flamengo" "botafogo"}
    #{"fluminense" "vasco"} #{"fluminense" "botafogo"} #{"vasco" "botafogo"}
    #{"corinthians" "palmeiras"} #{"corinthians" "sao paulo"} #{"corinthians" "santos"}
    #{"palmeiras" "sao paulo"} #{"palmeiras" "santos"} #{"sao paulo" "santos"}
    #{"gremio" "internacional"} #{"atletico mineiro" "cruzeiro"}
    #{"athletico paranaense" "coritiba"} #{"bahia" "vitoria"} #{"sport" "nautico"}
    #{"ceara" "fortaleza"}})

(defn derbies [db opts]
  (vec (filter #(rivalries #{(:home-key %) (:away-key %)}) (find-matches db opts))))

;; ---------------------------------------------------------------- players

(defn find-players
  "Filters: :name :nationality :club :position; sorted by overall desc."
  [db {:keys [name nationality club position limit]}]
  (let [norm #(str/lower-case (d/strip-accents (str %)))
        ck (when club (d/team-key club))
        pos-set (when position
                  (let [p (str/upper-case position)]
                    (case (norm position)
                      ("forward" "forwards" "attacker" "striker") #{"ST" "CF" "LF" "RF" "LW" "RW" "LS" "RS"}
                      ("midfielder" "midfielders") #{"CM" "CAM" "CDM" "LM" "RM" "LCM" "RCM" "LAM" "RAM" "LDM" "RDM"}
                      ("defender" "defenders") #{"CB" "LB" "RB" "LCB" "RCB" "LWB" "RWB"}
                      ("goalkeeper" "goalkeepers" "keeper") #{"GK"}
                      #{p})))]
    (->> (let [ps (:players db)
               exact (when ck (seq (filter #(= ck (:club-key %)) ps)))]
           (or exact ps))
         (filter (fn [p]
                   (and (or (nil? name) (str/includes? (norm (:name p)) (norm name)))
                        (or (nil? nationality) (= (norm nationality) (norm (:nationality p))))
                        (or (nil? ck) (= ck (:club-key p))
                            (str/includes? (norm (:club p)) (norm club)))
                        (or (nil? pos-set) (pos-set (:position p))))))
         (sort-by (comp - #(or (:overall %) 0)))
         (take (or limit 50)) vec)))

(defn format-players [title ps]
  (str title "\n"
       (if (empty? ps) "No players found."
           (str/join "\n" (map-indexed (fn [i p] (str (inc i) ". " (:name p) " - Overall: " (:overall p)
                                                      ", Position: " (:position p) ", Club: " (:club p)
                                                      ", Nationality: " (:nationality p) ", Age: " (:age p)))
                                       ps)))))

(defn players-by-club-summary
  "Players (optionally of a nationality) grouped by club with average rating."
  [db {:keys [nationality clubs]}]
  (let [ps (find-players db {:nationality nationality :limit Integer/MAX_VALUE})
        ks (when clubs (set (map d/team-key clubs)))]
    (->> (group-by :club ps)
         (filter (fn [[c _]] (and (seq c) (or (nil? ks) (ks (d/team-key c))))))
         (map (fn [[c xs]] {:club c :players (count xs)
                            :avg-rating (/ (reduce + (keep :overall xs)) (double (count xs)))}))
         (sort-by (comp - :players)) vec)))

(def brazilian-clubs
  ["Flamengo" "Fluminense" "Palmeiras" "Santos" "São Paulo" "Corinthians" "Grêmio"
   "Internacional" "Cruzeiro" "Atlético Mineiro" "Botafogo" "Vasco da Gama" "Bahia"
   "Atlético Paranaense" "Chapecoense" "América FC (Minas Gerais)" "Sport Club do Recife"
   "Vitória" "Ceará Sporting Club" "Paraná"])

(defn player-team-profile
  "Cross-file query: a player's FIFA info + their club's match record in the match data."
  [db player-name]
  (when-let [p (first (find-players db {:name player-name :limit 1}))]
    (let [ks (when (seq (:club p)) (resolve-team db (:club p)))]
      {:player p
       :club-record (when (seq ks) (with-rate (team-record ks (find-matches db {:team (:club p)}))))})))
