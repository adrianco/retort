(ns soccer.fixtures
  "=============================================================================
   soccer.fixtures — Small hand-built dataset for fast, deterministic tests
   -----------------------------------------------------------------------------
   The BDD scenarios in the *_test namespaces run against this fixture rather
   than the full CSV files so they are fast and assertion values are known
   exactly. The fixture mirrors the unified shapes produced by soccer.data.
   ============================================================================="
  (:require [soccer.normalize :as n]))

(defn- m [competition season round date home away hg ag]
  {:competition competition :season season :round round :date (n/norm-date date)
   :stage nil
   :home (n/display-name home) :away (n/display-name away)
   :home-key (n/team-key home) :away-key (n/team-key away)
   :home-goal hg :away-goal ag :stats nil :source "fixture"})

(def matches
  [;; Brasileirão 2019 — a tiny 3-team round robin (home & away)
   (m "Brasileirão Série A" 2019 "1" "2019-04-28" "Flamengo" "Palmeiras" 3 1)
   (m "Brasileirão Série A" 2019 "2" "2019-05-05" "Palmeiras" "Flamengo" 0 2)
   (m "Brasileirão Série A" 2019 "3" "2019-05-12" "Flamengo" "Santos" 4 0)
   (m "Brasileirão Série A" 2019 "4" "2019-05-19" "Santos" "Flamengo" 1 1)
   (m "Brasileirão Série A" 2019 "5" "2019-05-26" "Palmeiras" "Santos" 2 2)
   (m "Brasileirão Série A" 2019 "6" "2019-06-02" "Santos" "Palmeiras" 0 1)
   ;; A different season for the same teams
   (m "Brasileirão Série A" 2018 "1" "2018-04-28" "Flamengo" "Palmeiras" 0 1)
   ;; Fla-Flu derby across competitions
   (m "Brasileirão Série A" 2019 "7" "2019-09-03" "Flamengo" "Fluminense" 2 1)
   (m "Copa do Brasil"      2019 "Quarterfinals" "2019-07-10" "Fluminense" "Flamengo" 1 0)
   ;; Libertadores blowout for biggest-wins
   (m "Copa Libertadores"   2012 nil "2012-05-27" "Santos" "Bolivar" 8 0)])

(def players
  [{:id 1 :name "Neymar Jr" :age 27 :nationality "Brazil" :overall 92 :potential 92
    :club "Paris Saint-Germain" :position "LW" :jersey 10 :skills {}}
   {:id 2 :name "Gabriel Barbosa" :age 22 :nationality "Brazil" :overall 80 :potential 86
    :club "Flamengo" :position "ST" :jersey 9 :skills {}}
   {:id 3 :name "Bruno Henrique" :age 28 :nationality "Brazil" :overall 78 :potential 78
    :club "Flamengo" :position "LW" :jersey 27 :skills {}}
   {:id 4 :name "Diego Alves" :age 33 :nationality "Brazil" :overall 79 :potential 79
    :club "Flamengo" :position "GK" :jersey 1 :skills {}}
   {:id 5 :name "L. Messi" :age 31 :nationality "Argentina" :overall 94 :potential 94
    :club "FC Barcelona" :position "RF" :jersey 10 :skills {}}])

(def db {:matches matches :players players})
