(ns bookapi.handler-test
  (:require [bookapi.db :as db]
            [bookapi.handler :as handler]
            [cheshire.core :as json]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing use-fixtures]]
            [ring.mock.request :as mock]))

(def ^:dynamic *app* nil)

(defn- with-test-app [f]
  (let [db-file (java.io.File/createTempFile "bookapi-test" ".db")
        ds      (db/make-datasource (.getAbsolutePath db-file))]
    (db/init! ds)
    (binding [*app* (handler/make-app ds)]
      (try
        (f)
        (finally
          (io/delete-file db-file true))))))

(use-fixtures :each with-test-app)

(defn- json-request [method uri body]
  (-> (mock/request method uri)
      (mock/content-type "application/json")
      (mock/body (json/generate-string body))))

(defn- parse [response]
  (json/parse-string (:body response) true))

(defn- create-book! [book]
  (*app* (json-request :post "/books" book)))

(deftest health-check
  (let [response (*app* (mock/request :get "/health"))]
    (is (= 200 (:status response)))
    (is (= {:status "ok"} (parse response)))))

(deftest create-and-get-book
  (testing "POST /books creates a book"
    (let [response (create-book! {:title  "SICP"
                                  :author "Abelson & Sussman"
                                  :year   1985
                                  :isbn   "978-0262510875"})
          book     (parse response)]
      (is (= 201 (:status response)))
      (is (pos? (:id book)))
      (is (= "SICP" (:title book)))
      (is (= "Abelson & Sussman" (:author book)))
      (is (= 1985 (:year book)))

      (testing "GET /books/:id returns the created book"
        (let [get-response (*app* (mock/request :get (str "/books/" (:id book))))]
          (is (= 200 (:status get-response)))
          (is (= book (parse get-response))))))))

(deftest validation-errors
  (testing "missing title is rejected"
    (let [response (create-book! {:author "Anonymous"})]
      (is (= 400 (:status response)))
      (is (re-find #"title" (:error (parse response))))))
  (testing "missing author is rejected"
    (let [response (create-book! {:title "Untitled"})]
      (is (= 400 (:status response)))
      (is (re-find #"author" (:error (parse response))))))
  (testing "malformed JSON is rejected"
    (let [response (*app* (-> (mock/request :post "/books")
                              (mock/content-type "application/json")
                              (mock/body "{not json")))]
      (is (= 400 (:status response))))))

(deftest list-books-with-author-filter
  (create-book! {:title "Clojure for the Brave and True" :author "Daniel Higginbotham"})
  (create-book! {:title "The Joy of Clojure" :author "Michael Fogus"})
  (create-book! {:title "Functional Programming Patterns" :author "Michael Fogus"})
  (testing "GET /books lists everything"
    (let [response (*app* (mock/request :get "/books"))]
      (is (= 200 (:status response)))
      (is (= 3 (count (parse response))))))
  (testing "GET /books?author= filters by author"
    (let [response (*app* (mock/request :get "/books" {:author "Michael Fogus"}))
          books    (parse response)]
      (is (= 200 (:status response)))
      (is (= 2 (count books)))
      (is (every? #(= "Michael Fogus" (:author %)) books)))))

(deftest update-book
  (let [book (parse (create-book! {:title "Draft" :author "Someone" :year 2020}))]
    (testing "PUT /books/:id updates the book"
      (let [response (*app* (json-request :put (str "/books/" (:id book))
                                          {:title  "Final"
                                           :author "Someone"
                                           :year   2021
                                           :isbn   "123-456"}))
            updated  (parse response)]
        (is (= 200 (:status response)))
        (is (= "Final" (:title updated)))
        (is (= 2021 (:year updated)))
        (is (= "123-456" (:isbn updated)))))
    (testing "PUT validates required fields"
      (let [response (*app* (json-request :put (str "/books/" (:id book))
                                          {:title "No author"}))]
        (is (= 400 (:status response)))))
    (testing "PUT on a missing book returns 404"
      (let [response (*app* (json-request :put "/books/99999"
                                          {:title "X" :author "Y"}))]
        (is (= 404 (:status response)))))))

(deftest delete-book
  (let [book (parse (create-book! {:title "Ephemeral" :author "Gone Soon"}))]
    (testing "DELETE /books/:id removes the book"
      (is (= 204 (:status (*app* (mock/request :delete (str "/books/" (:id book)))))))
      (is (= 404 (:status (*app* (mock/request :get (str "/books/" (:id book))))))))
    (testing "DELETE on a missing book returns 404"
      (is (= 404 (:status (*app* (mock/request :delete "/books/99999"))))))))

(deftest get-missing-book
  (is (= 404 (:status (*app* (mock/request :get "/books/12345")))))
  (is (= 404 (:status (*app* (mock/request :get "/books/not-a-number"))))))
