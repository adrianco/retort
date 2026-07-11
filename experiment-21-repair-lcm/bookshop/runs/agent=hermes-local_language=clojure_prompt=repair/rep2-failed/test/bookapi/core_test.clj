(ns bookapi.core-test
  (:require [clojure.test :refer :all]
            [bookapi.db :as db]
            [bookapi.routes :as routes]
            [clojure.java.io :as io]
            [clojure.string :as str])
  (:import [java.io File]))

(defn- reset-db []
  ;; Remove existing db file and reinitialize
  (let [f (File. "books.db")]
    (when (.exists f) (.delete f)))
  (db/init-db!))

(defn- random-port []
  (+ 10000 (mod (System/currentTimeMillis) 50000)))

(defn- run-test-app []
  (reset-db)
  routes/app)

(deftest health-check-test
  (reset-db)
  (let [response ((run-test-app) {:request-method :get :uri "/health"})]
    (is (= 200 (:status response)))
    (is (= "ok" (-> response :body :status)))))

(deftest create-book-success-test
  (reset-db)
  (let [response ((run-test-app)
                  {:request-method :post
                   :uri "/books"
                   :body {:title "The Great Gatsby"
                          :author "F. Scott Fitzgerald"
                          :year 1925
                          :isbn "978-0743273565"}})]
    (is (= 201 (:status response)))
    (is (= "The Great Gatsby" (-> response :body :title)))
    (is (= "F. Scott Fitzgerald" (-> response :body :author)))
    (is (= 1925 (-> response :body :year)))
    (is (= "978-0743273565" (-> response :body :isbn)))))

(deftest create-book-validation-test
  (reset-db)
  ;; Missing title
  (let [response ((run-test-app)
                  {:request-method :post
                   :uri "/books"
                   :body {:author "Someone" :year 2000}})]
    (is (= 400 (:status response)))
    (is (str/includes? (str (-> response :body :error)) "title")))
  ;; Missing author
  (let [response ((run-test-app)
                  {:request-method :post
                   :uri "/books"
                   :body {:title "Some Book" :year 2000}})]
    (is (= 400 (:status response)))
    (is (str/includes? (str (-> response :body :error)) "author"))))

(deftest list-books-test
  (reset-db)
  ;; Create some books
  ((run-test-app)
   {:request-method :post
    :uri "/books"
    :body {:title "Book A" :author "Author One" :year 2001}})
  ((run-test-app)
   {:request-method :post
    :uri "/books"
    :body {:title "Book B" :author "Author One" :year 2002}})
  ((run-test-app)
   {:request-method :post
    :uri "/books"
    :body {:title "Book C" :author "Author Two" :year 2003}})
  
  ;; List all
  (let [response ((run-test-app)
                  {:request-method :get
                   :uri "/books"})]
    (is (= 200 (:status response)))
    (is (= 3 (count (-> response :body))))))

(deftest list-books-author-filter-test
  (reset-db)
  ((run-test-app)
   {:request-method :post
    :uri "/books"
    :body {:title "Book A" :author "Author One" :year 2001}})
  ((run-test-app)
   {:request-method :post
    :uri "/books"
    :body {:title "Book B" :author "Author One" :year 2002}})
  ((run-test-app)
   {:request-method :post
    :uri "/books"
    :body {:title "Book C" :author "Author Two" :year 2003}})
  
  ;; Filter by author
  (let [response ((run-test-app)
                  {:request-method :get
                   :uri "/books"
                   :query-params {"author" "Author One"}})]
    (is (= 200 (:status response)))
    (is (= 2 (count (-> response :body))))
    (is (every? #(= "Author One" (-> % :author)) (-> response :body)))))

(deftest get-book-by-id-test
  (reset-db)
  (let [create-response ((run-test-app)
                         {:request-method :post
                          :uri "/books"
                          :body {:title "Hobbit" :author "Tolkien" :year 1937}})
        book-id (-> create-response :body :id)
        response ((run-test-app)
                  {:request-method :get
                   :uri (str "/books/" book-id)})]
    (is (= 200 (:status response)))
    (is (= "Hobbit" (-> response :body :title)))
    (is (= "Tolkien" (-> response :body :author)))))

(deftest get-book-not-found-test
  (reset-db)
  (let [response ((run-test-app)
                  {:request-method :get
                   :uri "/books/999"})]
    (is (= 404 (:status response)))
    (is (-> response :body :error))))

(deftest update-book-test
  (reset-db)
  (let [create-response ((run-test-app)
                         {:request-method :post
                          :uri "/books"
                          :body {:title "Old Title" :author "Old Author" :year 2000}})
        book-id (-> create-response :body :id)
        update-response ((run-test-app)
                         {:request-method :put
                          :uri (str "/books/" book-id)
                          :body {:title "New Title" :author "New Author" :year 2024}})]
    (is (= 200 (:status update-response)))
    (is (= "New Title" (-> update-response :body :title)))
    (is (= "New Author" (-> update-response :body :author)))
    (is (= 2024 (-> update-response :body :year)))))

(deftest update-book-not-found-test
  (reset-db)
  (let [response ((run-test-app)
                  {:request-method :put
                   :uri "/books/999"
                   :body {:title "Nope"}})]
    (is (= 404 (:status response)))))

(deftest delete-book-test
  (reset-db)
  (let [create-response ((run-test-app)
                         {:request-method :post
                          :uri "/books"
                          :body {:title "To Delete" :author "Author" :year 2000}})
        book-id (-> create-response :body :id)
        delete-response ((run-test-app)
                         {:request-method :delete
                          :uri (str "/books/" book-id)})]
    (is (= 204 (:status delete-response)))
    ;; Verify it's gone
    (let [get-response ((run-test-app)
                        {:request-method :get
                         :uri (str "/books/" book-id)})]
      (is (= 404 (:status get-response))))))

(deftest delete-book-not-found-test
  (reset-db)
  (let [response ((run-test-app)
                  {:request-method :delete
                   :uri "/books/999"})]
    (is (= 404 (:status response)))))

(defn -main []
  (run-all-tests))
