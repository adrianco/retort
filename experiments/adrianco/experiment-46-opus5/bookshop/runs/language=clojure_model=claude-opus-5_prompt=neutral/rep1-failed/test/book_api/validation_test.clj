(ns book-api.validation-test
  "Unit tests for payload validation and coercion."
  (:require [book-api.validation :as v]
            [clojure.test :refer [are deftest is testing]]))

(defn- fields [payload]
  (set (map :field (:errors (v/validate-book payload)))))

(deftest valid-payloads
  (testing "a full payload is coerced, not rejected"
    (is (= {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441013593"}
           (:book (v/validate-book {:title "Dune" :author "Frank Herbert"
                                    :year 1965 :isbn "9780441013593"})))))

  (testing "year and isbn default to nil"
    (is (= {:title "Dune" :author "Frank Herbert" :year nil :isbn nil}
           (:book (v/validate-book {:title "Dune" :author "Frank Herbert"})))))

  (testing "a numeric year sent as a string is coerced"
    (is (= 1965 (:year (:book (v/validate-book {:title "Dune" :author "FH" :year "1965"})))))))

(deftest invalid-payloads
  (are [payload expected] (= expected (fields payload))
    {}                                        #{"title" "author"}
    {:title "Dune"}                           #{"author"}
    {:author "FH"}                            #{"title"}
    {:title "  " :author "FH"}                #{"title"}
    {:title "Dune" :author nil}               #{"author"}
    {:title ["Dune"] :author "FH"}            #{"title"}
    {:title "Dune" :author "FH" :year "soon"} #{"year"}
    {:title "Dune" :author "FH" :year 1e9}    #{"year"}
    {:title "Dune" :author "FH" :isbn 12345}  #{"isbn"})

  (testing "an over-long title is rejected"
    (is (= #{"title"} (fields {:title (apply str (repeat 501 "x")) :author "FH"}))))

  (testing "a non-map body is rejected"
    (is (= #{"body"} (fields [1 2 3])))
    (is (= #{"body"} (fields "hello")))))

(deftest parse-id
  (are [in out] (= out (v/parse-id in))
    "1"    1
    "42"   42
    " 7 "  7
    "0"    nil
    "-3"   nil
    "abc"  nil
    ""     nil
    nil    nil))
