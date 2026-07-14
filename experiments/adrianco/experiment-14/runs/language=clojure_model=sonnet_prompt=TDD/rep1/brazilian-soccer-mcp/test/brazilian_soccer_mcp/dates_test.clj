(ns brazilian-soccer-mcp.dates-test
  (:require [clojure.test :refer :all]
            [brazilian-soccer-mcp.dates :as dates]))

(deftest parse-date-test
  (testing "parses ISO date format"
    (let [d (dates/parse-date "2023-09-24")]
      (is (not (nil? d)))
      (is (= 2023 (dates/year d)))
      (is (= 9 (dates/month d)))
      (is (= 24 (dates/day d)))))

  (testing "parses Brazilian date format DD/MM/YYYY"
    (let [d (dates/parse-date "29/03/2003")]
      (is (not (nil? d)))
      (is (= 2003 (dates/year d)))
      (is (= 3 (dates/month d)))
      (is (= 29 (dates/day d)))))

  (testing "parses datetime format with time"
    (let [d (dates/parse-date "2012-05-19 18:30:00")]
      (is (not (nil? d)))
      (is (= 2012 (dates/year d)))
      (is (= 5 (dates/month d)))
      (is (= 19 (dates/day d)))))

  (testing "returns nil for nil or empty input"
    (is (nil? (dates/parse-date nil)))
    (is (nil? (dates/parse-date ""))))

  (testing "returns nil for unparseable date"
    (is (nil? (dates/parse-date "not-a-date")))))

(deftest date-in-range-test
  (testing "date within range is true"
    (let [d (dates/parse-date "2023-06-15")]
      (is (dates/date-in-range? d "2023-01-01" "2023-12-31"))))

  (testing "date outside range is false"
    (let [d (dates/parse-date "2022-06-15")]
      (is (not (dates/date-in-range? d "2023-01-01" "2023-12-31")))))

  (testing "nil bounds means no constraint"
    (let [d (dates/parse-date "2023-06-15")]
      (is (dates/date-in-range? d nil nil))
      (is (dates/date-in-range? d "2023-01-01" nil))
      (is (dates/date-in-range? d nil "2023-12-31"))))

  (testing "nil date returns false"
    (is (not (dates/date-in-range? nil "2023-01-01" "2023-12-31")))))

(deftest date-year-test
  (testing "extracts year from various formats"
    (is (= 2023 (dates/extract-year "2023-09-24")))
    (is (= 2003 (dates/extract-year "29/03/2003")))
    (is (= 2012 (dates/extract-year "2012-05-19 18:30:00")))
    (is (nil? (dates/extract-year nil)))
    (is (nil? (dates/extract-year "")))))
