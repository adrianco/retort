(ns brazilian-soccer-mcp.data
  "Load CSV datasets into normalized in-memory collections.

   Each match is reduced to a common schema:
     {:competition :season :round :date :datetime
      :home :away :home-goal :away-goal
      :home-state :away-state :stage :arena :source}
   so downstream queries don't care which file a row came from.

   The 5 match files overlap: BR-Football, Brasileirao_Matches, and
   the historical 2003-2019 file all carry Brasileirão Série A rows
   for some shared years. load-all dedupes by
   (competition, season, normalize(home), normalize(away), date)
   so per-season aggregates (standings, head-to-head, points) are not
   double-counted."
  (:require [brazilian-soccer-mcp.normalize :as norm]
            [clojure.data.csv :as csv]
            [clojure.java.io  :as io]
            [clojure.string   :as str]))

(def ^:dynamic *data-root* "data/kaggle")

(defn- read-csv [path]
  (with-open [r (io/reader path)]
    (doall (csv/read-csv r))))

(defn- rows->maps [[header & rows]]
  (let [ks (mapv #(-> % (str/replace "﻿" "") str/trim keyword) header)]
    (mapv #(zipmap ks %) rows)))

(defn- parse-long-safe [s]
  (try
    (when (and s (not (str/blank? (str s))))
      (Long/parseLong (str/trim (str/replace (str s) #"\.0$" ""))))
    (catch Exception _ nil)))

(defn- parse-double-safe [s]
  (try
    (when (and s (not (str/blank? (str s))))
      (Double/parseDouble (str/trim (str s))))
    (catch Exception _ nil)))

(defn- iso-date
  "Best-effort: pull a YYYY-MM-DD out of strings like
     '2012-05-19 18:30:00', '29/03/2003', '2023-09-24'."
  [s]
  (when (and s (not (str/blank? (str s))))
    (let [s (str/trim (str s))]
      (cond
        (re-matches #"\d{4}-\d{2}-\d{2}.*" s)
        (subs s 0 10)

        (re-matches #"\d{2}/\d{2}/\d{4}" s)
        (let [[d m y] (str/split s #"/")]
          (str y "-" m "-" d))

        :else s))))

;; ---- loaders -----------------------------------------------------------

(defn load-brasileirao [path]
  (->> (read-csv path)
       rows->maps
       (mapv (fn [r]
               {:competition "Brasileirão Série A"
                :season      (parse-long-safe (:season r))
                :round       (parse-long-safe (:round r))
                :datetime    (:datetime r)
                :date        (iso-date (:datetime r))
                :home        (:home_team r)
                :away        (:away_team r)
                :home-state  (:home_team_state r)
                :away-state  (:away_team_state r)
                :home-goal   (parse-long-safe (:home_goal r))
                :away-goal   (parse-long-safe (:away_goal r))
                :source      "Brasileirao_Matches.csv"}))))

(defn load-cup [path]
  (->> (read-csv path)
       rows->maps
       (mapv (fn [r]
               {:competition "Copa do Brasil"
                :season      (parse-long-safe (:season r))
                :round       (or (parse-long-safe (:round r)) (:round r))
                :datetime    (:datetime r)
                :date        (iso-date (:datetime r))
                :home        (:home_team r)
                :away        (:away_team r)
                :home-goal   (parse-long-safe (:home_goal r))
                :away-goal   (parse-long-safe (:away_goal r))
                :source      "Brazilian_Cup_Matches.csv"}))))

(defn load-libertadores [path]
  (->> (read-csv path)
       rows->maps
       (mapv (fn [r]
               {:competition "Copa Libertadores"
                :season      (parse-long-safe (:season r))
                :stage       (:stage r)
                :datetime    (:datetime r)
                :date        (iso-date (:datetime r))
                :home        (:home_team r)
                :away        (:away_team r)
                :home-goal   (parse-long-safe (:home_goal r))
                :away-goal   (parse-long-safe (:away_goal r))
                :source      "Libertadores_Matches.csv"}))))

(defn- canonical-competition [c]
  (let [lc (str/lower-case (str c))]
    (cond
      (or (str/includes? lc "brasileir")
          (= "serie a" lc)
          (str/includes? lc "série a"))         "Brasileirão Série A"
      (str/includes? lc "copa do brasil")        "Copa do Brasil"
      (str/includes? lc "libertadores")          "Copa Libertadores"
      :else                                      c)))

(defn load-br-football [path]
  (->> (read-csv path)
       rows->maps
       (mapv (fn [r]
               {:competition (canonical-competition (:tournament r))
                :season      (some-> (:date r) iso-date (subs 0 4) parse-long-safe)
                :date        (iso-date (:date r))
                :datetime    (str (:date r) " " (:time r))
                :home        (:home r)
                :away        (:away r)
                :home-goal   (some-> (:home_goal r) parse-double-safe long)
                :away-goal   (some-> (:away_goal r) parse-double-safe long)
                :home-corner (parse-double-safe (:home_corner r))
                :away-corner (parse-double-safe (:away_corner r))
                :home-shots  (parse-double-safe (:home_shots r))
                :away-shots  (parse-double-safe (:away_shots r))
                :ht-result   (:ht_result r)
                :at-result   (:at_result r)
                :source      "BR-Football-Dataset.csv"}))))

(defn- with-state [team state]
  (if (and team state (not (str/blank? (str state)))
           (not (re-find #"[-–—]\s*[A-Z]{2}\s*$" (str team))))
    (str team "-" state)
    team))

(defn load-historical [path]
  (->> (read-csv path)
       rows->maps
       (mapv (fn [r]
               {:competition "Brasileirão Série A"
                :season      (parse-long-safe (:Ano r))
                :round       (parse-long-safe (:Rodada r))
                :datetime    (:Data r)
                :date        (iso-date (:Data r))
                :home        (with-state (:Equipe_mandante r)  (:Mandante_UF r))
                :away        (with-state (:Equipe_visitante r) (:Visitante_UF r))
                :home-state  (:Mandante_UF r)
                :away-state  (:Visitante_UF r)
                :home-goal   (parse-long-safe (:Gols_mandante r))
                :away-goal   (parse-long-safe (:Gols_visitante r))
                :winner      (:Vencedor r)
                :arena       (:Arena r)
                :source      "novo_campeonato_brasileiro.csv"}))))

(defn load-fifa-players [path]
  (->> (read-csv path)
       rows->maps
       (mapv (fn [r]
               {:id          (parse-long-safe (:ID r))
                :name        (:Name r)
                :age         (parse-long-safe (:Age r))
                :nationality (:Nationality r)
                :overall     (parse-long-safe (:Overall r))
                :potential   (parse-long-safe (:Potential r))
                :club        (:Club r)
                :position    (:Position r)
                :jersey      (parse-long-safe (:Jersey r))
                :height      (:Height r)
                :weight      (:Weight r)
                :foot        (:Preferred r)}))))

;; ---- top-level db ------------------------------------------------------

(defn- path [name]
  (str *data-root* "/" name))

(defn- dedupe-key [m]
  [(:competition m) (:season m)
   (norm/normalize (:home m)) (norm/normalize (:away m))
   (:date m)])

(defn- dedupe-matches
  "Keep the first record encountered for a given
   (competition, season, home, away, date) tuple. Source ordering in
   load-all determines which dataset wins; historical (which has round
   numbers) is listed before the extended dataset (which doesn't)."
  [ms]
  (->> ms
       (reduce (fn [{:keys [seen out]} m]
                 (let [k (dedupe-key m)]
                   (if (contains? seen k)
                     {:seen seen :out out}
                     {:seen (conj seen k) :out (conj out m)})))
               {:seen #{} :out []})
       :out))

(defn load-all
  "Load every CSV into a single map. Slow-ish (a few seconds);
   call once at startup."
  []
  (let [brasileirao  (load-brasileirao  (path "Brasileirao_Matches.csv"))
        cup          (load-cup          (path "Brazilian_Cup_Matches.csv"))
        libertadores (load-libertadores (path "Libertadores_Matches.csv"))
        extended     (load-br-football  (path "BR-Football-Dataset.csv"))
        historical   (load-historical   (path "novo_campeonato_brasileiro.csv"))
        players      (load-fifa-players (path "fifa_data.csv"))
        ;; BR-Football (`extended`) uses different team naming conventions
        ;; ('Atletico Mineiro' vs 'Atletico-MG', 'EC Bahia' vs 'Bahia-BA'),
        ;; which makes dedupe against the canonical sources unreliable.
        ;; We include it for years/competitions the canonical files don't
        ;; cover:
        ;;   Brasileirão Série A: Brasileirao_Matches.csv ends at 2022
        ;;   Copa do Brasil:      Brazilian_Cup_Matches.csv ends at 2021
        ;;   Série B / Série C:   only in BR-Football
        extended-fill (filter (fn [{:keys [competition season]}]
                                (cond
                                  (= "Brasileirão Série A" competition) (and season (> season 2022))
                                  (= "Copa do Brasil"      competition) (and season (> season 2021))
                                  :else                                 true))
                              extended)
        matches      (dedupe-matches
                      (concat historical brasileirao cup libertadores
                              extended-fill))]
    {:matches      matches
     :brasileirao  brasileirao
     :cup          cup
     :libertadores libertadores
     :extended     extended
     :historical   historical
     :players      players}))

(defonce ^:private db-cache (atom nil))

(defn db
  "Memoized loader. Pass :force true to reload."
  ([] (db {}))
  ([{:keys [force]}]
   (when (or force (nil? @db-cache))
     (reset! db-cache (load-all)))
   @db-cache))
