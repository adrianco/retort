(ns br-soccer.data-test
  (:require [clojure.test :refer [deftest is testing]]
            [br-soccer.data :as d]))

(deftest normalize-team-test
  (testing "strips state suffixes"
    (is (= "palmeiras" (d/normalize-team "Palmeiras-SP")))
    (is (= "flamengo" (d/normalize-team "Flamengo-RJ")))
    (is (= "nacional" (d/normalize-team "Nacional (URU)")))
    (is (= "flamengo" (d/normalize-team "Flamengo")))))

(deftest team-matches-test
  (is (d/team-matches? "Flamengo" "Flamengo-RJ"))
  (is (d/team-matches? "flamengo" "Flamengo"))
  (is (d/team-matches? "Palmeiras" "Palmeiras-SP"))
  (is (not (d/team-matches? "Santos" "Palmeiras-SP"))))

(deftest loads-data-test
  (testing "match and player data load non-empty"
    (is (pos? (count (d/all-matches))))
    (is (pos? (count (d/all-players))))
    (let [m (first (d/all-matches))]
      (is (:home m))
      (is (:away m))
      (is (:competition m)))))
