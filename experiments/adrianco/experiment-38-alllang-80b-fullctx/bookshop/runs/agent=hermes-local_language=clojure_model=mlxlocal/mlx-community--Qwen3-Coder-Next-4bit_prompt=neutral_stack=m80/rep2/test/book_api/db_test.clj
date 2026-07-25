(ns book-api.db-test
  (:require [clojure.test :refer :all]
            [book-api.db :as db]))

(defn setup-test-db []
  "Setup a test database with a fresh schema"
  (db/init-db))

(defn cleanup-test-db []
  "Clean up the test database"
  (try
    (.delete (java.io.File. "books.db"))
    (catch Exception e)))

(defn reset-db []
  "Reset the database for testing"
  (cleanup-test-db)
  (setup-test-db))

(use-fixtures
  :once
  (fn [f]
    (setup-test-db)
    (f)
    (cleanup-test-db)))

(use-fixtures
  :each
  (fn [f]
    (reset-db)
    (f)))

(deftest test-create-and-get-book
  (testing "Creating and retrieving a book"
    (let [book {:title "Test Book" :author "Test Author" :year 2024 :isbn "1234567890"}
          result (db/create-book book)]
      (is (:success result) "Book should be created successfully")
      (let [books (db/get-all-books)]
        (is (= 1 (count books)) "Should have exactly one book")
        (is (= "Test Book" (:title (first books))) "Book title should match"))))

(deftest test-get-book-by-id
  (testing "Retrieving a book by ID"
    (let [book {:title "Get By ID Book" :author "Author Two" :year 2023 :isbn "9876543210"}
          create-result (db/create-book book)
          books (db/get-all-books)
          book-id (:id (first books))]
      (is (:success create-result) "Book should be created")
      (let [retrieved-book (db/get-book-by-id book-id)]
        (is (= (:title book) (:title retrieved-book)) "Retrieved book title should match")
        (is (= (:author book) (:author retrieved-book)) "Retrieved book author should match"))))

(deftest test-update-book
  (testing "Updating a book"
    (let [book {:title "Original Title" :author "Original Author" :year 2020 :isbn "1111111111"}
          create-result (db/create-book book)
          books (db/get-all-books)
          book-id (:id (first books))]
      (is (:success create-result) "Book should be created")
      (let [updated-book {:title "Updated Title" :author "Updated Author" :year 2024 :isbn "2222222222"}
            update-result (db/update-book book-id updated-book)]
        (is (:success update-result) "Book should be updated")
        (let [retrieved-book (db/get-book-by-id book-id)]
          (is (= "Updated Title" (:title retrieved-book)) "Updated title should match")
          (is (= "Updated Author" (:author retrieved-book)) "Updated author should match")))))

(deftest test-delete-book
  (testing "Deleting a book"
    (let [book {:title "Delete Me" :author "Delete Author" :year 2022 :isbn "3333333333"}
          create-result (db/create-book book)
          books (db/get-all-books)
          book-id (:id (first books))]
      (is (:success create-result) "Book should be created")
      (db/delete-book book-id)
      (let [books-after-delete (db/get-all-books)]
        (is (= 0 (count books-after-delete)) "Book should be deleted"))))

(deftest test-get-books-by-author
  (testing "Getting books by author"
    (db/create-book {:title "Book One" :author "Same Author" :year 2020 :isbn "4444444441"})
    (db/create-book {:title "Book Two" :author "Same Author" :year 2021 :isbn "4444444442"})
    (db/create-book {:title "Book Three" :author "Different Author" :year 2022 :isbn "4444444443"})
    (let [books (db/get-books-by-author "Same Author")]
      (is (= 2 (count books)) "Should have exactly 2 books by Same Author"))))
