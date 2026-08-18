(ns brazilian-soccer-mcp.core-test
  (:require [clojure.test :refer [deftest is testing]] [brazilian-soccer-mcp.core :as sut] [brazilian-soccer-mcp.server :as server]))

(def db {:matches [{:competition "Brasileirão" :date "2023-09-03" :season 2023 :round "22" :home "Flamengo-RJ" :away "Fluminense-RJ" :home-key "flamengo" :away-key "fluminense" :home-goals 2 :away-goals 1}
                  {:competition "Brasileirão" :date "2023-05-28" :season 2023 :round "8" :home "Fluminense" :away "Flamengo" :home-key "fluminense" :away-key "flamengo" :home-goals 0 :away-goals 1}
                  {:competition "Copa do Brasil" :date "2022-04-01" :season 2022 :home "Corinthians" :away "Santos" :home-key "corinthians" :away-key "santos" :home-goals 1 :away-goals 1}]
         :players [{:name "Neymar Jr" :nationality "Brazil" :club "Paris Saint-Germain" :position "LW" :overall 92}
                   {:name "Gabriel Barbosa" :nationality "Brazil" :club "Flamengo" :position "ST" :overall 81}]})

(deftest normalization-and-match-search
  (is (= "sao paulo" (sut/team-key "São Paulo-SP")))
  (is (= 2 (count (sut/search-matches db {:team "Flamengo"}))))
  (is (= 2 (count (sut/search-matches db {:team-a "Flamengo-RJ" :team-b "Fluminense"})))))
(deftest team-and-head-to-head-statistics
  (let [stats (sut/team-stats db {:team "Flamengo" :season 2023 :competition "Brasileirão"})]
    (is (= [2 2 0 0 3 1] ((juxt :matches :wins :draws :losses :goals-for :goals-against) stats)))
    (is (= 100.0 (:win-rate stats))))
  (is (= {:team-a-wins 2 :team-b-wins 0 :draws 0} (select-keys (sut/head-to-head db "Flamengo" "Fluminense" {}) [:team-a-wins :team-b-wins :draws]))))
(deftest player-standings-and-aggregates
  (is (= ["Gabriel Barbosa"] (map :name (sut/search-players db {:club "flamengo"}))))
  (is (= "Flamengo-RJ" (:team (first (sut/standings db {:competition "Brasileirão" :season 2023})))))
  (is (= 2.0 (:average-goals-per-match (sut/dataset-statistics db {:competition "Brasileirão" :season 2023})))))

(deftest standings-use-canonical-team-identities
  (let [variants {:matches [{:competition "Brasileirão" :date "2019-01-01" :season 2019
                             :home "Atletico-PR" :away "Flamengo-RJ"
                             :home-key (sut/team-key "Atletico-PR") :away-key (sut/team-key "Flamengo-RJ")
                             :home-goals 1 :away-goals 0}
                            {:competition "Brasileirão" :date "2019-01-08" :season 2019
                             :home "Flamengo" :away "Athletico-PR"
                             :home-key (sut/team-key "Flamengo") :away-key (sut/team-key "Athletico-PR")
                             :home-goals 0 :away-goals 2}]}
        table (sut/standings variants {:competition "Brasileirão" :season 2019})
        atletico (first (filter #(= "atletico pr" (:team-key %)) table))]
    (is (= "atletico pr" (sut/team-key "Athletico-PR")))
    (is (= 2 (count table)))
    (is (= [2 2 6] ((juxt :played :wins :points) atletico)))))
(deftest mcp-protocol
  (is (= 6 (count (get-in (server/handle db {"id" 1 "method" "tools/list"}) ["result" "tools"]))))
  (is (= 2 (count (get-in (server/handle db {"id" 2 "method" "tools/call" "params" {"name" "search_matches" "arguments" {"team" "Flamengo"}}}) ["result" :structuredContent])))))

(deftest supplied-corpus-is-queryable
  (let [loaded (sut/load-data)]
    (testing "all five match datasets and the FIFA player dataset load"
      (is (= 23954 (count (:matches loaded))))
      (is (= 18207 (count (:players loaded)))))
    (testing "a cross-file team query and a player query return real data"
      (is (pos? (count (sut/search-matches loaded {:team "Flamengo" :season 2023 :limit 1000}))))
      (is (pos? (count (sut/search-players loaded {:nationality "Brazil" :limit 1000})))))
    (testing "2019 standings merge supplied-name variants into the 20 Serie A clubs"
      (let [table (sut/standings loaded {:competition "Brasileirão" :season 2019})
            flamengo (first table)]
        (is (= 20 (count table)))
        (is (= ["flamengo" 38 90] ((juxt :team-key :played :points) flamengo)))))))
