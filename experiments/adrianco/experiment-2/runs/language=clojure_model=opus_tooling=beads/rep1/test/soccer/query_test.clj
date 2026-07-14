(ns soccer.query-test
  (:require [clojure.test :refer [deftest is testing use-fixtures]]
            [soccer.data :as data]
            [soccer.query :as q]))

(def ^:dynamic *ds* nil)

(defn with-dataset [f]
  (binding [*ds* (data/load-dataset)] (f)))

(use-fixtures :once with-dataset)

(defn- matches [] (:matches *ds*))
(defn- players [] (:players *ds*))

(deftest matches-by-team-test
  (let [ms (q/matches-by-team (matches) "Flamengo")]
    (is (pos? (count ms)))
    (is (every? #(or (= "Flamengo" (:home %))
                     (= "Flamengo" (:away %))
                     ;; some BR-Football may use different spelling
                     (re-find #"(?i)flamengo" (str (:home %) " " (:away %))))
                ms))))

(deftest matches-between-test
  (let [flu-fla (q/matches-between (matches) "Flamengo" "Fluminense")]
    (is (pos? (count flu-fla)))
    (is (every? (fn [m] (and (re-find #"(?i)flamengo|fluminense" (:home m))
                             (re-find #"(?i)flamengo|fluminense" (:away m))))
                flu-fla))))

(deftest winner-test
  (is (= :home  (q/winner {:home-goal 2 :away-goal 1})))
  (is (= :away  (q/winner {:home-goal 0 :away-goal 3})))
  (is (= :draw  (q/winner {:home-goal 1 :away-goal 1})))
  (is (nil?     (q/winner {:home-goal nil :away-goal 1}))))

(deftest team-record-test
  (let [ms (q/matches-by-season (matches) 2019)
        r  (q/team-record ms "Flamengo")]
    (is (pos? (:matches r)))
    (is (= (:matches r) (+ (:wins r) (:draws r) (:losses r))))
    (is (>= (:gf r) 0))))

(deftest head-to-head-test
  (let [h (q/head-to-head (matches) "Palmeiras" "Santos")]
    (is (pos? (:matches h)))
    (is (= (:matches h) (+ (:a-wins h) (:b-wins h) (:draws h))))))

(deftest standings-test
  (let [s (q/standings (-> (matches)
                           (q/matches-by-season 2019)
                           (q/matches-by-competition "Brasileirão")))]
    (is (seq s))
    (testing "sorted by points descending"
      (is (apply >= (map :points s))))
    (testing "champion has highest points"
      (is (= (:team (first s)) (:team (first (sort-by (comp - :points) s))))))))

(deftest stats-test
  (let [ms (q/matches-by-season (matches) 2019)]
    (is (pos? (q/avg-goals-per-match ms)))
    (is (<= 0.0 (q/home-win-rate ms) 1.0))
    (is (= 5 (count (q/biggest-wins ms 5))))))

(deftest players-test
  (let [brs (q/players-by-nationality (players) "Brazil")]
    (is (pos? (count brs)))
    (is (every? #(= "Brazil" (:nationality %)) brs)))
  (testing "top players sorted by overall"
    (let [top (q/top-players (players) 5)]
      (is (= 5 (count top)))
      (is (apply >= (map :overall top)))))
  (testing "search by name"
    (is (seq (q/players-by-name (players) "Neymar")))))
