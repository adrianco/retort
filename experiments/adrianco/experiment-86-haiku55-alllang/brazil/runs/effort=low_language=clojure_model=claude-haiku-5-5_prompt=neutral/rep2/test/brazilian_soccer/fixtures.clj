(ns brazilian-soccer.fixtures
  "Small hand-checked dataset for exact-value tests, plus a lazily loaded
  copy of the real data for smoke tests."
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.names :as names]))

(defn- match [competition date round home home-goals away away-goals]
  {:date date
   :season (parse-long (subs date 0 4))
   :competition competition
   :round round
   :home (names/base-name home)
   :away (names/base-name away)
   :home-key (names/team-key home)
   :away-key (names/team-key away)
   :home-goals home-goals
   :away-goals away-goals
   :source "fixture"})

(def matches
  [(match "Brasileirão" "2023-09-03" "22" "Flamengo-RJ" 2 "Fluminense-RJ" 1)
   (match "Brasileirão" "2023-05-28" "8" "Fluminense-RJ" 1 "Flamengo-RJ" 0)
   (match "Copa do Brasil" "2022-06-01" "final" "Palmeiras-SP" 3 "Santos-SP" 0)
   (match "Libertadores" "2023-03-10" "group stage" "Palmeiras-SP" 2 "Flamengo-RJ" 2)])

(def players
  [{:id "1" :name "Neymar Jr" :age 31 :nationality "Brazil" :overall 92
    :potential 92 :club "Paris Saint-Germain" :position "LW" :jersey-number 10}
   {:id "2" :name "Alisson" :age 29 :nationality "Brazil" :overall 89
    :potential 89 :club "Liverpool" :position "GK" :jersey-number 1}
   {:id "3" :name "Gabriel Barbosa" :age 22 :nationality "Brazil" :overall 76
    :potential 80 :club "Flamengo" :position "ST" :jersey-number 9}
   {:id "4" :name "L. Messi" :age 31 :nationality "Argentina" :overall 94
    :potential 94 :club "FC Barcelona" :position "RF" :jersey-number 10}])

(def real
  (delay (data/load-all "data/kaggle")))
