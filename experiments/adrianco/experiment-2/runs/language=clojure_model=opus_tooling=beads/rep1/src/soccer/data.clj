(ns soccer.data
  "Load Brazilian soccer CSV datasets into normalized maps."
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]))

(def default-data-dir "data/kaggle")

(defn- parse-int [s]
  (when (and s (not= "" s))
    (try (long (Double/parseDouble (str s))) (catch Exception _ nil))))

(defn- parse-double* [s]
  (when (and s (not= "" s))
    (try (Double/parseDouble (str s)) (catch Exception _ nil))))

(defn- strip-bom [s]
  (if (and s (.startsWith ^String s "\uFEFF"))
    (subs s 1)
    s))

(defn- read-csv-maps
  "Read a CSV into a seq of maps keyed by normalized header keywords."
  [path]
  (with-open [r (io/reader path)]
    (let [rows (csv/read-csv r)
          headers (map (fn [h] (-> h strip-bom str/trim (str/replace #"\s+" "_") keyword))
                       (first rows))]
      (doall
       (for [row (rest rows)]
         (zipmap headers row))))))

(defn normalize-team
  "Normalize a team name by stripping state/country suffix and trimming."
  [s]
  (when s
    (-> (str s)
        (str/replace #"\s*[\-–]\s*[A-Z]{2,3}\s*$" "")
        (str/replace #"\s*\([A-Z]{2,3}\)\s*$" "")
        str/trim)))

(defn- parse-date
  "Parse date strings from multiple formats; returns yyyy-MM-dd string."
  [s]
  (when (and s (not= "" s))
    (let [s (str/trim s)]
      (cond
        ;; ISO with time
        (re-matches #"\d{4}-\d{2}-\d{2}.*" s) (subs s 0 10)
        ;; Brazilian dd/mm/yyyy
        (re-matches #"\d{2}/\d{2}/\d{4}" s)
        (let [[d m y] (str/split s #"/")]
          (str y "-" m "-" d))
        :else s))))

(defn- season-from [row date-key season-key]
  (or (parse-int (get row season-key))
      (when-let [d (parse-date (get row date-key))]
        (parse-int (subs d 0 4)))))

(defn load-brasileirao
  "Load Brasileirao_Matches.csv into normalized match maps."
  [dir]
  (let [rows (read-csv-maps (io/file dir "Brasileirao_Matches.csv"))]
    (for [r rows]
      {:competition "Brasileirão"
       :date (parse-date (:datetime r))
       :home (normalize-team (:home_team r))
       :away (normalize-team (:away_team r))
       :home-state (:home_team_state r)
       :away-state (:away_team_state r)
       :home-goal (parse-int (:home_goal r))
       :away-goal (parse-int (:away_goal r))
       :season (parse-int (:season r))
       :round (parse-int (:round r))
       :source "Brasileirao_Matches.csv"})))

(defn load-copa-do-brasil [dir]
  (let [rows (read-csv-maps (io/file dir "Brazilian_Cup_Matches.csv"))]
    (for [r rows]
      {:competition "Copa do Brasil"
       :date (parse-date (:datetime r))
       :home (normalize-team (:home_team r))
       :away (normalize-team (:away_team r))
       :home-goal (parse-int (:home_goal r))
       :away-goal (parse-int (:away_goal r))
       :season (parse-int (:season r))
       :round (when-let [v (:round r)] (str/trim v))
       :source "Brazilian_Cup_Matches.csv"})))

(defn load-libertadores [dir]
  (let [rows (read-csv-maps (io/file dir "Libertadores_Matches.csv"))]
    (for [r rows]
      {:competition "Copa Libertadores"
       :date (parse-date (:datetime r))
       :home (normalize-team (:home_team r))
       :away (normalize-team (:away_team r))
       :home-goal (parse-int (:home_goal r))
       :away-goal (parse-int (:away_goal r))
       :season (parse-int (:season r))
       :stage (:stage r)
       :source "Libertadores_Matches.csv"})))

(defn load-br-football [dir]
  (let [rows (read-csv-maps (io/file dir "BR-Football-Dataset.csv"))]
    (for [r rows]
      {:competition (:tournament r)
       :date (parse-date (:date r))
       :home (normalize-team (:home r))
       :away (normalize-team (:away r))
       :home-goal (parse-int (:home_goal r))
       :away-goal (parse-int (:away_goal r))
       :home-corner (parse-double* (:home_corner r))
       :away-corner (parse-double* (:away_corner r))
       :home-shots (parse-double* (:home_shots r))
       :away-shots (parse-double* (:away_shots r))
       :ht-result (:ht_result r)
       :season (season-from r :date :season)
       :source "BR-Football-Dataset.csv"})))

(defn load-novo [dir]
  (let [rows (read-csv-maps (io/file dir "novo_campeonato_brasileiro.csv"))]
    (for [r rows]
      {:competition "Brasileirão"
       :match-id (:ID r)
       :date (parse-date (:Data r))
       :season (parse-int (:Ano r))
       :round (parse-int (:Rodada r))
       :home (normalize-team (:Equipe_mandante r))
       :away (normalize-team (:Equipe_visitante r))
       :home-goal (parse-int (:Gols_mandante r))
       :away-goal (parse-int (:Gols_visitante r))
       :home-state (:Mandante_UF r)
       :away-state (:Visitante_UF r)
       :winner (:Vencedor r)
       :arena (:Arena r)
       :source "novo_campeonato_brasileiro.csv"})))

(defn load-fifa [dir]
  (let [rows (read-csv-maps (io/file dir "fifa_data.csv"))]
    (for [r rows]
      {:id (parse-int (:ID r))
       :name (:Name r)
       :age (parse-int (:Age r))
       :nationality (:Nationality r)
       :overall (parse-int (:Overall r))
       :potential (parse-int (:Potential r))
       :club (:Club r)
       :position (:Position r)
       :jersey (parse-int (:Jersey_Number r))
       :height (:Height r)
       :weight (:Weight r)
       :preferred-foot (:Preferred_Foot r)})))

(defn load-all-matches
  "Return a vector of all matches across all match CSVs."
  [dir]
  (vec (concat (load-brasileirao dir)
               (load-copa-do-brasil dir)
               (load-libertadores dir)
               (load-br-football dir)
               (load-novo dir))))

(defn load-dataset
  "Load full dataset as {:matches [...] :players [...]}."
  ([] (load-dataset default-data-dir))
  ([dir]
   {:matches (load-all-matches dir)
    :players (vec (load-fifa dir))}))
