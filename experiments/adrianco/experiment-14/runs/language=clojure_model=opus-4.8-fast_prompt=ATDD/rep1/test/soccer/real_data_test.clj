(ns soccer.real-data-test
  "Coverage acceptance tests against the *real* provided Kaggle datasets in
   data/kaggle.  These confirm that all six CSV files are loadable and
   queryable through the MCP protocol, and that well-known real facts come
   back correctly (e.g. Flamengo won the 2019 Brasileirão)."
  (:require [clojure.test :refer [deftest testing is]]
            [clojure.string :as str]
            [soccer.test-helpers :as h]))

(def data-dir "data/kaggle")

(deftest all-datasets-load-and-answer-queries
  (testing "the real datasets back a working set of MCP tools"
    (let [srv (h/new-server data-dir)]

      (testing "player lookup across the FIFA database"
        (let [ans (h/call-tool srv "search_players" {:name "Neymar"})]
          (is (str/includes? ans "Neymar"))))

      (testing "a famous derby is found in the match data"
        (let [ans (h/call-tool srv "find_matches"
                               {:team "Flamengo" :opponent "Fluminense"})]
          (is (str/includes? ans "Flamengo"))
          (is (str/includes? ans "Fluminense"))))

      (testing "2019 Brasileirão champion is Flamengo"
        (let [ans (h/call-tool srv "competition_standings"
                               {:competition "Brasileirão" :season 2019})]
          (is (re-find #"(?m)^\s*1\.\s+Flamengo" ans))))

      (testing "Brazilian players can be filtered by nationality"
        (let [ans (h/call-tool srv "search_players"
                               {:nationality "Brazil" :limit 5})]
          (is (str/includes? ans "Brazil"))))

      (testing "aggregate statistics are computed without error"
        (let [ans (h/call-tool srv "competition_stats" {:competition "Brasileirão"})]
          (is (re-find #"\d\.\d" ans)))))))
