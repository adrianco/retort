(ns brazilian-soccer-mcp.core
  (:require [brazilian-soccer-mcp.csv :as csv]
            [clojure.string :as str])
  (:import (java.text Normalizer Normalizer$Form)
           (java.time LocalDate)))

(defn fold [x]
  (-> (Normalizer/normalize (str (or x "")) Normalizer$Form/NFD)
      (str/replace #"\p{M}" "") str/lower-case str/trim))

(defn team-key [team]
  (-> (fold team)
      (str/replace #"\s*-\s*[a-z]{2}$" "")
      (str/replace #"\b(futebol clube|football club|esporte clube|sport club)\b" "")
      (str/replace #"[^a-z0-9]+" " ") str/trim))

(defn number [x]
  (try (when-not (str/blank? (str x)) (long (Double/parseDouble (str x))))
       (catch Exception _ nil)))

(defn year-of [date]
  (or (some->> (re-find #"(?:19|20)\d{2}" (str date)) number) nil))

(defn date-key [s]
  (let [s (str s)]
    (cond (re-matches #"\d{4}-\d\d-\d\d.*" s) (subs s 0 10)
          (re-matches #"\d\d/\d\d/\d{4}" s) (let [[d m y] (str/split s #"/")] (str y "-" m "-" d))
          :else s)))

(defn standard-match [competition row]
  {:competition competition :date (date-key (:datetime row)) :season (number (:season row))
   :round (or (:round row) (:stage row)) :home (:home_team row) :away (:away_team row)
   :home-key (team-key (:home_team row)) :away-key (team-key (:away_team row))
   :home-goals (number (:home_goal row)) :away-goals (number (:away_goal row))})

(defn extended-match [row]
  {:competition (:tournament row) :date (date-key (:date row)) :season (year-of (:date row))
   :home (:home row) :away (:away row) :home-key (team-key (:home row)) :away-key (team-key (:away row))
   :home-goals (number (:home_goal row)) :away-goals (number (:away_goal row))
   :corners {:home (number (:home_corner row)) :away (number (:away_corner row))}
   :shots {:home (number (:home_shots row)) :away (number (:away_shots row))}})

(defn historical-match [row]
  {:competition "Brasileirão" :date (date-key (:Data row)) :season (number (:Ano row)) :round (:Rodada row)
   :home (:Equipe_mandante row) :away (:Equipe_visitante row)
   :home-key (team-key (:Equipe_mandante row)) :away-key (team-key (:Equipe_visitante row))
   :home-goals (number (:Gols_mandante row)) :away-goals (number (:Gols_visitante row)) :stadium (:Arena row)})

(defn player [row]
  {:id (:ID row) :name (:Name row) :age (number (:Age row)) :nationality (:Nationality row)
   :overall (number (:Overall row)) :potential (number (:Potential row)) :club (:Club row)
   :position (:Position row) :name-key (fold (:Name row)) :club-key (fold (:Club row))})

(defn load-data
  ([] (load-data "data/kaggle"))
  ([dir]
   (let [p #(str dir "/" %)]
     {:matches (vec (concat
                     (map #(standard-match "Brasileirão" %) (csv/read-csv (p "Brasileirao_Matches.csv")))
                     (map #(standard-match "Copa do Brasil" %) (csv/read-csv (p "Brazilian_Cup_Matches.csv")))
                     (map #(standard-match "Copa Libertadores" %) (csv/read-csv (p "Libertadores_Matches.csv")))
                     (map extended-match (csv/read-csv (p "BR-Football-Dataset.csv")))
                     (map historical-match (csv/read-csv (p "novo_campeonato_brasileiro.csv")))))
      :players (mapv player (csv/read-csv (p "fifa_data.csv")))})))

(defn match? [m {:keys [team team-a team-b competition season from to]}]
  (let [teams (set (map team-key (remove nil? [team team-a team-b])))]
    (and (or (empty? teams) (every? #(or (= % (:home-key m)) (= % (:away-key m))) teams))
         (or (nil? competition) (str/includes? (fold (:competition m)) (fold competition)))
         (or (nil? season) (= (number season) (:season m)))
         (or (nil? from) (not (neg? (compare (:date m) (date-key from)))))
         (or (nil? to) (not (pos? (compare (:date m) (date-key to))))))))

(defn search-matches [db criteria]
  (let [limit (min 500 (or (number (:limit criteria)) 50))]
    (->> (:matches db) (filter #(match? % criteria)) (sort-by :date #(compare %2 %1)) (take limit) vec)))

(defn record-for [matches key home-only? away-only?]
  (reduce (fn [r m]
            (let [home? (= key (:home-key m))
                  eligible (and (or home? (= key (:away-key m))) (or (not home-only?) home?) (or (not away-only?) (not home?)))]
              (if-not eligible r
                (let [gf (if home? (:home-goals m) (:away-goals m)) ga (if home? (:away-goals m) (:home-goals m))]
                  (cond-> (-> r (update :matches inc) (update :goals-for + gf) (update :goals-against + ga))
                    (> gf ga) (update :wins inc) (= gf ga) (update :draws inc) (< gf ga) (update :losses inc))))))
          {:matches 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0} matches))

(defn team-stats [db {:keys [team competition season venue] :as criteria}]
  (let [matches (search-matches db (assoc criteria :limit 100000))
        r (record-for matches (team-key team) (= "home" (fold venue)) (= "away" (fold venue)))]
    (assoc r :team team :competition competition :season (number season)
           :win-rate (if (pos? (:matches r)) (/ (* 100.0 (:wins r)) (:matches r)) 0.0))))

(defn head-to-head [db team-a team-b criteria]
  (let [matches (search-matches db (merge criteria {:team-a team-a :team-b team-b :limit 100000}))
        a (team-key team-a) stats (reduce (fn [s m] (let [ag (if (= a (:home-key m)) (:home-goals m) (:away-goals m)) bg (if (= a (:home-key m)) (:away-goals m) (:home-goals m))]
                                                (cond-> s (> ag bg) (update :team-a-wins inc) (= ag bg) (update :draws inc) (< ag bg) (update :team-b-wins inc))))
                                             {:team-a-wins 0 :team-b-wins 0 :draws 0} matches)]
    (assoc stats :team-a team-a :team-b team-b :matches (count matches) :recent (take 20 matches))))

(defn search-players [db {:keys [name nationality club position limit]}]
  (let [contains? #(str/includes? (fold %1) (fold %2))]
    (->> (:players db)
         (filter #(and (or (nil? name) (contains? (:name %) name)) (or (nil? nationality) (contains? (:nationality %) nationality))
                       (or (nil? club) (contains? (:club %) club)) (or (nil? position) (contains? (:position %) position))))
         (sort-by :overall #(compare %2 %1)) (take (min 500 (or (number limit) 50))) vec)))

(defn standings [db {:keys [competition season]}]
  (let [matches (search-matches db {:competition (or competition "Brasileirão") :season season :limit 100000})]
    (->> (reduce (fn [table m]
                   (letfn [(add [t team gf ga] (let [r (get t team {:team team :played 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0 :points 0})]
                                                  (assoc t team (cond-> (-> r (update :played inc) (update :goals-for + gf) (update :goals-against + ga))
                                                                  (> gf ga) (-> (update :wins inc) (update :points + 3)) (= gf ga) (-> (update :draws inc) (update :points inc)) (< gf ga) (update :losses inc)))))]
                     (-> table (add (:home m) (:home-goals m) (:away-goals m)) (add (:away m) (:away-goals m) (:home-goals m))))) {} matches)
         vals (sort-by (juxt :points #(- (:goals-for %) (:goals-against %)) :goals-for) #(compare %2 %1)) vec)))

(defn dataset-statistics [db {:keys [competition season]}]
  (let [ms (search-matches db {:competition competition :season season :limit 100000})
        scored (filter #(and (some? (:home-goals %)) (some? (:away-goals %))) ms)
        total (reduce + 0 (map #(+ (:home-goals %) (:away-goals %)) scored))]
    {:matches (count ms) :scored-matches (count scored) :average-goals-per-match (if (seq scored) (/ (double total) (count scored)) 0.0)
     :home-wins (count (filter #(> (:home-goals %) (:away-goals %)) scored)) :draws (count (filter #(= (:home-goals %) (:away-goals %)) scored))
     :away-wins (count (filter #(< (:home-goals %) (:away-goals %)) scored))}))
