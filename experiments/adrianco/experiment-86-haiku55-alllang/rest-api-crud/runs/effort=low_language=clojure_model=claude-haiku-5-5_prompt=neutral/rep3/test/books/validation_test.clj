(ns books.validation-test
  (:require [clojure.test :refer [deftest is testing]]
            [books.handler :as h]))

(deftest valid-book-passes
  (is (nil? (h/validate {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "978"})))
  (is (nil? (h/validate {:title "Dune" :author "Frank Herbert"}))))

(deftest required-fields
  (testing "missing title and author"
    (is (= {:title "title is required" :author "author is required"} (h/validate {}))))
  (testing "blank title and author"
    (is (= {:title "title must not be blank" :author "author must not be blank"}
           (h/validate {:title "  " :author ""})))))

(deftest type-checks
  (is (= {:year "year must be an integer"} (h/validate {:title "a" :author "b" :year "1965"})))
  (is (= {:isbn "isbn must be a string"} (h/validate {:title "a" :author "b" :isbn 123}))))
