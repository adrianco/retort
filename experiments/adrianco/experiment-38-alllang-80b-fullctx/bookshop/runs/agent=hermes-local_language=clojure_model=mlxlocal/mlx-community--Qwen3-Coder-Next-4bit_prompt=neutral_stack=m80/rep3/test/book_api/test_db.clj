(ns book-api.test-db
  (:require [clojure.test :refer :all]
            [book-api.db :as db]))

(use-fixtures :once
  (fn [f]
    (db/init-db)
    (f)))

(deftest test-create-and-get-book
  (testing "Create a book and retrieve it"
    (let [book (db/create-book {:title "Test Book" :author "Test Author" :year 2024 :isbn "123-456"})
          book-id (:id book)
          retrieved (db/get-book-by-id book-id)]
      (is (= (:title retrieved) "Test Book"))
      (is (= (:author retrieved) "Test Author"))
      (is (= (:year retrieved) 2024))
      (is (= (:isbn retrieved) "123-456")))))

(deftest test-get-all-books
  (testing "Get all books"
    (db/create-book {:title "Book 1" :author "Author A" :year 2020 :isbn "001"})
    (db/create-book {:title "Book 2" :author "Author B" :year 2021 :isbn "002"})
    (let [books (db/get-all-books)]
      (is (>= (count books) 2)))))

(deftest test-update-book
  (testing "Update an existing book"
    (let [book (db/create-book {:title "Original Title" :author "Original Author" :year 2020 :isbn "000"})
          book-id (:id book)]
      (db/update-book book-id {:title "Updated Title" :author "Updated Author" :year 2024 :isbn "999"})
      (let [updated (db/get-book-by-id book-id)]
        (is (= (:title updated) "Updated Title"))
        (is (= (:author updated) "Updated Author"))
        (is (= (:year updated) 2024))
        (is (= (:isbn updated) "999"))))))

(deftest test-delete-book
  (testing "Delete a book"
    (let [book (db/create-book {:title "To Delete" :author "Delete Author" :year 2020 :isbn "DEL"})
          book-id (:id book)]
      (is (seq (db/get-book-by-id book-id)))
      (db/delete-book book-id)
      (is (nil? (seq (db/get-book-by-id book-id)))))))

(deftest test-get-books-by-author
  (testing "Get books by author"
    (db/create-book {:title "Book A1" :author "Author X" :year 2020 :isbn "AX1"})
    (db/create-book {:title "Book A2" :author "Author X" :year 2021 :isbn "AX2"})
    (db/create-book {:title "Book B1" :author "Author Y" :year 2022 :isbn "AY1"})
    (let [books-by-x (db/get-books-by-author "Author X")]
      (is (= (count books-by-x) 2)))))
