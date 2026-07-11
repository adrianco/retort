(ns book-api.handler-test
  (:require [clojure.test :refer [deftest is]]
            [book-api.handler :as handler]
            [book-api.db :as db]))

;; Set up and teardown for each test
(defn- setup []
  (db/reset-db!))

(defn- cleanup []
  (db/clear-db!))

(deftest health-check-test
  (let [response (handler/app {:request-method :get :uri "/health"})]
    (is (= 200 (:status response)))))

(deftest create-book-test
  (setup)
  (try
    (let [response (handler/app
                     {:request-method :post
                      :uri "/books"
                      :body "{\"title\":\"The Hobbit\",\"author\":\"J.R.R. Tolkien\",\"year\":1937,\"isbn\":\"978-0-261-10325-4\"}"
                      :headers {"Content-Type" "application/json"}})]
      (is (= 201 (:status response)))
      (let [body (:body response)]
        (is (= "The Hobbit" (:title body)))
        (is (= "J.R.R. Tolkien" (:author body)))
        (is (= 1937 (:year body)))
        (is (= "978-0-261-10325-4" (:isbn body)))
        (is (some? (:id body)))))
    (finally
      (cleanup))))

(deftest create-book-validation-test
  (setup)
  (try
    ;; Missing title
    (let [response (handler/app
                     {:request-method :post
                      :uri "/books"
                      :body "{\"author\":\"Some Author\",\"year\":2020}"
                      :headers {"Content-Type" "application/json"}})]
      (is (= 400 (:status response))))
    ;; Missing author
    (let [response (handler/app
                     {:request-method :post
                      :uri "/books"
                      :body "{\"title\":\"Some Title\",\"year\":2020}"
                      :headers {"Content-Type" "application/json"}})]
      (is (= 400 (:status response))))
    ;; Empty title
    (let [response (handler/app
                     {:request-method :post
                      :uri "/books"
                      :body "{\"title\":\"\",\"author\":\"Some Author\"}"
                      :headers {"Content-Type" "application/json"}})]
      (is (= 400 (:status response))))
    (finally
      (cleanup))))

(deftest list-books-test
  (setup)
  (try
    ;; List empty
    (let [response (handler/app {:request-method :get :uri "/books"})]
      (is (= 200 (:status response)))
      (is (= [] (:books (:body response)))))
    ;; Add some books
    (db/add-book! {:title "The Hobbit" :author "J.R.R. Tolkien" :year 1937 :isbn "978-0-261-10325-4"})
    (db/add-book! {:title "The Lord of the Rings" :author "J.R.R. Tolkien" :year 1954 :isbn "978-0-618-00221-4"})
    (db/add-book! {:title "1984" :author "George Orwell" :year 1949 :isbn "978-0-451-52493-5"})
    ;; List all
    (let [response (handler/app {:request-method :get :uri "/books"})]
      (is (= 200 (:status response)))
      (is (= 3 (count (:books (:body response))))))
    ;; Filter by author
    (let [response (handler/app {:request-method :get
                                  :uri "/books"
                                  :params {:author "J.R.R. Tolkien"}})]
      (is (= 200 (:status response)))
      (is (= 2 (count (:books (:body response))))))
    (finally
      (cleanup))))

(deftest get-book-by-id-test
  (setup)
  (try
    (let [book (db/add-book! {:title "The Hobbit" :author "J.R.R. Tolkien" :year 1937})
          id (:id book)
          response (handler/app {:request-method :get
                                 :uri (str "/books/" id)})]
      (is (= 200 (:status response)))
      (is (= "The Hobbit" (:title (:book (:body response))))))
    ;; Non-existent book
    (let [response (handler/app {:request-method :get :uri "/books/999"})]
      (is (= 404 (:status response))))
    (finally
      (cleanup))))

(deftest update-book-test
  (setup)
  (try
    (let [book (db/add-book! {:title "The Hobbit" :author "J.R.R. Tolkien" :year 1937 :isbn "978-0-261-10325-4"})
          id (:id book)]
      ;; Update title
      (let [response (handler/app
                       {:request-method :put
                        :uri (str "/books/" id)
                        :body "{\"title\":\"The Hobbit (Updated)\"}"
                        :headers {"Content-Type" "application/json"}})]
        (is (= 200 (:status response)))
        (is (= "The Hobbit (Updated)" (:title (:book (:body response))))))
      ;; Non-existent book
      (let [response (handler/app
                       {:request-method :put
                        :uri "/books/999"
                        :body "{\"title\":\"Ghost\"}"
                        :headers {"Content-Type" "application/json"}})]
        (is (= 404 (:status response)))))
    (finally
      (cleanup))))

(deftest delete-book-test
  (setup)
  (try
    (let [book (db/add-book! {:title "The Hobbit" :author "J.R.R. Tolkien" :year 1937})
          id (:id book)]
      ;; Delete
      (let [response (handler/app
                       {:request-method :delete
                        :uri (str "/books/" id)})]
        (is (= 200 (:status response)))
        (is (= "The Hobbit" (:title (:book (:body response))))))
      ;; Try to delete again - should 404
      (let [response (handler/app
                       {:request-method :delete
                        :uri (str "/books/" id)})]
        (is (= 404 (:status response)))))
    (finally
      (cleanup))))

(deftest integration-test
  (setup)
  (try
    ;; Full lifecycle: create, list, get, update, delete
    (let [;; Create
          create-res (handler/app
                       {:request-method :post
                        :uri "/books"
                        :body "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"978-0-441-17271-9\"}"
                        :headers {"Content-Type" "application/json"}})
          id (-> create-res :body :book :id)]
      (is (= 201 (:status create-res)))
      ;; List
      (let [list-res (handler/app {:request-method :get :uri "/books"})]
        (is (= 200 (:status list-res)))
        (is (<= 1 (count (:books (:body list-res))))))
      ;; Get
      (let [get-res (handler/app {:request-method :get
                                  :uri (str "/books/" id)})]
        (is (= 200 (:status get-res)))
        (is (= "Dune" (:title (:book (:body get-res))))))
      ;; Update
      (let [update-res (handler/app
                         {:request-method :put
                          :uri (str "/books/" id)
                          :body "{\"year\":1965,\"isbn\":\"978-0-441-17271-9\"}"
                          :headers {"Content-Type" "application/json"}})]
        (is (= 200 (:status update-res))))
      ;; Delete
      (let [delete-res (handler/app
                         {:request-method :delete
                          :uri (str "/books/" id)})]
        (is (= 200 (:status delete-res))))
      ;; Verify deleted
      (let [get-res (handler/app {:request-method :get
                                  :uri (str "/books/" id)})]
        (is (= 404 (:status get-res)))))
    (finally
      (cleanup))))

(deftest invalid-id-test
  (setup)
  (try
    (let [response (handler/app {:request-method :get :uri "/books/abc"})]
      (is (= 400 (:status response))))
    (finally
      (cleanup))))

(deftest not-found-test
  (let [response (handler/app {:request-method :get :uri "/nonexistent"})]
    (is (= 404 (:status response))))
  (let [response (handler/app {:request-method :post :uri "/nonexistent"})]
    (is (= 404 (:status response)))))
