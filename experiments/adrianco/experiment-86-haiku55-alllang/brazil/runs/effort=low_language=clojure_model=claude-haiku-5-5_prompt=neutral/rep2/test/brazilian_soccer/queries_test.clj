(ns brazilian-soccer.queries-test
  (:require [brazilian-soccer.fixtures :as fx]
            [brazilian-soccer.queries :as q]
            [clojure.test :refer [deftest is testing]]))

(def ms fx/matches)

(deftest resolves-free-text-team-names
  (is (= "flamengo" (q/resolve-team ms "Flamengo-RJ")))
  (is (= "flamengo" (q/resolve-team ms "flamengo")))
  (is (= "flamengo" (q/resolve-team ms "fla")) "substring fallback")
  (is (nil? (q/resolve-team ms "Corinthians"))))

(deftest search-matches-by-team-newest-first
  (let [found (q/search-matches ms {:team "Flamengo"})]
    (is (= ["2023-09-03" "2023-05-28" "2023-03-10"] (map :date found)))))

(deftest search-matches-by-competition-season-and-dates
  (is (= 1 (count (q/search-matches ms {:competition "Copa Libertadores"}))))
  (is (= 2 (count (q/search-matches ms {:team "Flamengo" :season 2023 :competition "Brasileirão"}))))
  (is (= ["2023-09-03"] (map :date (q/search-matches ms {:team "Flamengo" :from "2023-06-01"}))))
  (is (= ["2023-05-28"] (map :date (q/search-matches ms {:team "Flamengo" :to "2023-06-01"
                                                        :competition "Brasileirão"})))))

(deftest venue-filter-restricts-to-home-or-away
  (is (= ["2023-09-03"] (map :date (q/search-matches ms {:team "Flamengo" :venue :home}))))
  (is (= ["2023-05-28" "2023-03-10"] (map :date (q/search-matches ms {:team "Flamengo" :venue :away})))))

(deftest team-record-counts-results-and-goals
  (let [{:keys [record]} (q/team-record ms {:team "Flamengo" :season 2023})]
    (is (= {:played 3 :wins 1 :draws 1 :losses 1 :goals-for 4 :goals-against 4}
           (dissoc record :win-rate)))
    (is (< (Math/abs (- 1/3 (:win-rate record))) 1e-9))))

(deftest team-record-home-only
  (let [{:keys [record]} (q/team-record ms {:team "Flamengo" :season 2023 :venue :home})]
    (is (= 1 (:played record)))
    (is (= 1 (:wins record)))))

(deftest head-to-head-between-two-teams
  (let [{:keys [record matches]} (q/head-to-head ms "Flamengo" "Fluminense")]
    (is (= 2 (:played record)))
    (is (= 1 (:wins record)))
    (is (= 1 (:losses record)))
    (is (= 2 (count matches)))))

(deftest standings-are-calculated-from-results
  (let [[first second] (q/standings ms {:season 2023 :competition "Brasileirão"})]
    (is (= "Flamengo" (:team first)))
    (is (= 3 (:points first)))
    (is (= 2 (:goals-for first)))
    (is (= 0 (:goal-difference first)))
    (is (= "Fluminense" (:team second)))
    (is (= 0 (:goal-difference second)))))

(deftest league-stats-aggregate-goals-and-results
  (let [s (q/league-stats ms {:competition "Brasileirão" :season 2023})]
    (is (= 2 (:matches s)))
    (is (= 4 (:total-goals s)))
    (is (== 2.0 (:goals-per-match s)))
    (is (== 1.0 (:home-win-rate s)))
    (is (== 0.0 (:away-win-rate s)))
    (is (== 0.0 (:draw-rate s)))))

(deftest player-search-filters-and-ranks
  (testing "nationality filter, highest overall first"
    (is (= ["Neymar Jr" "Alisson" "Gabriel Barbosa"]
           (map :name (q/search-players fx/players {:nationality "brazil"})))))
  (testing "position, minimum overall and name"
    (is (= ["Gabriel Barbosa"] (map :name (q/search-players fx/players {:position "st"}))))
    (is (= ["L. Messi" "Neymar Jr"] (map :name (q/search-players fx/players {:min-overall 90}))))
    (is (= ["Gabriel Barbosa"] (map :name (q/search-players fx/players {:name "gabriel"})))))
  (testing "limit"
    (is (= 1 (count (q/search-players fx/players {:nationality "Brazil" :limit 1}))))))

(deftest brazilian-club-summary-groups-by-club
  (let [rows (q/brazilian-club-summary fx/players)]
    (is (= 3 (count rows)))
    (is (= "Flamengo" (:club (first (filter #(= "Flamengo" (:club %)) rows)))))
    (is (== 76.0 (:average-overall (first (filter #(= "Flamengo" (:club %)) rows)))))))

(deftest real-2019-standings-match-the-spec-example
  (let [data @fx/real
        [champ second third] (q/standings (:matches data) {:season 2019})]
    (is (= ["Flamengo" 90 28 6 4] [(:team champ) (:points champ) (:wins champ) (:draws champ) (:losses champ)]))
    (is (= 74 (:points second) (:points third)))))
