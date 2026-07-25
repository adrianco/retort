(ns book-api.test-routes
  (:require [clojure.test :refer :all]
            [book-api.routes :refer :all]
            [book-api.db :as db]
            [ring.mock.request :refer [request]]))

(use-fixtures :each
  (fn [f]
    (db/init-db)
    (f)))

(defn parse-json [response]
  (cheshire.core/parse-string (:body response) true))

(deftest test-health-endpoint
  (testing "Health endpoint returns status healthy"
    (let [response (app (request :get "/health"))]
      (is (= (:status response) 200))
      (is (= (:status (parse-json response)) "healthy")))))

(deftest test-create-book
  (testing "Create a new book"
    (let [body {:title "New Book" :author "New Author" :year 2024 :isbn "ISBN-001"}
          response (app (request :post "/books" {:body (cheshire.core/generate-string body)}))]
      (is (= (:status response) 201))
      (is (= (:title (parse-json response)) "New Book"))
      (is (= (:author (parse-json response)) "New Author")))))

(deftest test-create-book-validation
  (testing "Validation errors for missing required fields"
    (let [body-no-title {:author "No Title Author" :year 2024 :isbn "ISBN-002"}
          body-no-author {:title "No Author Book" :year 2024 :isbn "ISBN-003"}
          response1 (app (request :post "/books" {:body (cheshire.core/generate-string body-no-title)}))
          response2 (app (request :post "/books" {:body (cheshire.core/generate-string body-no-author)}))]
      (is (= (:status response1) 400))
      (is (= (:status response2) 400)))))

(deftest test-get-all-books
  (testing "Get all books"
    (db/create-book {:title "Book 1" :author "Author 1" :year 2020 :isbn "001"})
    (db/create-book {:title "Book 2" :author "Author 2" :year 2021 :isbn "002"})
    (let [response (app (request :get "/books"))]
      (is (= (:status response) 200))
      (is (>= (count (:body (parse-json response))) 2)))))

(deftest test-get-book-by-id
  (testing "Get a single book by ID"
    (let [book (db/create-book {:title "Get Book" :author "Get Author" :year 2024 :isbn "GET-001"})
          book-id (:id book)
          response (app (request :get (str "/books/" book-id)))]
      (is (= (:status response) 200))
      (is (= (:title (parse-json response)) "Get Book")))))

(deftest test-get-book-not-found
  (testing "Get non-existent book returns 404"
    (let [response (app (request :get "/books/99999"))]
      (is (= (:status response) 404)))))

(deftest test-update-book
  (testing "Update an existing book"
    (let [book (db/create-book {:title "Original" :author "Original Author" :year 2020 :isbn "ORIG-001"})
          book-id (:id book)
          body {:title "Updated Title" :author "Updated Author" :year 2024 :isbn "UPD-001"}
          response (app (request :put (str "/books/" book-id) {:body (cheshire.core/generate-string body)}))]
      (is (= (:status response) 200))
      (is (= (:title (parse-json response)) "Updated Title"))
      (is (= (:author (parse-json response)) "Updated Author")))))

(deftest test-delete-book
  (testing "Delete a book"
    (let [book (db/create-book {:title "Delete Me" :author "Delete Author" :year 2020 :isbn "DEL-001"})
          book-id (:id book)
          response (app (request :delete (str "/books/" book-id)))]
      (is (= (:status response) 204))
      (let [get-response (app (request :get (str "/books/" book-id)))]
        (is (= (:status get-response) 404))))))

(deftest test-get-books-by-author
  (testing "Get books filtered by author"
    (db/create-book {:title "Book A1" :author "Author X" :year 2020 :isbn "AX1"})
    (db/create-book {:title "Book A2" :author "Author X" :year 2021 :isbn "AX2"})
    (db/create-book {:title "Book B1" :author "Author Y" :year 2022 :isbn "AY1"})
    (let [response (app (request :get "/books" {:query-params {:author "Author X"}})]
      (is (= (:status response) 200))
      (is (= (count (:body (parse-json response))) 2)))))
