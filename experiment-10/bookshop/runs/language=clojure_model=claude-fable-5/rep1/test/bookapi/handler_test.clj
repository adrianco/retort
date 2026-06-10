(ns bookapi.handler-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [cheshire.core :as json]
            [ring.mock.request :as mock]
            [bookapi.db :as db]
            [bookapi.handler :as handler])
  (:import [java.io File]))

(def ^:dynamic *app* nil)

(defn- with-test-app [f]
  (let [tmp (File/createTempFile "books-test" ".db")
        ds (db/make-datasource (.getAbsolutePath tmp))]
    (db/init! ds)
    (binding [*app* (handler/app ds)]
      (try
        (f)
        (finally
          (.delete tmp))))))

(use-fixtures :each with-test-app)

(defn- parse-body [response]
  (let [body (:body response)]
    (json/parse-string (if (string? body) body (slurp body)) true)))

(defn- create-book! [book]
  (*app* (-> (mock/request :post "/books")
             (mock/json-body book))))

(deftest health-check
  (let [response (*app* (mock/request :get "/health"))]
    (is (= 200 (:status response)))
    (is (= {:status "ok"} (parse-body response)))))

(deftest create-and-get-book
  (testing "POST /books creates a book"
    (let [response (create-book! {:title "Release It!"
                                  :author "Michael Nygard"
                                  :year 2018
                                  :isbn "978-1680502398"})
          body (parse-body response)]
      (is (= 201 (:status response)))
      (is (pos-int? (:id body)))
      (is (= "Release It!" (:title body)))
      (is (= "Michael Nygard" (:author body)))
      (is (= 2018 (:year body)))
      (is (= "978-1680502398" (:isbn body)))

      (testing "GET /books/{id} returns the created book"
        (let [get-response (*app* (mock/request :get (str "/books/" (:id body))))]
          (is (= 200 (:status get-response)))
          (is (= body (parse-body get-response))))))))

(deftest create-book-validation
  (testing "missing title and author returns 400 with errors"
    (let [response (create-book! {:year 2020})
          body (parse-body response)]
      (is (= 400 (:status response)))
      (is (= 2 (count (:errors body))))))
  (testing "blank title is rejected"
    (let [response (create-book! {:title "  " :author "Someone"})]
      (is (= 400 (:status response)))))
  (testing "non-integer year is rejected"
    (let [response (create-book! {:title "T" :author "A" :year "1999"})]
      (is (= 400 (:status response))))))

(deftest list-books-with-author-filter
  (create-book! {:title "Book One" :author "Alice"})
  (create-book! {:title "Book Two" :author "Bob"})
  (create-book! {:title "Book Three" :author "Alice"})
  (testing "GET /books returns all books"
    (let [response (*app* (mock/request :get "/books"))
          body (parse-body response)]
      (is (= 200 (:status response)))
      (is (= 3 (count body)))))
  (testing "GET /books?author= filters by author"
    (let [response (*app* (mock/request :get "/books" {:author "Alice"}))
          body (parse-body response)]
      (is (= 200 (:status response)))
      (is (= 2 (count body)))
      (is (every? #(= "Alice" (:author %)) body)))))

(deftest update-book
  (let [created (parse-body (create-book! {:title "Old Title" :author "Old Author"}))
        id (:id created)]
    (testing "PUT /books/{id} updates the book"
      (let [response (*app* (-> (mock/request :put (str "/books/" id))
                                (mock/json-body {:title "New Title"
                                                 :author "New Author"
                                                 :year 2021})))
            body (parse-body response)]
        (is (= 200 (:status response)))
        (is (= "New Title" (:title body)))
        (is (= "New Author" (:author body)))
        (is (= 2021 (:year body)))))
    (testing "PUT with invalid payload returns 400"
      (let [response (*app* (-> (mock/request :put (str "/books/" id))
                                (mock/json-body {:title ""})))]
        (is (= 400 (:status response)))))
    (testing "PUT to a missing book returns 404"
      (let [response (*app* (-> (mock/request :put "/books/99999")
                                (mock/json-body {:title "X" :author "Y"})))]
        (is (= 404 (:status response)))))))

(deftest delete-book
  (let [created (parse-body (create-book! {:title "Doomed" :author "Nobody"}))
        id (:id created)]
    (testing "DELETE /books/{id} removes the book"
      (let [response (*app* (mock/request :delete (str "/books/" id)))]
        (is (= 204 (:status response))))
      (let [response (*app* (mock/request :get (str "/books/" id)))]
        (is (= 404 (:status response)))))
    (testing "DELETE on a missing book returns 404"
      (let [response (*app* (mock/request :delete "/books/99999"))]
        (is (= 404 (:status response)))))))

(deftest get-missing-or-invalid-id
  (testing "GET /books/{id} with unknown id returns 404"
    (is (= 404 (:status (*app* (mock/request :get "/books/424242"))))))
  (testing "GET /books/{id} with non-numeric id returns 404"
    (is (= 404 (:status (*app* (mock/request :get "/books/abc")))))))
