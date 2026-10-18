(ns brazil-soccer.support
  "Shared fixtures: the real datasets (loaded once, on first use) and a tiny hand-built
  database whose query results can be worked out by hand."
  (:require [brazil-soccer.data :as data])
  (:import [java.time LocalDate]))

(def real-db
  "The full database loaded from data/kaggle."
  (delay (data/load-db data/default-data-dir)))

(defn- match [date competition home away home-goals away-goals & {:keys [round stage]}]
  (let [d (LocalDate/parse date)]
    {:date d :season (.getYear d) :competition competition :round round :stage stage
     :home home :away away :home-goals home-goals :away-goals away-goals}))

(def small-db
  "Four matches in the 2020 Serie A, one 2019 match, and a two-round Copa do Brasil."
  {:matches
   [(match "2020-03-01" :serie-a "flamengo" "fluminense" 2 1 :round 1)
    (match "2020-03-08" :serie-a "fluminense" "flamengo" 0 0 :round 2)
    (match "2020-03-15" :serie-a "palmeiras" "flamengo" 1 0 :round 3)
    (match "2020-03-22" :serie-a "flamengo" "palmeiras" 3 3 :round 4)
    (match "2020-03-29" :copa-do-brasil "flamengo" "santos" 1 0 :round 1)
    (match "2020-04-05" :copa-do-brasil "santos" "flamengo" 2 2 :round 2)
    (match "2019-05-01" :serie-a "flamengo" "fluminense" 1 0 :round 1)]
   :players
   [{:name "Gabriel Jesus" :nationality "Brazil" :club "Manchester City" :club-key "manchester city"
     :overall 83 :potential 88 :position "ST" :age 21}
    {:name "Alisson" :nationality "Brazil" :club "Liverpool" :club-key "liverpool"
     :overall 89 :potential 90 :position "GK" :age 26}
    {:name "Lucas Paqueta" :nationality "Brazil" :club "Flamengo" :club-key "flamengo"
     :overall 78 :potential 84 :position "CAM" :age 21}
    {:name "Diego Ribas" :nationality "Brazil" :club "Flamengo" :club-key "flamengo"
     :overall 80 :potential 80 :position "CAM" :age 33}
    {:name "Lionel Messi" :nationality "Argentina" :club "FC Barcelona" :club-key "fc barcelona"
     :overall 94 :potential 94 :position "RW" :age 31}]})
