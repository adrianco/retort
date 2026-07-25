(ns book-api.db-test
  "Tests for the SQLite persistence layer, independent of HTTP."
  (:require [book-api.db :as db]
            [book-api.test-support :as ts :refer [*ds*]]
            [clojure.test :refer [deftest is testing use-fixtures]]))

(use-fixtures :each ts/with-test-db)

(def dune {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441013593"})

(deftest migrate-is-idempotent
  (testing "re-running the migration on a live database is harmless"
    (db/insert-book! *ds* dune)
    (db/migrate! *ds*)
    (is (= 1 (count (db/list-books *ds* {}))))))

(deftest ping-reports-a-live-database
  (is (true? (db/ping *ds*))))

(deftest insert-returns-the-stored-row
  (let [row (db/insert-book! *ds* dune)]
    (is (pos-int? (:id row)))
    (is (= dune (dissoc row :id)))
    (is (= row (db/find-book *ds* (:id row))))))

(deftest ids-are-distinct
  (let [a (db/insert-book! *ds* dune)
        b (db/insert-book! *ds* (assoc dune :title "Dune Messiah" :isbn "9780575074903"))]
    (is (not= (:id a) (:id b)))))

(deftest find-missing-book-is-nil
  (is (nil? (db/find-book *ds* 12345))))

(deftest author-filter
  (db/insert-book! *ds* dune)
  (db/insert-book! *ds* {:title "Emma" :author "Jane Austen" :year 1815 :isbn nil})
  (testing "no filter returns everything"
    (is (= 2 (count (db/list-books *ds* {})))))
  (testing "an exact author match filters"
    (is (= ["Dune"] (map :title (db/list-books *ds* {:author "Frank Herbert"})))))
  (testing "the match is case-insensitive"
    (is (= ["Dune"] (map :title (db/list-books *ds* {:author "FRANK HERBERT"})))))
  (testing "an unknown author yields nothing"
    (is (empty? (db/list-books *ds* {:author "Nobody"})))))

(deftest update-and-delete
  (let [id (:id (db/insert-book! *ds* dune))]
    (testing "update returns the new row"
      (let [row (db/update-book! *ds* id (assoc dune :year 2019 :isbn nil))]
        (is (= 2019 (:year row)))
        (is (nil? (:isbn row)))
        (is (= id (:id row)))))
    (testing "updating an unknown id returns nil"
      (is (nil? (db/update-book! *ds* 12345 dune))))
    (testing "delete reports whether a row went away"
      (is (true? (db/delete-book! *ds* id)))
      (is (false? (db/delete-book! *ds* id)))
      (is (nil? (db/find-book *ds* id))))))

(deftest isbn-owner-lookup
  (let [id (:id (db/insert-book! *ds* dune))]
    (is (= id (db/isbn-owner *ds* (:isbn dune))))
    (is (nil? (db/isbn-owner *ds* "0000000000000")))
    (testing "a nil isbn never claims ownership"
      (db/insert-book! *ds* {:title "Untitled" :author "Anon" :year nil :isbn nil})
      (is (nil? (db/isbn-owner *ds* nil))))))
