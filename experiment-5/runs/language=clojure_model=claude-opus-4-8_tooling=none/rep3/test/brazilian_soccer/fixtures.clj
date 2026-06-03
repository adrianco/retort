;; =============================================================================
;; brazilian-soccer.fixtures
;; -----------------------------------------------------------------------------
;; Small, hand-built match/player fixtures shared by the test suite, plus a
;; helper to build normalised match maps the same way data.clj does. Keeps the
;; query/tool tests deterministic and disk-free.
;; =============================================================================
(ns brazilian-soccer.fixtures
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.normalize :as norm]))

(defn match
  "Build a normalised fixture match (delegates to data/->match for parity)."
  [competition date season round home away hg ag]
  (data/->match {:competition competition :source "fixture"
                 :date date :season season :round round
                 :home-raw home :away-raw away :hg hg :ag ag}))

;; A tiny two-season Brasileirão-style league plus a couple of cup/derby games.
(def matches
  [;; --- 2019 Brasileirão mini-table: Flamengo dominant ---
   (match "Brasileirão Série A" "2019-09-03" 2019 "22" "Flamengo-RJ" "Fluminense-RJ" 2 1)
   (match "Brasileirão Série A" "2019-05-28" 2019 "8"  "Fluminense-RJ" "Flamengo-RJ" 1 0)
   (match "Brasileirão Série A" "2019-10-27" 2019 "30" "Flamengo-RJ" "Grêmio-RS" 5 0)
   (match "Brasileirão Série A" "2019-07-14" 2019 "12" "Palmeiras-SP" "Flamengo-RJ" 1 3)
   (match "Brasileirão Série A" "2019-08-01" 2019 "15" "Santos-SP" "Palmeiras-SP" 0 0)
   (match "Brasileirão Série A" "2019-06-10" 2019 "10" "Palmeiras-SP" "Santos-SP" 2 1)
   (match "Brasileirão Série A" "2019-09-20" 2019 "24" "Fluminense-RJ" "Santos-SP" 1 1)

   ;; --- 2018 Brasileirão sample ---
   (match "Brasileirão Série A" "2018-09-03" 2018 "22" "Palmeiras-SP" "Santos-SP" 3 0)
   (match "Brasileirão Série A" "2018-05-28" 2018 "8"  "Flamengo-RJ" "Palmeiras-SP" 1 1)

   ;; --- Copa do Brasil & Libertadores cross-competition ---
   (match "Copa do Brasil" "2019-09-24" 2019 "Final" "São Paulo" "Flamengo" 1 1)
   (match "Copa Libertadores" "2012-05-27" 2012 "knockout" "Santos-SP" "Bolivar" 8 0)])

(def players
  [{:id 1 :name "Neymar Jr"   :age 27 :nationality "Brazil"    :overall 92 :potential 92 :club "Paris Saint-Germain" :position "LW"}
   {:id 2 :name "Alisson"     :age 26 :nationality "Brazil"    :overall 89 :potential 91 :club "Liverpool"           :position "GK"}
   {:id 3 :name "Casemiro"    :age 27 :nationality "Brazil"    :overall 89 :potential 90 :club "Real Madrid"         :position "CDM"}
   {:id 4 :name "Gabriel Barbosa" :age 22 :nationality "Brazil" :overall 80 :potential 87 :club "Flamengo"          :position "ST"}
   {:id 5 :name "Bruno Henrique" :age 28 :nationality "Brazil"  :overall 78 :potential 80 :club "Flamengo"          :position "LW"}
   {:id 6 :name "L. Messi"    :age 31 :nationality "Argentina" :overall 94 :potential 94 :club "FC Barcelona"       :position "RF"}
   {:id 7 :name "Dani Alves"  :age 36 :nationality "Brazil"    :overall 82 :potential 82 :club "São Paulo"          :position "RB"}]
  )

;; Players need the derived match-keys that data.clj computes; build them.
(def players*
  (mapv (fn [p]
          (assoc p
                 :name-key (norm/match-key (:name p))
                 :club-key (norm/match-key (:club p))
                 :nat-key  (norm/match-key (:nationality p))))
        players))
