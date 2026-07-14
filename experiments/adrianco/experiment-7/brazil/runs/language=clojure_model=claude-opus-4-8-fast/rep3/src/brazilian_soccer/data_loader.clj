;; =============================================================================
;; brazilian-soccer.data-loader
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   Reads the six provided Kaggle CSV files (data/kaggle/) and converts each row
;;   into a uniform internal record so the rest of the system never has to know
;;   which file a match or player came from.
;;
;;   Files & the canonical competition they map to:
;;     Brasileirao_Matches.csv          -> "Brasileirão Série A" (2012-2022)
;;     novo_campeonato_brasileiro.csv   -> "Brasileirão Série A" (2003-2019)
;;     Brazilian_Cup_Matches.csv        -> "Copa do Brasil"
;;     Libertadores_Matches.csv         -> "Copa Libertadores"
;;     BR-Football-Dataset.csv          -> "Brasileirão Série A/B/C" or "Copa do Brasil"
;;                                         (+ extended stats: shots, corners, attacks)
;;     fifa_data.csv                    -> player records (FIFA ratings/attributes)
;;
;; UNIFORM MATCH RECORD
;;   {:competition :season :round :stage :date
;;    :home :away                ; clean display names
;;    :home-key :away-key        ; normalize/team-key for matching & grouping
;;    :home-goals :away-goals    ; ints (nil if unknown)
;;    :source                    ; originating file keyword
;;    :stats {...}}              ; extended stats when available
;;
;; UNIFORM PLAYER RECORD
;;   {:id :name :age :nationality :overall :potential :club :position
;;    :jersey :height :weight :preferred-foot
;;    :name-key :nationality-key :club-key}
;; =============================================================================
(ns brazilian-soccer.data-loader
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer.normalize :as n]))

(def default-data-dir "data/kaggle")

;; ---------------------------------------------------------------------------
;; CSV reading helpers
;; ---------------------------------------------------------------------------

(defn- strip-bom [s]
  ;; fifa_data.csv starts with a UTF-8 BOM on the first header cell
  (if (and s (pos? (count s)) (= (first s) \uFEFF))
    (subs s 1)
    s))

(defn read-csv-maps
  "Read a CSV file into a lazy-realised vector of maps keyed by header string.
   Reads as UTF-8 and strips a leading BOM from the first header cell."
  [path]
  (with-open [r (io/reader path :encoding "UTF-8")]
    (let [rows (csv/read-csv r)
          header (mapv strip-bom (first rows))]
      (->> (rest rows)
           (mapv (fn [row] (zipmap header row)))))))

(defn- file-path [dir fname]
  (str (io/file dir fname)))

;; ---------------------------------------------------------------------------
;; Match builder
;; ---------------------------------------------------------------------------

(defn- match-record
  [{:keys [competition season round stage date home away
           home-goals away-goals source stats]}]
  {:competition competition
   :season      (n/->int season)
   :round       (n/blank->nil round)
   :stage       (n/blank->nil stage)
   :date        (n/iso-date date)
   :home        (n/display-name home)
   :away        (n/display-name away)
   :home-key    (n/team-key home)
   :away-key    (n/team-key away)
   :home-goals  (n/->int home-goals)
   :away-goals  (n/->int away-goals)
   :source      source
   :stats       (or stats {})})

(defn- load-brasileirao [dir]
  (->> (read-csv-maps (file-path dir "Brasileirao_Matches.csv"))
       (mapv (fn [m]
               (match-record
                {:competition "Brasileirão Série A"
                 :season (m "season") :round (m "round") :date (m "datetime")
                 :home (m "home_team") :away (m "away_team")
                 :home-goals (m "home_goal") :away-goals (m "away_goal")
                 :source :brasileirao})))))

(defn- load-novo [dir]
  (->> (read-csv-maps (file-path dir "novo_campeonato_brasileiro.csv"))
       (mapv (fn [m]
               (match-record
                {:competition "Brasileirão Série A"
                 :season (m "Ano") :round (m "Rodada") :date (m "Data")
                 :home (m "Equipe_mandante") :away (m "Equipe_visitante")
                 :home-goals (m "Gols_mandante") :away-goals (m "Gols_visitante")
                 :source :novo
                 :stats (let [arena (n/blank->nil (m "Arena"))]
                          (cond-> {} arena (assoc :arena arena)))})))))

