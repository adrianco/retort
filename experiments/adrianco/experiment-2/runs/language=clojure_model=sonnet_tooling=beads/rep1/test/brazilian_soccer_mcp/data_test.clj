(ns brazilian-soccer-mcp.data-test
  (:require [clojure.test :refer [deftest is testing]]
            [brazilian-soccer-mcp.data :as data]))

;; ---------------------------------------------------------------------------
;; Team name normalisation
;; ---------------------------------------------------------------------------

(deftest normalize-team-name-test
  (testing "strips state suffix"
    (is (= "Palmeiras" (data/normalize-team-name "Palmeiras-SP")))
    (is (= "Flamengo"  (data/normalize-team-name "Flamengo-RJ")))
    (is (= "Sport"     (data/normalize-team-name "Sport-PE"))))
  (testing "handles names without suffix"
    (is (= "Flamengo"  (data/normalize-team-name "Flamengo")))
    (is (= "Santos"    (data/normalize-team-name "Santos"))))
  (testing "handles nil/empty"
    (is (nil? (data/normalize-team-name nil)))
    (is (nil? (data/normalize-team-name ""))))
  (testing "handles extra whitespace"
    (is (= "Palmeiras" (data/normalize-team-name "  Palmeiras-SP  ")))))

(deftest team-matches-test
  (testing "case-insensitive substring match"
    (is (data/team-matches? "flamengo" "Flamengo-RJ"))
    (is (data/team-matches? "Palmeiras" "Palmeiras-SP"))
    (is (not (data/team-matches? "Santos" "Flamengo-RJ"))))
  (testing "partial name match"
    (is (data/team-matches? "Palm" "Palmeiras-SP")))
  (testing "nil safety"
    (is (not (data/team-matches? nil "Flamengo")))
    (is (not (data/team-matches? "Flamengo" nil)))))

;; ---------------------------------------------------------------------------
;; Date parsing
;; ---------------------------------------------------------------------------

(deftest parse-date-test
  (testing "ISO datetime"
    (let [d (data/parse-date "2012-05-19 18:30:00")]
      (is (some? d))
      (is (= 2012 (.getYear d)))
      (is (= 5 (.getMonthValue d)))
      (is (= 19 (.getDayOfMonth d)))))
  (testing "ISO date"
    (let [d (data/parse-date "2023-09-24")]
      (is (= 2023 (.getYear d)))))
  (testing "Brazilian format"
    (let [d (data/parse-date "29/03/2003")]
      (is (= 2003 (.getYear d)))
      (is (= 3 (.getMonthValue d)))
      (is (= 29 (.getDayOfMonth d)))))
  (testing "nil/empty returns nil"
    (is (nil? (data/parse-date nil)))
    (is (nil? (data/parse-date "")))
    (is (nil? (data/parse-date "bad-date")))))

;; ---------------------------------------------------------------------------
;; Data loading
;; ---------------------------------------------------------------------------

(deftest load-all-datasets-test
  (testing "all datasets load without error"
    (let [db (data/load-all!)]
      (is (map? db))
      (is (seq (:brasileirao db)))
      (is (seq (:cup db)))
      (is (seq (:libertadores db)))
      (is (seq (:br-football db)))
      (is (seq (:historico db)))
      (is (seq (:fifa db)))
      (is (seq (:all-matches db)))))
  (testing "dataset sizes are reasonable"
    (let [db (data/db)]
      (is (>= (count (:brasileirao db)) 4000))
      (is (>= (count (:cup db)) 1000))
      (is (>= (count (:libertadores db)) 1000))
      (is (>= (count (:fifa db)) 10000))))
  (testing "match records have expected fields"
    (let [m (first (:brasileirao (data/db)))]
      (is (contains? m :competition))
      (is (contains? m :home-team))
      (is (contains? m :away-team))
      (is (contains? m :home-goals))
      (is (contains? m :away-goals))
      (is (contains? m :season))))
  (testing "player records have expected fields"
    (let [p (first (:fifa (data/db)))]
      (is (contains? p :name))
      (is (contains? p :nationality))
      (is (contains? p :overall))
      (is (contains? p :club)))))
