(ns brazilian-soccer-mcp.players
  (:require [clojure.string :as str]
            [brazilian-soccer-mcp.normalization :as norm]))

(defn- ci-contains? [s query]
  (when (and s query)
    (str/includes? (str/lower-case s) (str/lower-case query))))

(defn find-players
  "Filter players by criteria map.
   Keys: :name, :nationality, :club, :position, :sort-by, :limit"
  [players {:keys [name nationality club position sort-by limit]}]
  (let [sorted-key sort-by]
    (cond->> players
      name        (filter #(ci-contains? (:name %) name))
      nationality (filter #(ci-contains? (:nationality %) nationality))
      club        (filter #(ci-contains? (:club %) club))
      position    (filter #(= (str/upper-case (or (:position %) ""))
                               (str/upper-case position)))
      sorted-key  (clojure.core/sort-by (fn [p] (- (or (get p sorted-key) 0))))
      limit       (take limit)
      true        vec)))

(defn top-players-by-club
  "Returns top n players (by overall rating) for each club in clubs list."
  [players clubs n]
  (into {}
        (for [club clubs]
          (let [club-players (->> players
                                  (filter #(ci-contains? (:club %) club))
                                  (sort-by (comp - #(or (:overall %) 0)))
                                  (take n)
                                  vec)]
            [club club-players]))))
