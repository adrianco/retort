(ns brazilian-soccer.format-test
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.format :as fmt])
  (:import [java.time LocalDate]))

(def sample-matches
  [{:competition "Brasileirão" :season 2019 :round "20"
    :date (LocalDate/of 2019 9 3)
    :home-team "Flamengo" :away-team "Grêmio" :home-goal 5 :away-goal 0}
   {:competition "Brasileirão" :season 2019 :round "1"
    :date (LocalDate/of 2019 5 19)
    :home-team "Flamengo" :away-team "Santos" :home-goal 2 :away-goal 0}])

(deftest format-matches-test
  (testing "renders one line per match with date, score and competition"
    (let [s (fmt/matches sample-matches)]
      (is (re-find #"2019-09-03: Flamengo 5-0 Grêmio \(Brasileirão Round 20\)" s))
      (is (re-find #"2019-05-19: Flamengo 2-0 Santos" s))))
  (testing "reports when there are no matches"
    (is (re-find #"(?i)no matches" (fmt/matches [])))))

(deftest format-head-to-head-test
  (testing "summarizes the head-to-head tally"
    (let [s (fmt/head-to-head {:team-a "Flamengo" :team-b "Santos" :total 2
                               :team-a-wins 1 :team-b-wins 0 :draws 1
                               :team-a-goals 3 :team-b-goals 1})]
      (is (re-find #"Flamengo" s))
      (is (re-find #"Santos" s))
      (is (re-find #"1 win" s))
      (is (re-find #"1 draw" s)))))

(deftest format-team-record-test
  (testing "renders a readable record block"
    (let [s (fmt/team-record {:team "Flamengo" :matches 3 :wins 2 :draws 1
                              :losses 0 :goals-for 8 :goals-against 1
                              :points 7 :win-rate 66.7})]
      (is (re-find #"Matches: 3" s))
      (is (re-find #"Wins: 2" s))
      (is (re-find #"66.7%" s)))))

(deftest format-standings-test
  (testing "renders a numbered league table"
    (let [s (fmt/standings "Brasileirão" 2019
                           [{:team "Flamengo" :points 7 :wins 2 :draws 1 :losses 0
                             :goals-for 8 :goals-against 1 :goal-difference 7 :played 3}
                            {:team "Santos" :points 1 :wins 0 :draws 1 :losses 1
                             :goals-for 1 :goals-against 3 :goal-difference -2 :played 2}])]
      (is (re-find #"2019 Brasileirão" s))
      (is (re-find #"1\. Flamengo - 7 pts" s))
      (is (re-find #"2\. Santos - 1 pts" s)))))

(deftest format-players-test
  (testing "renders a numbered player list with rating, position and club"
    (let [s (fmt/players [{:name "Neymar Jr" :overall 92 :position "LW"
                           :club "Paris Saint-Germain" :nationality "Brazil"}])]
      (is (re-find #"1\. Neymar Jr - Overall: 92, Position: LW" s))
      (is (re-find #"Paris Saint-Germain" s)))))
