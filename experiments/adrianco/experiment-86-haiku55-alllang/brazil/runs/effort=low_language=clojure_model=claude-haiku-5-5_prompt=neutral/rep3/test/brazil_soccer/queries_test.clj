(ns brazil-soccer.queries-test
  (:require [clojure.test :refer [deftest is testing]]
            [brazil-soccer.queries :as q]
            [brazil-soccer.support :refer [real-db small-db]]))

(deftest find_matches_by_team_and_opponent
  (testing "Given the small database, when I search Flamengo vs Fluminense, then I get their three meetings, newest first"
    (let [ms (q/filter-matches small-db {:team "Flamengo" :opponent "Fluminense"})]
      (is (= 3 (count ms)))
      (is (= [2020 2020 2019] (map :season ms)))
      (is (= "2020-03-08" (str (:date (first ms)))))))
  (testing "Given venue home, when I search Flamengo's 2020 games, then only the home ones are returned"
    (let [ms (q/filter-matches small-db {:team "Flamengo" :season 2020 :venue "home"})]
      (is (= 3 (count ms)))
      (is (every? #(= "flamengo" (:home %)) ms)))))

(deftest find_matches_by_date_range
  (testing "Given a date range, when I search, then only matches inside it are returned"
    (let [ms (q/filter-matches small-db {:from "2020-03-10" :to "2020-03-31"})]
      (is (= 3 (count ms))))
    (testing "Given dd/MM/yyyy dates, then they are accepted too"
      (is (= 3 (count (q/filter-matches small-db {:from "10/03/2020" :to "31/03/2020"})))))))

(deftest find_copa_do_brasil_finals
  (testing "Given the Copa do Brasil, when I ask for finals, then only the last round of the season is returned"
    (let [ms (q/filter-matches small-db {:competition "Copa do Brasil" :final-only true})]
      (is (= 1 (count ms)))
      (is (= 2 (:round (first ms)))))))

(deftest team_record_for_a_season
  (testing "Given Flamengo in 2020 Serie A, then the record is 1 win, 2 draws, 1 loss"
    (let [r (q/team-record small-db {:team "Flamengo" :season 2020 :competition "Serie A"})]
      (is (= 4 (:played r)))
      (is (= [1 2 1] [(:wins r) (:draws r) (:losses r)]))
      (is (= [5 5] [(:goals-for r) (:goals-against r)]))
      (is (= 5 (:points r)))
      (is (= 25.0 (:win-rate r)))))
  (testing "Given Flamengo's home games in 2020 Serie A, then only those two count"
    (let [r (q/team-record small-db {:team "Flamengo" :season 2020 :competition "Serie A" :venue "home"})]
      (is (= 2 (:played r)))
      (is (= [1 1 0] [(:wins r) (:draws r) (:losses r)])))))

(deftest head_to_head_record
  (testing "Given Flamengo and Fluminense across all competitions, then Flamengo's record is 2 wins and 1 draw"
    (let [{:keys [record matches]} (q/head-to-head small-db {:team-a "Flamengo" :team-b "Fluminense"})]
      (is (= 3 (count matches)))
      (is (= [2 1 0] [(:wins record) (:draws record) (:losses record)])))))

(deftest standings_are_calculated_from_results
  (testing "Given the 2020 Serie A results, when I ask for the table, then points are 3 for a win and 1 for a draw"
    (let [table (q/standings small-db {:competition "Serie A" :season 2020})]
      (is (= ["flamengo" "palmeiras" "fluminense"] (map :team table)))
      (is (= [5 4 1] (map :points table)))
      (is (= [1 2 3] (map :position table)))))
  (testing "Given a cup competition, when I ask for standings, then I am told it is not a league"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"only available"
                          (q/standings small-db {:competition "Copa do Brasil" :season 2020})))))

(deftest team_rankings_sort_by_a_field
  (testing "Given 2020 Serie A, when ranked by points, then Flamengo leads"
    (let [rows (q/team-rankings small-db {:competition "Serie A" :season 2020})]
      (is (= "flamengo" (:team (first rows))))))
  (testing "Given a snake_case sort field, then it is accepted"
    (let [rows (q/team-rankings small-db {:competition "Serie A" :season 2020 :sort-by "goals_for"})]
      (is (= "flamengo" (:team (first rows))))))
  (testing "Given an unknown sort field, then the error names the allowed fields"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"sort_by must be one of"
                          (q/team-rankings small-db {:competition "Serie A" :sort-by "fame"})))))

(deftest league_summary_aggregates_goals_and_rates
  (testing "Given 2020 Serie A, then there are 4 matches, 10 goals and 2.5 goals per match"
    (let [s (q/league-summary small-db {:competition "Serie A" :season 2020})]
      (is (= 4 (:matches s)))
      (is (= 10 (:goals s)))
      (is (= 2.5 (:goals-per-match s)))
      (is (= 50.0 (:home-win-rate s))))))

(deftest real_data_standings_match_the_published_table
  (testing "Given the real 2019 Brasileirão data, then Flamengo are champions on 90 points"
    (let [table (q/standings @real-db {:competition "Serie A" :season 2019})
          champion (first table)]
      (is (= "flamengo" (:team champion)))
      (is (= 90 (:points champion)))
      (is (= 20 (count table))))))

(deftest player_search_filters_and_sorts
  (testing "Given Brazilian players, when filtered by nationality, then only Brazilians return, best first"
    (let [{:keys [total players]} (q/search-players small-db {:nationality "Brazil"})]
      (is (= 4 total))
      (is (= "Alisson" (:name (first players))))))
  (testing "Given a club filter, then it matches on the club's canonical key"
    (let [{:keys [players]} (q/search-players small-db {:club "Flamengo"})]
      (is (= ["Diego Ribas" "Lucas Paqueta"] (map :name players)))))
  (testing "Given a position group, then forwards are returned"
    (let [{:keys [players]} (q/search-players small-db {:position-group "forward"})]
      (is (= ["Lionel Messi" "Gabriel Jesus"] (map :name players)))))
  (testing "Given a name fragment with accents folded, then the player is found"
    (is (= 1 (:total (q/search-players small-db {:name "paqueta"}))))))

(deftest brazilian_players_grouped_by_club
  (testing "Given the small database, then only Brazilian players at Brazilian clubs are counted"
    (let [rows (q/brazilian-players-by-club small-db {})]
      (is (= [{:club "flamengo" :players 2 :average-overall 79.0}]
             (filter #(= "flamengo" (:club %)) rows)))
      (is (not-any? #(= "liverpool" (:club %)) rows)))))

(deftest real_data_player_queries
  (testing "Given the real FIFA data, when I search Brazilian players at Brazilian clubs, then results exist"
    (is (pos? (count (q/brazilian-players-by-club @real-db {})))))
  (testing "Given Gabriel Jesus by name, then he is found with a rating"
    (let [{:keys [players]} (q/search-players @real-db {:name "Gabriel Jesus"})]
      (is (= "Gabriel Jesus" (:name (first players))))
      (is (pos? (:overall (first players)))))))

(deftest team_profile_combines_both_datasets
  (testing "Given the small database, then the profile has a record per competition"
    (let [p (q/team-profile small-db {:team "Flamengo"})]
      (is (= 7 (:played (:record p))))
      (is (= 2 (:squad-size p)))
      (is (= #{:serie-a :copa-do-brasil}
             (set (map :competition (:by-competition p))))))))

(deftest team_profile_reports_squad_from_fifa
  (testing "Given the real data, when I profile Flamengo, then its squad is looked up in the FIFA file"
    (let [p (q/team-profile @real-db {:team "Flamengo"})]
      (is (pos? (:played (:record p))))
      (is (zero? (:squad-size p))
          "Flamengo is not in the FIFA file, so the squad is empty"))))
