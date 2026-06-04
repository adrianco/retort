;; =============================================================================
;; brazilian-soccer.knowledge-graph
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   Builds and holds the in-memory knowledge graph that the query layer and the
;;   MCP server operate on. Nodes are Teams, Players and Competitions; edges are
;;   the Matches that connect two teams within a competition/season.
;;
;;   The graph is plain Clojure data (no external database required) with a few
;;   indexes pre-computed for fast lookup so simple queries answer in well under
;;   the 2s budget and aggregates well under 5s.
;;
;; CROSS-SOURCE DE-DUPLICATION
;;   The same real match can appear in several files (e.g. Brasileirão Série A
;;   2015 is in both Brasileirao_Matches.csv and novo_campeonato_brasileiro.csv,
;;   and again in BR-Football-Dataset.csv). Matches are de-duplicated on
;;   [competition home-key away-key date]; when duplicates are merged we keep the
;;   richest record (the one carrying extended :stats) and union the source set.
;;
;; GRAPH SHAPE
;;   {:matches      [match ...]                 ; de-duplicated edges
;;    :players      [player ...]
;;    :teams        {team-key {:name :matches [idx ...] :competitions #{} :seasons #{}}}
;;    :competitions {comp-name {:seasons #{} :teams #{} :match-count n}}
;;    :by-team      {team-key [match ...]}       ; convenience index
;;    :players-by-club        {club-key [player ...]}
;;    :players-by-nationality {nat-key  [player ...]}}
;; =============================================================================
(ns brazilian-soccer.knowledge-graph
  (:require [brazilian-soccer.data-loader :as loader]
            [clojure.string :as str]))

(defn- dedup-key [m]
  [(:competition m) (:home-key m) (:away-key m) (:date m)])

(defn- richness [m]
  ;; prefer the record with more known information when merging duplicates
  (+ (count (:stats m))
     (if (:home-goals m) 1 0)
     (if (:away-goals m) 1 0)
     (if (:round m) 1 0)
     (if (:stage m) 1 0)))

(defn- merge-dupes [a b]
  (let [[rich poor] (if (>= (richness a) (richness b)) [a b] [b a])]
    (-> rich
        (update :stats merge (:stats poor))
        (assoc :sources (into (or (:sources a) #{(:source a)})
                              (or (:sources b) #{(:source b)}))))))

(defn dedup-matches
  "Collapse matches that describe the same real fixture (same competition,
   teams and date). Records lacking a date are never merged (we can't be sure
   they are the same fixture). Returns a vector."
  [matches]
  (let [{:keys [keyed unkeyed]}
        (reduce (fn [acc m]
                  (if (and (:date m) (:home-key m) (:away-key m))
                    (update acc :keyed
                            (fn [mp]
                              (let [k (dedup-key m)]
                                (if-let [ex (get mp k)]
                                  (assoc mp k (merge-dupes ex m))
                                  (assoc mp k (assoc m :sources #{(:source m)}))))))
                    (update acc :unkeyed conj (assoc m :sources #{(:source m)}))))
                {:keyed {} :unkeyed []}
                matches)]
    (vec (concat (vals keyed) unkeyed))))

(defn- index-teams [matches]
  (reduce
   (fn [acc m]
     (let [add (fn [acc team-key name]
                 (if (nil? team-key)
                   acc
                   (-> acc
                       (update-in [team-key :name] #(or % name))
                       (update-in [team-key :competitions] (fnil conj #{}) (:competition m))
                       (update-in [team-key :seasons] (fnil conj #{}) (:season m)))))]
       (-> acc
           (add (:home-key m) (:home m))
           (add (:away-key m) (:away m)))))
   {}
   matches))

(defn- index-competitions [matches]
  (reduce
   (fn [acc m]
     (-> acc
         (update-in [(:competition m) :seasons] (fnil conj #{}) (:season m))
         (update-in [(:competition m) :teams] (fnil into #{})
                    (remove nil? [(:home-key m) (:away-key m)]))
         (update-in [(:competition m) :match-count] (fnil inc 0))))
   {}
   matches))

(defn- group-by-multi
  "group-by where each match contributes to several keys."
  [key-fns matches]
  (reduce (fn [acc m]
            (reduce (fn [a k] (if k (update a k (fnil conj []) m) a))
                    acc (key-fns m)))
          {} matches))

(defn build-graph
  "Build the knowledge graph from already-loaded match & player seqs."
  [matches players]
  (let [matches (dedup-matches matches)]
    {:matches      matches
     :players      players
     :teams        (index-teams matches)
     :competitions (index-competitions matches)
     :by-team      (group-by-multi (juxt :home-key :away-key) matches)
     :players-by-club        (group-by :club-key players)
     :players-by-nationality (group-by :nationality-key players)}))

(defn load-graph
  "Load CSVs from `dir` (default data/kaggle) and build the knowledge graph."
  ([] (load-graph loader/default-data-dir))
  ([dir]
   (build-graph (loader/load-matches dir)
                (loader/load-players-data dir))))

;; ---------------------------------------------------------------------------
;; A process-wide cached graph for the MCP server (loaded once at startup).
;; ---------------------------------------------------------------------------
(defonce ^:private graph-atom (atom nil))

(defn graph
  "Return the cached graph, building it on first use."
  ([] (graph loader/default-data-dir))
  ([dir]
   (or @graph-atom
       (reset! graph-atom (load-graph dir)))))

(defn set-graph! [g] (reset! graph-atom g))

(defn stats-summary
  "Small map describing graph size — handy for diagnostics / the MCP banner."
  [g]
  {:matches      (count (:matches g))
   :players      (count (:players g))
   :teams        (count (:teams g))
   :competitions (count (:competitions g))
   :competition-names (sort (keys (:competitions g)))})
