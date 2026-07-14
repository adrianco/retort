(ns brazilian-soccer-mcp.data
  (:require [clojure.data.csv :as csv]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer-mcp.normalize :as norm]))

(def ^:dynamic *data-dir* "data/kaggle/")

(defonce state
  (atom {:loaded? false
         :brasileirao []
         :copa-brasil []
         :libertadores []
         :br-football []
         :historico []
         :fifa []
         :all-matches []}))

(defn header->keyword
  "Convert CSV header string to a normalized keyword."
  [s]
  (let [clean (-> s
                  (str/replace "﻿" "")
                  str/trim
                  (str/replace #"[\s_]+" "-")
                  (str/replace #"[^a-zA-Z0-9-]" "")
                  str/lower-case)]
    (when (seq clean) (keyword clean))))

(defn parse-csv-file
  "Parse a CSV file from the data directory, returning a vector of maps."
  [filename]
  (let [path (str *data-dir* filename)]
    (with-open [reader (io/reader path :encoding "UTF-8")]
      (let [all-rows  (doall (csv/read-csv reader))
            raw-hdrs  (first all-rows)
            headers   (mapv header->keyword raw-hdrs)
            data-rows (rest all-rows)]
        (mapv (fn [row]
                (into {}
                      (keep (fn [[k v]] (when k [k v]))
                            (map vector headers row))))
              data-rows)))))

;; ── Row normalizers ────────────────────────────────────────────────────────────

(defn- norm-brasileirao [row]
  {:date       (norm/parse-date (:datetime row))
   :home-team  (:home-team row)
   :away-team  (:away-team row)
   :home-goals (norm/parse-int (:home-goal row))
   :away-goals (norm/parse-int (:away-goal row))
   :season     (norm/parse-int (:season row))
   :competition :brasileirao
   :round      (:round row)
   :stage      nil})

(defn- norm-copa-brasil [row]
  {:date       (norm/parse-date (:datetime row))
   :home-team  (:home-team row)
   :away-team  (:away-team row)
   :home-goals (norm/parse-int (:home-goal row))
   :away-goals (norm/parse-int (:away-goal row))
   :season     (norm/parse-int (:season row))
   :competition :copa-brasil
   :round      (:round row)
   :stage      nil})

(defn- norm-libertadores [row]
  {:date       (norm/parse-date (:datetime row))
   :home-team  (:home-team row)
   :away-team  (:away-team row)
   :home-goals (norm/parse-int (:home-goal row))
   :away-goals (norm/parse-int (:away-goal row))
   :season     (norm/parse-int (:season row))
   :competition :libertadores
   :round      nil
   :stage      (:stage row)})

(defn- norm-br-football [row]
  (let [date (norm/parse-date (:date row))]
    {:date       date
     :home-team  (:home row)
     :away-team  (:away row)
     :home-goals (norm/parse-int (str (:home-goal row)))
     :away-goals (norm/parse-int (str (:away-goal row)))
     :season     (norm/extract-year date)
     :competition (keyword (-> (or (:tournament row) "unknown")
                               str/lower-case
                               (str/replace #"[^a-z0-9]+" "-")
                               (str/replace #"^-|-$" "")))
     :tournament  (:tournament row)
     :round       nil
     :stage       nil
     :home-corners (norm/parse-double-str (str (:home-corner row)))
     :away-corners (norm/parse-double-str (str (:away-corner row)))
     :home-shots   (norm/parse-double-str (str (:home-shots row)))
     :away-shots   (norm/parse-double-str (str (:away-shots row)))}))

(defn- norm-historico [row]
  {:date       (norm/parse-date (:data row))
   :home-team  (:equipe-mandante row)
   :away-team  (:equipe-visitante row)
   :home-goals (norm/parse-int (:gols-mandante row))
   :away-goals (norm/parse-int (:gols-visitante row))
   :season     (norm/parse-int (:ano row))
   :competition :brasileirao-historico
   :round      (:rodada row)
   :stage      nil
   :arena      (:arena row)})

(defn- norm-fifa [row]
  {:id           (:id row)
   :name         (:name row)
   :age          (norm/parse-int (:age row))
   :nationality  (:nationality row)
   :overall      (norm/parse-int (:overall row))
   :potential    (norm/parse-int (:potential row))
   :club         (:club row)
   :position     (:position row)
   :jersey-number (:jersey-number row)
   :height       (:height row)
   :weight       (:weight row)
   :value        (:value row)
   :wage         (:wage row)})

;; ── Public API ─────────────────────────────────────────────────────────────────

(defn load-all-data!
  "Load all CSV datasets into memory. Idempotent."
  []
  (when-not (:loaded? @state)
    (let [brasileirao (mapv norm-brasileirao (parse-csv-file "Brasileirao_Matches.csv"))
          copa-brasil (mapv norm-copa-brasil  (parse-csv-file "Brazilian_Cup_Matches.csv"))
          libertadores (mapv norm-libertadores (parse-csv-file "Libertadores_Matches.csv"))
          br-football  (mapv norm-br-football  (parse-csv-file "BR-Football-Dataset.csv"))
          historico    (mapv norm-historico     (parse-csv-file "novo_campeonato_brasileiro.csv"))
          fifa         (mapv norm-fifa          (parse-csv-file "fifa_data.csv"))
          all-matches  (vec (concat brasileirao copa-brasil libertadores br-football historico))]
      (reset! state {:loaded?     true
                     :brasileirao brasileirao
                     :copa-brasil copa-brasil
                     :libertadores libertadores
                     :br-football br-football
                     :historico   historico
                     :fifa        fifa
                     :all-matches all-matches}))))

(defn get-brasileirao  [] (:brasileirao  @state))
(defn get-copa-brasil  [] (:copa-brasil  @state))
(defn get-libertadores [] (:libertadores @state))
(defn get-br-football  [] (:br-football  @state))
(defn get-historico    [] (:historico    @state))
(defn get-fifa         [] (:fifa         @state))
(defn get-all-matches  [] (:all-matches  @state))

(defn matches-for-competition
  "Return matches for a given competition keyword, or all matches."
  [comp-key]
  (case comp-key
    :brasileirao    (get-brasileirao)
    :copa-brasil    (get-copa-brasil)
    :libertadores   (get-libertadores)
    :br-football    (get-br-football)
    :historico      (get-historico)
    :brasileirao-historico (get-historico)
    (get-all-matches)))
