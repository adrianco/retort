(ns brazilian-soccer-mcp.core-test (:require [clojure.test :refer [deftest is testing]] [brazilian-soccer-mcp.core :as soccer]))
(def fixtures [{:date "2023-09-03" :season 2023 :competition "Brasileirão" :home-team "Flamengo-RJ" :away-team "Fluminense-RJ" :home-key "flamengo" :away-key "fluminense" :home-goals 2 :away-goals 1}
 {:date "2023-05-28" :season 2023 :competition "Brasileirão" :home-team "Fluminense" :away-team "Flamengo" :home-key "fluminense" :away-key "flamengo" :home-goals 1 :away-goals 0}
 {:date "2022-01-01" :season 2022 :competition "Copa do Brasil" :home-team "Palmeiras" :away-team "Santos" :home-key "palmeiras" :away-key "santos" :home-goals 0 :away-goals 0}])
(deftest normalization-and-match-query-scenarios
 (testing "Given variant team names, when a user searches Flamengo vs Fluminense, matching games are returned"
  (is (= "sao paulo" (soccer/canonical-name "São Paulo FC")))
  (is (= 2 (count (soccer/search-matches fixtures {:team "Flamengo" :opponent "Fluminense"}))))))
(deftest team-and-head-to-head-scenarios
 (let [stats (soccer/team-statistics fixtures "Flamengo" {:season 2023}) h2h (soccer/head-to-head fixtures "Flamengo" "Fluminense" {})]
  (is (= [1 0 1 2 2] ((juxt :wins :draws :losses :goals-for :goals-against) stats)))
  (is (= [2 1 1 0] ((juxt :matches :team-a-wins :team-b-wins :draws) h2h)))))
(deftest player-and-competition-scenarios
 (let [players [{:name "Neymar Jr" :nationality "Brazil" :club "PSG" :position "LW" :overall 92} {:name "Other" :nationality "Brazil" :overall 70}]]
  (is (= ["Neymar Jr"] (map :name (soccer/search-players players {:name "neymar"}))))
  (is (= 2.0 (:average-goals-per-match (soccer/competition-statistics fixtures {:competition "Brasileirão" :season 2023}))))))
