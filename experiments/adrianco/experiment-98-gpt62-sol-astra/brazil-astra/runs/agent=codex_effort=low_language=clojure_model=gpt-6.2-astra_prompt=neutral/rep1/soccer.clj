(ns soccer
  (:require [clojure.data.csv :as csv] [clojure.java.io :as io] [clojure.string :as s])
  (:import [java.text Normalizer Normalizer$Form]))

(defn fold [v]
  (-> (Normalizer/normalize (str v) Normalizer$Form/NFD)
      (s/replace #"\p{M}" "") s/lower-case s/trim))

(def aliases
  {"sport club corinthians paulista" "corinthians" "clube de regatas do flamengo" "flamengo"
   "sociedade esportiva palmeiras" "palmeiras" "sao paulo futebol clube" "sao paulo"
   "vasco" "vasco da gama" "ec bahia" "bahia" "ec juventude" "juventude"
   "atletico mineiro" "atletico mg" "athletico" "atletico pr" "athletico pr" "atletico pr"
   "atletico paranaense" "atletico pr" "athletico paranaense" "atletico pr"
   "atletico goianiense" "atletico go" "america mineiro" "america mg"
   "botafogo rj" "botafogo" "red bull bragantino" "bragantino" "rb bragantino" "bragantino"
   "nautico capibaribe" "nautico" "sport recife" "sport" "sport club do recife" "sport"
   "america fc (minas gerais)" "america mg" "ceara sporting club" "ceara"})

(def team
  (memoize
   (fn [v]
     (let [n (-> (fold v) (s/replace #"\s*-\s*" " ") (s/replace #" f\.?c\.?$" ""))
           base (if (re-find #"^(atletico|athletico|america|botafogo|rio branco|operario|nacional) " n)
                  n (s/replace n #" (ac|al|ap|am|ba|ce|df|es|go|ma|mt|ms|mg|pa|pb|pr|pe|pi|rj|rn|rs|ro|rr|sc|sp|se|to)$" ""))]
       (get aliases base base)))))

(defn number-value [v]
  (when (re-matches #"\d+(?:\.0+)?" (str v)) (Long/parseLong (first (s/split v #"\.")))))

(defn date-value [v]
  (cond (re-find #"^\d{4}-\d\d-\d\d" v) (subs v 0 10)
        (re-matches #"\d{2}/\d{2}/\d{4}" v) (s/join "-" (reverse (s/split v #"/")))))

(defn rows [dir file transform]
  (with-open [r (io/reader (io/file dir file) :encoding "UTF-8")]
    (let [[header & data] (csv/read-csv r)
          keys (mapv keyword header)]
      (mapv #(transform (zipmap keys %)) data))))

(def files ["Brasileirao_Matches.csv" "Brazilian_Cup_Matches.csv" "Libertadores_Matches.csv"
            "novo_campeonato_brasileiro.csv" "BR-Football-Dataset.csv"])

(defn match-row [file r]
  (let [home (or (:home_team r) (:Equipe_mandante r) (:home r))
        away (or (:away_team r) (:Equipe_visitante r) (:away r))
        date (date-value (or (:datetime r) (:Data r) (:date r)))
        season (number-value (or (:season r) (:Ano r) (some-> date (subs 0 4))))
        round (or (:round r) (:Rodada r))
        competition (case file "Brazilian_Cup_Matches.csv" "Copa do Brasil"
                          "Libertadores_Matches.csv" "Libertadores"
                          "BR-Football-Dataset.csv" (:tournament r) "Serie A")]
    {:date date :season season :competition competition :home home :away away
     :home-id (team home) :away-id (team away)
     :home_goal (number-value (or (:home_goal r) (:Gols_mandante r)))
     :away_goal (number-value (or (:away_goal r) (:Gols_visitante r)))
     :round round :stage (or (:stage r)
                             (when (and (= competition "Copa do Brasil") round
                                        (= round (get {2012 "6" 2016 "7" 2021 "7"} season "8"))) "final"))
     :source file :details r}))

(defn player-row [r]
  {:id (:ID r) :name (:Name r) :club (:Club r) :position (:Position r)
   :overall (number-value (:Overall r)) :nationality (:Nationality r)
   :attributes (dissoc r (keyword "\uFEFF"))})

(defn load-db [dir]
  (let [all (mapcat #(rows dir % (partial match-row %)) files)
        fixture-key (juxt :competition :date :home-id :away-id)
        extended (into {} (for [m all :when (= (last files) (:source m))]
                            [(fixture-key m) m]))
        cup-dates (map :date (filter #(= (second files) (:source %)) all))
        cup-end (last (sort cup-dates))
        ;; Prefer the tournament feed over secondary feeds during its coverage.
        primary (filter (fn [{:keys [source season competition date]}]
                          (cond
                            (= competition "Serie A")
                            (= source (cond (<= 2012 season 2022) (first files)
                                            (< season 2012) (nth files 3)
                                            :else (last files)))
                            (and (= competition "Copa do Brasil") (= source (last files)))
                            (pos? (compare date cup-end))
                            :else true)) all)
        fixtures (for [m primary
                       :let [extra (get extended (fixture-key m))]]
                   (if (and extra (not= (:source extra) (:source m)))
                     (cond-> (assoc m :extended_details (:details extra))
                       (nil? (:home_goal m)) (assoc :home_goal (:home_goal extra))
                       (nil? (:away_goal m)) (assoc :away_goal (:away_goal extra)))
                     m))
        ordered (fn [xs] (vec (sort-by (juxt :date :home :away) #(compare %2 %1) xs)))]
    {:matches (ordered fixtures) :sources (update-vals (group-by :source all) ordered)
     :players (vec (sort-by :overall > (rows dir "fifa_data.csv" player-row)))}))

(def derbies
  (set (map set [["flamengo" "fluminense"] ["flamengo" "vasco da gama"]
                 ["palmeiras" "corinthians"] ["santos" "sao paulo"] ["palmeiras" "sao paulo"]
                 ["corinthians" "sao paulo"] ["gremio" "internacional"] ["cruzeiro" "atletico mg"]
                 ["bahia" "vitoria"] ["fortaleza" "ceara"] ["atletico pr" "coritiba"]])))

(defn matches [db {:keys [source team_name opponent venue competition season start end stage derby]}]
  (let [a (team team_name) b (team opponent)
        comp-name (get {"brasileirao" "serie a" "brasileirao serie a" "serie a"
                        "copa libertadores" "libertadores"} (fold competition) (fold competition))]
    (filter (fn [{:keys [home-id away-id date] :as m}]
              (and (or (nil? season) (= season (:season m)))
                   (or (nil? competition) (= comp-name (fold (:competition m))))
                   (or (nil? start) (and date (not (neg? (compare date start)))))
                   (or (nil? end) (and date (not (pos? (compare date end)))))
                   (or (nil? stage) (some #{(fold stage)} (map fold [(:stage m) (:round m)])))
                   (or (not derby) (derbies (hash-set home-id away-id)))
                   (or (nil? team_name)
                       (and (not= venue "away") (= a home-id) (or (nil? opponent) (= b away-id)))
                       (and (not= venue "home") (= a away-id) (or (nil? opponent) (= b home-id))))))
            (if source (get-in db [:sources source]) (:matches db)))))

(defn played? [m] (and (number? (:home_goal m)) (number? (:away_goal m))))
(defn ratio [x y] (when (pos? y) (/ (double x) y)))
(defn record [id pairs]
  (let [n (count pairs) wins (count (filter #(apply > %) pairs))
        draws (count (filter #(apply = %) pairs))
        gf (reduce + (map first pairs)) ga (reduce + (map second pairs))]
    {:team id :matches n :wins wins :draws draws :losses (- n wins draws)
     :points (+ (* 3 wins) draws) :goals_for gf :goals_against ga :goal_difference (- gf ga)
     :win_rate (ratio wins n)}))

(defn standings [ms venue]
  (let [scores (reduce (fn [acc {:keys [home-id away-id home_goal away_goal]}]
                         (cond-> acc
                           (not= venue "away") (update home-id conj [home_goal away_goal])
                           (not= venue "home") (update away-id conj [away_goal home_goal])))
                       {} (filter played? ms))]
    (sort-by (juxt (comp - :points) (comp - :wins) (comp - :goal_difference)
                   (comp - :goals_for) :team)
             (map (fn [[id pairs]] (record id pairs)) scores))))

(defn summary [ms]
  (let [played (filter played? ms) n (count played)]
    {:fixtures (count ms) :played n
     :average_goals (ratio (reduce + (map #(+ (:home_goal %) (:away_goal %)) played)) n)
     :home_win_rate (ratio (count (filter #(> (:home_goal %) (:away_goal %)) played)) n)}))

(defn page [xs {:keys [offset limit] :or {offset 0 limit 20}}]
  {:total (count xs) :offset offset :results (vec (take limit (drop offset xs)))})

(defn players [db {:keys [name nationality club position]}]
  (filter #(and (or (nil? name) (s/includes? (fold (:name %)) (fold name)))
                (or (nil? nationality) (= (fold nationality) (fold (:nationality %))))
                (or (nil? club) (= (team club) (team (:club %))))
                (or (nil? position) (if (= "forward" (fold position))
                                      (#{"ST" "CF" "LW" "RW" "LF" "RF" "LS" "RS"} (:position %))
                                      (= (fold position) (fold (:position %))))))
          (:players db)))

(defn query [db tool {:keys [team_name venue group_by rank_by] :as args}]
  (let [ms (matches db args)]
    (case tool
      "matches" (page ms args)
      "players" (page (players db args) args)
      "team_profile" (let [id (team team_name)
                           team-record (fn [games]
                                         (or (first (filter #(= id (:team %)) (standings games venue)))
                                             (record id [])))]
                       {:team id :record (team-record ms)
                        :by_competition (update-vals (group-by :competition ms) team-record)
                        :by_season (into {} (for [[year games] (group-by :season ms)]
                                              [(str year) (team-record games)]))
                        :players (page (players db {:club team_name}) args)})
      "standings" (let [table (standings ms venue)]
                    (page (case rank_by "goals" (sort-by :goals_for > table)
                                "win_rate" (sort-by :win_rate > table) table) args))
      "statistics" (if group_by
                     (into {} (for [[k games] (group-by (keyword group_by) ms)]
                                [(str k) (summary games)]))
                     (summary ms))
      "biggest_wins" (page (sort-by #(abs (- (:home_goal %) (:away_goal %))) >
                                    (filter #(and (played? %) (not= (:home_goal %) (:away_goal %))) ms)) args))))
