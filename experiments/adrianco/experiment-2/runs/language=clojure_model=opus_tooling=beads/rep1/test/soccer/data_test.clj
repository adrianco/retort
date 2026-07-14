(ns soccer.data-test
  (:require [clojure.test :refer [deftest is testing]]
            [soccer.data :as data]))

(deftest normalize-team-test
  (testing "strips state suffix"
    (is (= "Palmeiras" (data/normalize-team "Palmeiras-SP")))
    (is (= "Flamengo" (data/normalize-team "Flamengo-RJ"))))
  (testing "strips country suffix"
    (is (= "Nacional" (data/normalize-team "Nacional (URU)"))))
  (testing "trims whitespace"
    (is (= "Santos" (data/normalize-team "  Santos  "))))
  (testing "handles nil"
    (is (nil? (data/normalize-team nil)))))

(deftest load-dataset-test
  (testing "loads all six datasets"
    (let [ds (data/load-dataset)]
      (is (pos? (count (:matches ds))))
      (is (pos? (count (:players ds))))
      ;; At least 20k matches across all files per spec counts
      (is (> (count (:matches ds)) 20000))
      (is (> (count (:players ds)) 18000))
      ;; Every match has core fields
      (let [m (first (:matches ds))]
        (is (contains? m :home))
        (is (contains? m :away))
        (is (contains? m :competition))))))
