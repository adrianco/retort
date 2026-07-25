(ns book-api.handler-test
  (:require [clojure.test :refer :all]
            [book-api.handler :as handler]
            [cheshire.core :as json]))

(defn create-request [method path body query-params]
  "Create a Ring request map"
  {:request-method method
   :uri path
   :body body
   :query-params query-params
   :route-params {:id "1"}})

(deftest test-health-endpoint
  (testing "Health check endpoint"
    (let [request {:request-method :get :uri "/health"}
          response (handler/route-request request)]
      (is (= 200 (:status response))
          "Health endpoint should return 200")
      (is (re-find #"application/json" (get-in response [:headers "Content-Type"]))
          "Should return JSON content type")
      (is (= "healthy" (get-in (json/parse-string (:body response)) [:status]))
          "Should return healthy status"))))

(deftest test-books-list-endpoint
  (testing "List all books endpoint"
    (let [request {:request-method :get :uri "/books"}
          response (handler/route-request request)]
      (is (= 200 (:status response))
          "Books list endpoint should return 200")
      (let [body (json/parse-string (:body response))]
        (is (contains? body :books) "Should contain books array")
        (is (contains? body :count) "Should contain count")))))

(deftest test-books-create-endpoint
  (testing "Create book endpoint"
    (let [book {:title "API Test Book" :author "API Test Author" :year 2024 :isbn "1234567890"}
          body (json/generate-string book)
          request {:request-method :post :uri "/books" :body body}
          response (handler/route-request request)]
      (is (= 201 (:status response))
          "Create book should return 201")
      (let [body (json/parse-string (:body response))]
        (is (= "Book created" (get body :message))
            "Should return success message")))))

(deftest test-books-create-validation
  (testing "Create book validation"
    (testing "Missing title"
      (let [book {:author "Author" :year 2024 :isbn "1234567890"}
            body (json/generate-string book)
            request {:request-method :post :uri "/books" :body body}
            response (handler/route-request request)]
        (is (= 400 (:status response))
            "Should return 400 for missing title")
        (let [body (json/parse-string (:body response))]
          (is (contains? body :errors) "Should return errors"))))

    (testing "Missing author"
      (let [book {:title "Title" :year 2024 :isbn "1234567890"}
            body (json/generate-string book)
            request {:request-method :post :uri "/books" :body body}
            response (handler/route-request request)]
      (is (= 400 (:status response))
          "Should return 400 for missing author")))))

(deftest test-books-get-by-id
  (testing "Get book by ID endpoint"
    (let [request {:request-method :get :uri "/books/1"}
          response (handler/route-request request)]
      (is (= 404 (:status response))
          "Should return 404 when book doesn't exist"))))

(deftest test-books-update-endpoint
  (testing "Update book endpoint"
    (let [book {:title "Original" :author "Original Author" :year 2020 :isbn "1111111111"}
          create-body (json/generate-string book)
          create-request {:request-method :post :uri "/books" :body create-body}
          create-response (handler/route-request create-request)]
      (is (= 201 (:status create-response))
          "Create should succeed")
      
      (let [updated-book {:title "Updated" :author "Updated Author" :year 2024 :isbn "2222222222"}
            update-body (json/generate-string updated-book)
            update-request {:request-method :put :uri "/books/1" :body update-body}
            update-response (handler/route-request update-request)]
        (is (= 200 (:status update-response))
            "Update should succeed")))))

(deftest test-books-delete-endpoint
  (testing "Delete book endpoint"
    (let [book {:title "To Delete" :author "Delete Author" :year 2020 :isbn "3333333333"}
          create-body (json/generate-string book)
          create-request {:request-method :post :uri "/books" :body create-body}
          create-response (handler/route-request create-request)]
      (is (= 201 (:status create-response))
          "Create should succeed")
      
      (let [delete-request {:request-method :delete :uri "/books/1"}
            delete-response (handler/route-request delete-request)]
        (is (= 204 (:status delete-response))
            "Delete should succeed")))))

(deftest test-books-author-filter
  (testing "Filter books by author"
    (let [book1 {:title "Book One" :author "Author One" :year 2020 :isbn "4444444441"}
          book2 {:title "Book Two" :author "Author Two" :year 2021 :isbn "4444444442"}
          book3 {:title "Book Three" :author "Author One" :year 2022 :isbn "4444444443"}
          create-body1 (json/generate-string book1)
          create-body2 (json/generate-string book2)
          create-body3 (json/generate-string book3)
          create-request1 {:request-method :post :uri "/books" :body create-body1}
          create-request2 {:request-method :post :uri "/books" :body create-body2}
          create-request3 {:request-method :post :uri "/books" :body create-body3}
          create-response1 (handler/route-request create-request1)
          create-response2 (handler/route-request create-request2)
          create-response3 (handler/route-request create-request3)]
      (is (= 201 (:status create-response1)) "Create book 1 should succeed")
      (is (= 201 (:status create-response2)) "Create book 2 should succeed")
      (is (= 201 (:status create-response3)) "Create book 3 should succeed")
      
      (let [filter-request {:request-method :get :uri "/books" :query-params {:author "Author One"}}
            filter-response (handler/route-request filter-request)]
        (is (= 200 (:status filter-response))
            "Filter endpoint should succeed")
        (let [body (json/parse-string (:body filter-response))]
          (is (= 2 (:count body))
              "Should return 2 books by Author One")))))
