(ns book-api.handlers-test
  (:require [clojure.test :refer :all]
            [book-api.handlers :as handlers]
            [book-api.db :as db]))

(defn reset-db []
  (try
    (.delete (java.io.File. "books.db"))
    (catch Exception e nil))
  (db/init-db))

(defn ->response [method path params & [query]]
  {:request-method method
   :uri path
   :params params
   :query-params query})

(deftest test-health-handler
  (testing "Health check returns ok"
    (let [response (handlers/health-handler nil)]
      (is (= 200 (:status response)))
      (is (= "ok" (get-in response [:body :status])))))

  (testing "Health check returns service name"
    (let [response (handlers/health-handler nil)]
      (is (= "book-api" (get-in response [:body :service]))))))

(deftest test-create-book-handler
  (reset-db)
  
  (testing "Create book with valid data"
    (let [response (handlers/create-book-handler {:title "Test Book" :author "Test Author" :year 2024 :isbn "1234567890"})]
      (is (= 201 (:status response)))
      (is (= "Test Book" (get-in response [:body :title])))
      (is (= "Test Author" (get-in response [:body :author])))
      (is (contains? (:body response) :id))))

  (testing "Create book with missing title"
    (let [response (handlers/create-book-handler {:author "Test Author" :year 2024 :isbn "1234567890"})]
      (is (= 400 (:status response)))
      (is (contains? (get-in response [:body :errors]) :title))))

  (testing "Create book with missing author"
    (let [response (handlers/create-book-handler {:title "Test Book" :year 2024 :isbn "1234567890"})]
      (is (= 400 (:status response)))
      (is (contains? (get-in response [:body :errors]) :author))))

  (testing "Create book with invalid year"
    (let [response (handlers/create-book-handler {:title "Test Book" :author "Test Author" :year "not-a-number" :isbn "1234567890"})]
      (is (= 400 (:status response)))))

  (testing "Create book with duplicate ISBN"
    (db/create-book {:title "First Book" :author "Author 1" :year 2020 :isbn "9780596517748"})
    (let [response (handlers/create-book-handler {:title "Second Book" :author "Author 2" :year 2021 :isbn "9780596517748"})]
      (is (= 500 (:status response))))))

(deftest test-list-books-handler
  (reset-db)
  
  (db/create-book {:title "Book 1" :author "Author A" :year 2020 :isbn "1111111111"})
  (db/create-book {:title "Book 2" :author "Author B" :year 2021 :isbn "2222222222"})
  (db/create-book {:title "Book 3" :author "Author A" :year 2022 :isbn "3333333333"})
  
  (testing "List all books"
    (let [response (handlers/list-books-handler {})]
      (is (= 200 (:status response)))
      (is (vector? (:body response)))
      (is (>= (count (:body response)) 3))))

  (testing "Filter by author"
    (let [response (handlers/list-books-handler {:author "Author A"})]
      (is (= 200 (:status response)))
      (is (= 2 (count (:body response)))))))

(deftest test-get-book-handler
  (reset-db)
  
  (testing "Get existing book"
    (let [book {:title "Get Test" :author "Get Author" :year 2024 :isbn "5555555555"}
          created (db/create-book book)
          response (handlers/get-book-handler (:id created))]
      (is (= 200 (:status response)))
      (is (= "Get Test" (get-in response [:body :title])))))

  (testing "Get non-existent book"
    (let [response (handlers/get-book-handler 9999)]
      (is (= 404 (:status response)))
      (is (contains? (get-in response [:body]) :error))))

  (testing "Get book with invalid ID"
    (let [response (handlers/get-book-handler -1)]
      (is (= 400 (:status response))))))

(deftest test-update-book-handler
  (reset-db)
  
  (testing "Update existing book"
    (let [book {:title "Original" :author "Original Author" :year 2020 :isbn "6666666666"}
          created (db/create-book book)
          response (handlers/update-book-handler (:id created) {:title "Updated" :author "Updated Author" :year 2023 :isbn "7777777777"})]
      (is (= 200 (:status response)))
      (is (= "Updated" (get-in response [:body :title])))
      (is (= 2023 (get-in response [:body :year])))))

  (testing "Update non-existent book"
    (let [response (handlers/update-book-handler 9999 {:title "Updated" :author "Updated Author"})]
      (is (= 404 (:status response)))))

  (testing "Update with missing title"
    (let [book {:title "Test" :author "Author" :year 2020 :isbn "8888888888"}
          created (db/create-book book)
          response (handlers/update-book-handler (:id created) {:author "New Author"})]
      (is (= 400 (:status response)))))

  (testing "Update with invalid ID"
    (let [response (handlers/update-book-handler -1 {:title "Updated"})]
      (is (= 400 (:status response))))))

(deftest test-delete-book-handler
  (reset-db)
  
  (testing "Delete existing book"
    (let [book {:title "To Delete" :author "Delete Author" :year 2024 :isbn "9999999999"}
          created (db/create-book book)
          id (:id created)
          response (handlers/delete-book-handler id)]
      (is (= 204 (:status response)))
      (is (nil? (db/get-book id)))))

  (testing "Delete non-existent book"
    (let [response (handlers/delete-book-handler 9999)]
      (is (= 404 (:status response)))))

  (testing "Delete with invalid ID"
    (let [response (handlers/delete-book-handler -1)]
      (is (= 400 (:status response)))))

  (testing "Delete book with invalid ID format"
    (let [response (handlers/delete-book-handler "not-a-number")]
      (is (= 400 (:status response))))))