(defn- load-cup [dir]
  (->> (read-csv-maps (file-path dir "Brazilian_Cup_Matches.csv"))
       (mapv (fn [m]
               (match-record
                {:competition "Copa do Brasil"
                 :season (m "season") :round (m "round") :date (m "datetime")
                 :home (m "home_team") :away (m "away_team")
                 :home-goals (m "home_goal") :away-goals (m "away_goal")
                 :source :cup})))))

(defn- load-libertadores [dir]
  (->> (read-csv-maps (file-path dir "Libertadores_Matches.csv"))
       (mapv (fn [m]
               (match-record
                {:competition "Copa Libertadores"
                 :season (m "season") :stage (m "stage") :date (m "datetime")
                 :home (m "home_team") :away (m "away_team")
                 :home-goals (m "home_goal") :away-goals (m "away_goal")
                 :source :libertadores})))))

(def ^:private br-football-competition
  {"Serie A" "Brasileirão Série A"
   "Serie B" "Brasileirão Série B"
   "Serie C" "Brasileirão Série C"
   "Copa do Brasil" "Copa do Brasil"})

(defn- load-br-football [dir]
  (->> (read-csv-maps (file-path dir "BR-Football-Dataset.csv"))
       (mapv (fn [m]
               (let [date (n/iso-date (m "date"))
                     season (when date (Integer/parseInt (subs date 0 4)))]
                 (match-record
                  {:competition (get br-football-competition (m "tournament")
                                     (m "tournament"))
                   :season season :date (m "date")
                   :home (m "home") :away (m "away")
                   :home-goals (m "home_goal") :away-goals (m "away_goal")
                   :source :br-football
                   :stats (->> {:home-corner (n/->int (m "home_corner"))
                                :away-corner (n/->int (m "away_corner"))
                                :home-shots  (n/->int (m "home_shots"))
                                :away-shots  (n/->int (m "away_shots"))
                                :home-attack (n/->int (m "home_attack"))
                                :away-attack (n/->int (m "away_attack"))
                                :ht-result   (n/blank->nil (m "ht_result"))
                                :at-result   (n/blank->nil (m "at_result"))}
                               (remove (comp nil? val))
                               (into {}))}))))))

;; ---------------------------------------------------------------------------
;; Player builder
;; ---------------------------------------------------------------------------

(defn- player-record [m]
  (let [name (n/blank->nil (m "Name"))
        nat  (n/blank->nil (m "Nationality"))
        club (n/blank->nil (m "Club"))]
    {:id          (n/->int (m "ID"))
     :name        name
     :age         (n/->int (m "Age"))
     :nationality nat
     :overall     (n/->int (m "Overall"))
     :potential   (n/->int (m "Potential"))
     :club        club
     :position    (n/blank->nil (m "Position"))
     :jersey      (n/->int (m "Jersey Number"))
     :height      (n/blank->nil (m "Height"))
     :weight      (n/blank->nil (m "Weight"))
     :preferred-foot (n/blank->nil (m "Preferred Foot"))
     :value       (n/blank->nil (m "Value"))
     :name-key        (n/norm-text name)
     :nationality-key (n/norm-text nat)
     :club-key        (n/norm-text club)}))

(defn- load-players [dir]
  (->> (read-csv-maps (file-path dir "fifa_data.csv"))
       (filter #(n/blank->nil (% "Name")))
       (mapv player-record)))

;; ---------------------------------------------------------------------------
;; Public API
;; ---------------------------------------------------------------------------

(defn load-matches
  "Load and concatenate all match records from `dir` (default data/kaggle)."
  ([] (load-matches default-data-dir))
  ([dir]
   (vec (concat (load-brasileirao dir)
                (load-novo dir)
                (load-cup dir)
                (load-libertadores dir)
                (load-br-football dir)))))

(defn load-players-data
  ([] (load-players default-data-dir))
  ([dir] (load-players dir)))
