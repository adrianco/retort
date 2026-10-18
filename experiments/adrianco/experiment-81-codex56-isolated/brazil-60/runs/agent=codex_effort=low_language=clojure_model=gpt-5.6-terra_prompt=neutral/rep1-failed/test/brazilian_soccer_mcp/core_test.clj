(ns brazilian-soccer-mcp.core-test
  (:require [clojure.test :refer [deftest is testing]] [brazilian-soccer-mcp.core :as sut]))

(def fixture [{:competition "brasileirao" :date "2023-09-03" :season 2023 :home-team "Flamengo-RJ" :away-team "Fluminense-RJ" :home-key "flamengo" :away-key "fluminense" :home-goals 2 :away-goals 1}
              {:competition "brasileirao" :date "2023-09-10" :season 2023 :home-team "Palmeiras-SP" :away-team "Flamengo-RJ" :home-key "palmeiras" :away-key "flamengo" :home-goals 1 :away-goals 1}])
(deftest normalization-and-match-search
  (is (= "sao paulo" (sut/normalize-name "São Paulo-SP")))
  (is (= 2 (count (sut/find-matches fixture {:team "Flamengo"}))))
  (is (= 1
         (count (sut/find-matches fixture {:team "Flamengo"
                                           :season 2023
                                           :from "2023-09-05"})))))
(deftest statistics
  (let [s (sut/team-statistics fixture "Flamengo" {})]
    (is (= 2 (:played s))) (is (= 1 (:wins s))) (is (= 1 (:draws s))) (is (= 4 (:points s))) (is (= 3 (:goals-for s)))))
(deftest json-round-trip
  (is (= {"method" "tools/list" "id" 1.0} (#'sut/json-read "{\"method\":\"tools/list\",\"id\":1}"))))
