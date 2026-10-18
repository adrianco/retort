(ns book-api.validation-test
  (:require [book-api.validation :as v]
            [clojure.test :refer [deftest is testing]]))

(deftest valid-book-returns-nil
  (is (nil? (v/validate-book {:title "Dune" :author "Frank Herbert"})))
  (is (nil? (v/validate-book {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "123"}))))

(deftest required-fields
  (is (= #{:title :author} (set (keys (v/validate-book {}))))))

(deftest optional-field-types
  (is (= #{:year} (set (keys (v/validate-book {:title "t" :author "a" :year 1.5})))))
  (is (= #{:isbn} (set (keys (v/validate-book {:title "t" :author "a" :isbn 123}))))))

(deftest normalize-trims-strings
  (is (= {:title "Dune" :author "Frank Herbert" :year nil :isbn "1"}
         (v/normalize-book {:title " Dune " :author "Frank Herbert " :isbn " 1 "}))))
