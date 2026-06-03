;; =============================================================================
;; brazilian-soccer.fixtures
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   Test support for the Brazilian Soccer MCP server. Provides a small, fully
;;   deterministic set of match and player maps (matching the uniform shapes
;;   produced by brazilian-soccer.data) so that query logic can be asserted
;;   exactly, independent of the large real CSV datasets.
;; =============================================================================
(ns brazilian-soccer.fixtures
  (:require [brazilian-soccer.data :as data]))

(defn mk-match
  [competition season date home away hg ag & [extra]]
  (merge
   {:competition competition :season season :date date
    :round nil :stage nil
    :home (data/clean-name home) :away (data/clean-name away)
    :home-raw home :away-raw away
    :home-key (data/team-key home) :away-key (data/team-key away)
    :home-goal hg :away-goal ag :source "fixture"}
   extra))

;; A tiny 3-team round-robin-ish Brasileirão season plus a couple of other
;; competitions, designed so standings/head-to-head/stats are hand-verifiable.
(def matches
  [;; --- 2019 Brasileirão ---
   (mk-match "Brasileirão Série A" 2019 "2019-05-01" "Flamengo" "Palmeiras" 3 0 {:round "1"})
   (mk-match "Brasileirão Série A" 2019 "2019-06-01" "Palmeiras" "Flamengo" 1 1 {:round "2"})
   (mk-match "Brasileirão Série A" 2019 "2019-07-01" "Flamengo" "Santos"    5 0 {:round "3"})
   (mk-match "Brasileirão Série A" 2019 "2019-08-01" "Santos"   "Flamengo"  0 2 {:round "4"})
   (mk-match "Brasileirão Série A" 2019 "2019-09-01" "Palmeiras" "Santos"   2 1 {:round "5"})
   (mk-match "Brasileirão Série A" 2019 "2019-10-01" "Santos"   "Palmeiras" 0 0 {:round "6"})
   ;; --- 2018 Brasileirão (different winner) ---
   (mk-match "Brasileirão Série A" 2018 "2018-05-01" "Palmeiras" "Flamengo" 2 0 {:round "1"})
   ;; --- Copa do Brasil ---
   (mk-match "Copa do Brasil" 2019 "2019-05-15" "Flamengo" "Grêmio" 2 1 {:round "Final"})
   ;; --- Libertadores (accent + country code teams) ---
   (mk-match "Copa Libertadores" 2019 "2019-11-23" "Flamengo" "River Plate (ARG)" 2 1
             {:stage "final"})])

(def players
  [{:id 1 :name "Neymar Jr"       :age 27 :nationality "Brazil"    :overall 92 :potential 92 :club "Paris Saint-Germain" :position "LW" :jersey 10}
   {:id 2 :name "Gabriel Barbosa" :age 23 :nationality "Brazil"    :overall 80 :potential 86 :club "Flamengo"            :position "ST" :jersey 9}
   {:id 3 :name "Bruno Henrique"  :age 28 :nationality "Brazil"    :overall 78 :potential 79 :club "Flamengo"            :position "LM" :jersey 27}
   {:id 4 :name "Lionel Messi"    :age 31 :nationality "Argentina" :overall 94 :potential 94 :club "FC Barcelona"        :position "RF" :jersey 10}
   {:id 5 :name "Dudu"            :age 27 :nationality "Brazil"    :overall 79 :potential 80 :club "Palmeiras"           :position "RM" :jersey 7}])
