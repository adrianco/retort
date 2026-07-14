;; =============================================================================
;; brazilian-soccer.data-test
;; -----------------------------------------------------------------------------
;; BDD scenarios for parsing primitives (dates, ints) and for loading the real
;; CSV datasets from data/kaggle (integration-style coverage of all 6 files).
;; =============================================================================
(ns brazilian-soccer.data-test
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.data :as data]))

(deftest parse-int-scenario
  (testing "Given numeric strings of various shapes, Then they parse to longs"
    (is (= 1 (data/parse-int "1")))
    (is (= 1 (data/parse-int "1.0")))
    (is (= 8 (data/parse-int "8")))
    (is (nil? (data/parse-int "")))
    (is (nil? (data/parse-int nil)))
    (is (nil? (data/parse-int "abc")))))

(deftest parse-date-scenario
  (testing "Given the three date formats in the data, Then all normalise to ISO"
    (is (= "2012-05-19" (data/parse-date "2012-05-19 18:30:00")))
    (is (= "2023-09-24" (data/parse-date "2023-09-24")))
    (is (= "2003-03-29" (data/parse-date "29/03/2003")))
    (is (nil? (data/parse-date "")))
    (is (nil? (data/parse-date nil)))))

(deftest ->match-scenario
  (testing "Given a raw Brasileirão row, When normalised, Then the schema is correct"
    (let [m (data/->match {:competition "Brasileirão Série A" :source "x"
                           :date "2019-10-27 16:00:00" :season "2019" :round "30"
                           :home-raw "Flamengo-RJ" :away-raw "Grêmio-RS"
                           :hg "5" :ag "0"})]
      (is (= "Flamengo" (:home m)))
      (is (= "Grêmio" (:away m)))
      (is (= "flamengo" (:home-key m)))
      (is (= 2019 (:season m)))
      (is (= "2019-10-27" (:date m)))
      (is (= 5 (:home-goal m)))
      (is (= :home (:winner m))))))

(deftest dedupe-scenario
  (testing "Given the same game from two files with different naming, Then it is merged"
    (let [bras (data/->match {:competition "Brasileirão Série A" :source "a"
                              :date "2019-04-27 21:00:00" :season "2019" :round "1"
                              :home-raw "Flamengo-RJ" :away-raw "Cruzeiro-MG"
                              :home-state "RJ" :away-state "MG" :hg "3" :ag "1"})
          novo (data/->match {:competition "Brasileirão Série A" :source "b"
                              :date "27/04/2019" :season "2019" :round "1"
                              :home-raw "Flamengo" :away-raw "Cruzeiro"
                              :home-state "RJ" :away-state "MG" :hg "3" :ag "1"})
          other (data/->match {:competition "Brasileirão Série A" :source "a"
                               :date "2019-05-01" :season "2019" :round "2"
                               :home-raw "Internacional-RS" :away-raw "Flamengo-RJ"
                               :home-state "RS" :away-state "RJ" :hg "2" :ag "1"})]
      (is (= 2 (count (data/dedupe-matches [bras novo other]))))))
  (testing "Given matches without a date, Then they are never merged away"
    (let [m (data/->match {:competition "x" :source "a" :date nil
                           :home-raw "A" :away-raw "B" :hg "1" :ag "0"})]
      (is (= 3 (count (data/dedupe-matches [m m m])))))))

(deftest load-all-scenario
  (testing "Given the bundled Kaggle CSVs, When loaded, Then all datasets populate"
    (let [{:keys [matches players]} (data/load-all)]
      (is (> (count matches) 20000)
          "all match files combine into a large corpus")
      (is (> (count players) 18000)
          "the FIFA player file loads")
      (testing "And every required competition label is present"
        (let [comps (set (map :competition matches))]
          (is (contains? comps "Brasileirão Série A"))
          (is (contains? comps "Copa do Brasil"))
          (is (contains? comps "Copa Libertadores"))))
      (testing "And matches carry normalised keys and parsed goals"
        (let [m (first (filter #(and (:home-key %) (:home-goal %)) matches))]
          (is (string? (:home-key m)))
          (is (integer? (:home-goal m))))))))
