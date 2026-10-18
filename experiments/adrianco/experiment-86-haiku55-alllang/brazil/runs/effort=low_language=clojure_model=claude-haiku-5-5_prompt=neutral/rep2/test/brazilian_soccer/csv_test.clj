(ns brazilian-soccer.csv-test
  (:require [brazilian-soccer.csv :as csv]
            [clojure.test :refer [deftest is testing]]))

(deftest parse-rows-handles-quoting
  (testing "quoted fields keep commas, doubled quotes and newlines"
    (is (= [["a" "b,c\"d" "e\nf"]]
           (csv/parse-rows "a,\"b,c\"\"d\",\"e\nf\"\n"))))
  (testing "CRLF line endings and trailing newline"
    (is (= [["x" "y"] ["1" "2"]] (csv/parse-rows "x,y\r\n1,2\r\n"))))
  (testing "leading UTF-8 BOM is ignored and blank lines skipped"
    (is (= [["id" "name"] ["1" "São Paulo"]]
           (csv/parse-rows "\uFEFFid,name\n\n1,São Paulo\n")))))

(deftest parse-rows-keeps-empty-fields
  (is (= [["" "b" ""]] (csv/parse-rows ",b,\n"))))

(deftest read-maps-keys-rows-by-trimmed-header
  (let [f (java.io.File/createTempFile "csv-test" ".csv")]
    (try
      (spit f "\"ID\", Name ,Goals\n1,\"Flamengo, RJ\",2\n")
      (is (= [{"ID" "1" "Name" "Flamengo, RJ" "Goals" "2"}]
             (csv/read-maps (.getPath f))))
      (finally (.delete f)))))
