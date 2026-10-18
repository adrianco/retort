(ns brazilian-soccer-mcp.core-test
  (:require [clojure.test :refer [deftest is testing]] [brazilian-soccer-mcp.core :as sut]))

(def fixture [{:competition "brasileirao" :date "2023-09-03" :season 2023 :home-team "Flamengo-RJ" :away-team "Fluminense-RJ" :home-key "flamengo" :away-key "fluminense" :home-goals 2 :away-goals 1}
              {:competition "brasileirao" :date "2023-09-10" :season 2023 :home-team "Palmeiras-SP" :away-team "Flamengo-RJ" :home-key "palmeiras" :away-key "flamengo" :home-goals 1 :away-goals 1}])
(deftest normalization-and-match-search
  (is (= "sao paulo" (sut/normalize-name "São Paulo-SP")))
  (is (= 2 (count (sut/find-matches fixture {:team "Flamengo"}))))
  (is (= 2 (count (sut/find-matches fixture {:competition "Brasileirão"}))))
  (is (= 1
         (count (sut/find-matches fixture {:team "Flamengo"
                                           :season 2023
                                           :from "2023-09-05"})))))
(deftest statistics
  (let [s (sut/team-statistics fixture "Flamengo" {})]
    (is (= 2 (:played s))) (is (= 1 (:wins s))) (is (= 1 (:draws s))) (is (= 4 (:points s))) (is (= 3 (:goals-for s)))))
(deftest head-to-head-and-aggregate-statistics
  (with-redefs [sut/data (constantly {:matches fixture :players []})]
    (let [h (sut/head-to-head "Flamengo" "Fluminense")
          summary (sut/aggregate-statistics {:competition :brasileirao})]
      (is (= 1 (:team-a-wins h)))
      (is (= 2 (:matches summary)))
      (is (= 2.5 (:average-goals-per-match summary)))
      (is (= 1 (:home-wins summary))))))
(deftest player-search-supports-name-nationality-and-club
  (with-redefs [sut/data (constantly {:matches []
                                       :players [{"Name" "Gabriel Barbosa" "Nationality" "Brazil" "Club" "Flamengo" "Overall" "81" "Position" "ST"}
                                                 {"Name" "Gabriel Martinelli" "Nationality" "Brazil" "Club" "Arsenal" "Overall" "78" "Position" "LW"}]})]
    (is (= ["Gabriel Barbosa"] (mapv #(get % "Name") (sut/search-players {:name "barbosa"}))))
    (is (= ["Gabriel Barbosa"] (mapv #(get % "Name") (sut/search-players {:nationality "Brazil" :club "Flamengo"}))))))
(deftest standings-use-a-single-canonical-season
  (let [table (sut/standings 2019)
        flamengo (first (filter #(= "flamengo" (:team %)) table))]
    (is (= 20 (count table)))
    (is (= {:position 1 :played 38 :wins 28 :draws 6 :losses 4 :points 90}
           (select-keys flamengo [:position :played :wins :draws :losses :points])))))
(deftest json-round-trip
  (is (= {"method" "tools/list" "id" 1.0} (#'sut/json-read "{\"method\":\"tools/list\",\"id\":1}"))))
