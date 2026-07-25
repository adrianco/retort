(ns book-api.db-test
  (:require [clojure.test :refer :all]
            [book-api.db :as db]
            [book-api.schema :as schema]))

(deftest test-init-db
  (testing "Database initialization"
    (is (thrown? clojure.lang.ExceptionInfo
                 (db/get-book 1)))))

(deftest test-book-crud
  (testing "Create book"
    (let [book {:title "Test Book" :author "Test Author" :year 2024 :isbn "1234567890"}
          created (db/create-book book)]
      (is (:id created))
      (is (= "Test Book" (:title created)))
      (is (= "Test Author" (:author created)))))

  (testing "Get book by ID"
    (let [book {:title "Get Test Book" :author "Get Author" :year 2024 :isbn "0987654321"}
          created (db/create-book book)
          retrieved (db/get-book (:id created))]
      (is retrieved)
      (is (= (:id created) (:id retrieved)))))

  (testing "Get books with filter"
    (db/create-book {:title "Book 1" :author "Author A" :year 2020 :isbn "1111111111"})
    (db/create-book {:title "Book 2" :author "Author B" :year 2021 :isbn "2222222222"})
    (db/create-book {:title "Book 3" :author "Author A" :year 2022 :isbn "3333333333"})
    
    (let [all-books (db/get-books {})
          author-a-books (db/get-books {:author "Author A"})]
      (is (>= (count all-books) 3))
      (is (= 2 (count author-a-books)))))

  (testing "Update book"
    (let [book {:title "Original Title" :author "Original Author" :year 2020 :isbn "1111111112"}
          created (db/create-book book)
          updated (db/update-book (:id created) {:title "Updated Title" :author "Updated Author" :year 2023 :isbn "2222222223"})]
      (is (= "Updated Title" (:title updated)))
      (is (= "Updated Author" (:author updated)))
      (is (= 2023 (:year updated)))))

  (testing "Delete book"
    (let [book {:title "To Delete" :author "Delete Author" :year 2024 :isbn "4444444444"}
          created (db/create-book book)
          id (:id created)]
      (db/delete-book id)
      (is (nil? (db/get-book id))))))

(deftest test-schema-validation
  (testing "Validate book parameters"
    (is (thrown? clojure.lang.ExceptionInfo
                 (schema/validate-book-params {})))
    (is (thrown? clojure.lang.ExceptionInfo
                 (schema/validate-book-params {:title "Test"})))
    (is (thrown? clojure.lang.ExceptionInfo
                 (schema/validate-book-params {:author "Test"})))
    (is (thrown? clojure.lang.ExceptionInfo
                 (schema/validate-book-params {:title "" :author ""})))
    
    (is (try
          (schema/validate-book-params {:title "Valid" :author "Valid" :year 2024 :isbn "123"})
          true
          (catch Exception e false)))))
