(ns soccer.query
  (:require [clojure.string :as str]
            [soccer.data :as data]))

(def derbies
  (set (map set [["flamengo" "fluminense"] ["flamengo" "vasco"] ["flamengo" "botafogo"]
                 ["fluminense" "vasco"] ["fluminense" "botafogo"] ["vasco" "botafogo"]
                 ["corinthians" "palmeiras"] ["corinthians" "sao paulo"] ["corinthians" "santos"]
                 ["palmeiras" "sao paulo"] ["palmeiras" "santos"] ["sao paulo" "santos"]
                 ["gremio" "internacional"] ["atletico mg" "cruzeiro"] ["bahia" "vitoria"]
                 ["ceara" "fortaleza"] ["athletico pr" "coritiba"] ["sport" "nautico"]
                 ["sport" "santa cruz"] ["nautico" "santa cruz"] ["goias" "vila nova"]
                 ["america rn" "abc"] ["avai" "figueirense"]])))

(defn sides [{:keys [home-id away-id]} venue]
  (case venue "home" [home-id] "away" [away-id] [home-id away-id]))

(defn scored? [{:keys [home-goals away-goals]}]
  (and (some? home-goals) (some? away-goals)))

(defn matches [db {:keys [team opponent venue competition season from to round stage source
                          derby completed]}]
  (let [team (some-> team data/team-id)
        opponent (some-> opponent data/team-id)
        competition (some-> competition data/competition-id)
        from (some-> from data/parse-date str)
        to (some-> to data/parse-date str)
        stage (some-> stage data/fold)
        fixtures (if source (get-in db [:sources source]) (:matches db))]
    (when (and from to (pos? (compare from to)))
      (throw (ex-info "The start date must precede or equal the end date." {})))
    (filterv
     (fn [{:keys [date home-id away-id] :as match}]
       (and (or (nil? team) (some #{team} (sides match venue)))
            (or (nil? opponent) (and (not= team opponent) (some #{opponent} (sides match nil))))
            (or (nil? competition) (= competition (:competition match)))
            (or (nil? season) (= season (:season match)))
            (or (nil? round) (= round (:round match)))
            (or (nil? stage) (= stage (:stage match)))
            (or (nil? from) (and date (not (neg? (compare date from)))))
            (or (nil? to) (and date (not (pos? (compare date to)))))
            (or (not derby) (contains? derbies (set [home-id away-id])))
            (or (nil? completed) (= completed (scored? match)))))
     fixtures)))

(defn page [items {:keys [limit offset] :or {limit 20 offset 0}}]
  (let [total (count items)
        results (vec (take limit (drop offset items)))]
    {:total total :offset offset :results results
     :next-offset (when (< (+ offset (count results)) total) (+ offset (count results)))}))

(defn find-matches [db args]
  (page (if (:source args)
          (sort-by (juxt :date :time) #(compare %2 %1) (matches db args))
          (matches db args))
        args))

(def empty-record {:played 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0})

(defn add-result [record goals conceded]
  (-> (or record empty-record)
      (update :played inc)
      (update (cond (> goals conceded) :wins (< goals conceded) :losses :else :draws) inc)
      (update :goals-for + goals)
      (update :goals-against + conceded)))

(defn ratio [n d]
  (when (pos? d) (/ (double n) d)))

(defn finish-record [{:keys [wins draws played goals-for goals-against] :as record}]
  (assoc record :points (+ (* 3 wins) draws)
         :goal-difference (- goals-for goals-against)
         :win-rate (ratio wins played)))

(defn team-record [fixtures team]
  (finish-record
   (reduce (fn [record {:keys [home-id home-goals away-goals]}]
             (if (= team home-id)
               (add-result record home-goals away-goals)
               (add-result record away-goals home-goals)))
           empty-record (filter scored? fixtures))))

(defn breakdown [key fixtures team]
  (->> (group-by key fixtures)
       (sort-by key)
       (mapv (fn [[label games]]
               {:group label :fixtures (count games) :record (team-record games team)}))))

(defn team-stats [db {:keys [team] :as args}]
  (let [fixtures (matches db args)
        id (data/team-id team)]
    {:team team :team-id id :fixtures (count fixtures)
     :record (team-record fixtures id)
     :by-season (breakdown :season fixtures id)
     :by-competition (breakdown :competition fixtures id)
     :home (team-record (filter #(= id (:home-id %)) fixtures) id)
     :away (team-record (filter #(= id (:away-id %)) fixtures) id)}))

(defn head-to-head [db {:keys [team opponent] :as args}]
  (when (= (data/team-id team) (data/team-id opponent))
    (throw (ex-info "Choose two different teams." {})))
  (let [fixtures (matches db args)]
    {:team team :opponent opponent :team-record (team-record fixtures (data/team-id team))
     :opponent-record (team-record fixtures (data/team-id opponent))
     :matches (page (sort-by (juxt :date :time) #(compare %2 %1) fixtures) args)}))

(def forwards #{"ST" "CF" "LF" "RF" "LW" "RW" "LS" "RS"})

(def player-aliases {"gabigol" "gabriel barbosa"})

(defn players [db {:keys [name nationality club position domestic-only]}]
  (let [name (some-> name data/fold)
        name (get player-aliases name name)
        nationality (some-> nationality data/fold)
        nationality (if (= "brazilian" nationality) "brazil" nationality)
        club (some-> club data/team-id)
        position (some-> position data/fold)]
    (filterv
     (fn [player]
       (and (or (nil? name) (str/includes? (data/fold (:name player)) name))
            (or (nil? nationality) (= nationality (data/fold (:nationality player))))
            (or (nil? club) (= club (:club-id player)))
            (or (nil? position)
                (if (#{"forward" "forwards"} position)
                  (contains? forwards (:position player))
                  (= position (data/fold (:position player)))))
            (or (not domestic-only) (contains? (:domestic-clubs db) (:club-id player)))))
     (:players db))))

(defn find-players [db args]
  (let [results (page (players db args) args)]
    (assoc (if (:include-attributes args)
             results
             (update results :results #(mapv (fn [player] (dissoc player :attributes)) %)))
           :note "Club affiliations, ages and ratings reflect the FIFA dataset snapshot.")))

(defn club-profile [db {:keys [team] :as args}]
  {:team (team-stats db args)
   :players (find-players db (assoc args :club team))})

(defn club-player-summary [db args]
  (page (->> (players db args)
             (group-by (juxt :club-id :club))
             (map (fn [[[id club] roster]]
                    (let [ratings (keep :overall roster)]
                      {:club-id id :club club :players (count roster)
                       :average-overall (ratio (reduce + ratings) (count ratings))})))
             (sort-by (juxt (comp - :players) :club))) args))

(defn records [fixtures venue]
  (->> fixtures
       (reduce (fn [teams {:keys [home-id away-id home away home-goals away-goals] :as match}]
                 (cond-> teams
                   (and (scored? match) (not= venue "away"))
                   (update home-id (fn [record]
                                     (assoc (add-result record home-goals away-goals)
                                            :team home :team-id home-id)))
                   (and (scored? match) (not= venue "home"))
                   (update away-id (fn [record]
                                     (assoc (add-result record away-goals home-goals)
                                            :team away :team-id away-id)))))
               {})
       vals (map finish-record)))

(defn standings [db {:keys [competition season] :as args}]
  (let [competition (data/competition-id (or competition "Serie A"))]
    (when-not (str/starts-with? competition "Brasileirão Série")
      (throw (ex-info "Standings are available for league competitions. Use knockout_bracket for cup stages." {})))
    (let [fixtures (matches db {:competition competition :season season :source (:source args)})
          table (->> (records fixtures nil)
                     (sort-by (juxt (comp - :points) (comp - :wins) (comp - :goal-difference)
                                    (comp - :goals-for) :team-id))
                     (map-indexed #(assoc %2 :rank (inc %1))) vec)
          expected (when (= competition "Brasileirão Série A")
                     (data/expected-serie-a-matches season))
          complete? (and expected (= expected (count fixtures))
                         (every? scored? fixtures)
                         (every? #(= (* 2 (dec (count table))) (:played %)) table))]
      {:competition competition :season season :fixtures (count fixtures)
       :complete (boolean complete?)
       :leader (first table)
       :relegation-zone (when (and complete? (>= season 2005)) (vec (take-last 4 table)))
       :standings table
       :note "Calculated from available results using points, wins, goal difference and goals scored. Administrative adjustments and further tie-breakers are outside the source data."})))

(def bracket-order ["round of 16" "quarterfinals" "semifinals" "final"])

(defn knockout-bracket [db args]
  (when-not (#{"Copa Libertadores" "Copa do Brasil"} (data/competition-id (:competition args)))
    (throw (ex-info "Choose Copa Libertadores or Copa do Brasil for a knockout bracket." {})))
  (let [fixtures (matches db args)
        stages (group-by #(or (:stage %) (some-> (:round %) (->> (str "round "))) "unknown")
                         (remove #(= "group stage" (:stage %)) fixtures))
        ordered (concat (sort (remove (set bracket-order) (keys stages)))
                        (filter stages bracket-order))]
    {:stages (mapv (fn [stage] {:stage stage :matches (vec (sort-by :date (stages stage)))}) ordered)
     :note "Fixtures and scores reflect available CSV records. Penalty shootout scores are unavailable."}))

(defn aggregate [fixtures]
  (let [completed (filterv scored? fixtures)
        played (count completed)
        goals (reduce + (map #(+ (:home-goals %) (:away-goals %)) completed))
        outcomes (frequencies (map #(compare (:home-goals %) (:away-goals %)) completed))]
    {:fixtures (count fixtures) :played played :goals goals :goals-per-match (ratio goals played)
     :home-wins (get outcomes 1 0) :away-wins (get outcomes -1 0) :draws (get outcomes 0 0)
     :home-win-rate (ratio (get outcomes 1 0) played)}))

(defn match-statistics [db args]
  (let [fixtures (matches db args)]
    (assoc (aggregate fixtures)
           :by-season (mapv (fn [[season games]] (assoc (aggregate games) :season season))
                            (sort-by key (group-by :season fixtures)))
           :biggest-wins (page (->> fixtures (filter scored?)
                                    (keep (fn [{:keys [home-goals away-goals] :as match}]
                                            (let [margin (abs (- home-goals away-goals))]
                                              (when (pos? margin) (assoc match :margin margin)))))
                                    (sort-by (juxt :margin :date) #(compare %2 %1)))
                               args))))

(defn team-leaders [db {:keys [venue metric min-played] :or {metric "win-rate" min-played 1} :as args}]
  (page (->> (records (matches db args) venue)
             (filter #(>= (:played %) min-played))
             (sort-by (juxt (comp - (keyword metric)) (comp - :played) :team-id)))
        args))
