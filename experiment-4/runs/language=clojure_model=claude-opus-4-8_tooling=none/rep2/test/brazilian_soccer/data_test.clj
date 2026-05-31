(ns brazilian-soccer.data-test
  "Context
  =======
  BDD tests for data loading: every CSV must be loadable and the unified match
  schema must be populated, with dates normalised and cross-file duplicates
  removed."
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.data :as data]))

(deftest date-parsing
  (testing "Scenario: multiple date formats normalise to ISO yyyy-MM-dd"
    (is (= "2012-05-19" (data/parse-date "2012-05-19 18:30:00")))
    (is (= "2023-09-24" (data/parse-date "2023-09-24")))
    (is (= "2003-03-29" (data/parse-date "29/03/2003")))
    (is (nil? (data/parse-date "")))))

(deftest int-parsing
  (testing "Scenario: lenient integer parsing handles floats and blanks"
    (is (= 3 (data/parse-int "3")))
    (is (= 3 (data/parse-int "3.0")))
    (is (nil? (data/parse-int "")))
    (is (nil? (data/parse-int "x")))))

(deftest all-files-loaded
  (testing "Scenario: all six datasets contribute to the in-memory db"
    ;; Given the loaded database
    (let [ms (data/matches)
          ps (data/players)]
      ;; Then there are matches and players
      (is (pos? (count ms)))
      (is (pos? (count ps)))
      ;; And every match competition is represented
      (let [comps (set (map :competition ms))]
        (is (contains? comps "Brasileirão Série A"))
        (is (contains? comps "Copa do Brasil"))
        (is (contains? comps "Copa Libertadores"))))))

(deftest unified-schema-is-complete
  (testing "Scenario: each match has teams, keys, scores and a competition"
    (doseq [m (take 200 (data/matches))]
      (is (string? (:home m)))
      (is (string? (:away m)))
      (is (string? (:home-key m)))
      (is (integer? (:home-goal m)))
      (is (integer? (:away-goal m)))
      (is (string? (:competition m))))))

(deftest no-tripled-seasons
  (testing "Scenario: a Brasileirão season is not double/triple counted"
    ;; Given the 2019 Série A (present in three source files)
    ;; When we count distinct teams' matches
    ;; Then no team has more than a full season of fixtures
    (let [ms (->> (data/matches)
                  (filter #(and (= (:competition %) "Brasileirão Série A")
                                (= (:season %) 2019))))
          per-team (->> (mapcat (fn [m] [(:home-key m) (:away-key m)]) ms)
                        frequencies vals)]
      (is (every? #(<= % 40) per-team)
          "each team plays ~38 league matches, never ~76 or ~114"))))
