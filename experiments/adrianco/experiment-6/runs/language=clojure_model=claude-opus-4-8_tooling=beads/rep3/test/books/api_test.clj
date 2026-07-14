(ns books.api-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [books.core :as core]
            [books.db :as db]
            [muuntaja.core :as m]))

;; Each test gets a fresh in-memory database and app handler.
(def ^:dynamic *app* nil)

(defn fresh-app-fixture [f]
  (let [ds (db/make-datasource ":memory:")]
    (db/init-schema! ds)
    (binding [*app* (core/app ds)]
      (f))))

(use-fixtures :each fresh-app-fixture)

(defn json-request
  "Build a Ring request with a JSON-encoded body."
  [method uri body]
  (let [[path query] (clojure.string/split uri #"\?" 2)]
  (cond-> {:request-method method
           :uri path
           :query-string query
           :headers {"accept" "application/json"}}
    body (assoc :headers {"accept" "application/json"
                          "content-type" "application/json"}
                :body (java.io.ByteArrayInputStream.
                       (.getBytes ^String (slurp (m/encode "application/json" body))))))))

(defn decode-body
  "Decode a JSON response body into a Clojure value with keyword keys."
  [response]
  (when-let [b (:body response)]
    (m/decode m/instance "application/json" b)))

(deftest health-check
  (testing "GET /health returns ok"
    (let [resp (*app* (json-request :get "/health" nil))]
      (is (= 200 (:status resp)))
      (is (= "ok" (:status (decode-body resp)))))))

(deftest create-and-get-book
  (testing "POST /books creates a book and GET /books/:id retrieves it"
    (let [resp (*app* (json-request :post "/books"
                                    {:title "The Pragmatic Programmer"
                                     :author "Hunt"
                                     :year 1999
                                     :isbn "978-0201616224"}))
          created (decode-body resp)]
      (is (= 201 (:status resp)))
      (is (= "The Pragmatic Programmer" (:title created)))
      (is (integer? (:id created)))
      (let [got (*app* (json-request :get (str "/books/" (:id created)) nil))]
        (is (= 200 (:status got)))
        (is (= "Hunt" (:author (decode-body got))))))))

(deftest validation-rejects-missing-fields
  (testing "POST /books without title/author returns 400"
    (let [resp (*app* (json-request :post "/books" {:year 2020}))]
      (is (= 400 (:status resp)))
      (let [errors (:errors (decode-body resp))]
        (is (contains? errors :title))
        (is (contains? errors :author))))))

(deftest list-and-filter-by-author
  (testing "GET /books lists all and ?author= filters"
    (*app* (json-request :post "/books" {:title "A" :author "Alice"}))
    (*app* (json-request :post "/books" {:title "B" :author "Bob"}))
    (*app* (json-request :post "/books" {:title "C" :author "Alice"}))
    (let [all (decode-body (*app* (json-request :get "/books" nil)))]
      (is (= 3 (count all))))
    (let [alice (decode-body (*app* (json-request :get "/books?author=Alice" nil)))]
      (is (= 2 (count alice)))
      (is (every? #(= "Alice" (:author %)) alice)))))

(deftest update-book
  (testing "PUT /books/:id updates an existing book"
    (let [created (decode-body (*app* (json-request :post "/books"
                                                    {:title "Old" :author "Someone"})))
          id (:id created)
          resp (*app* (json-request :put (str "/books/" id)
                                    {:title "New" :author "Someone" :year 2024}))
          updated (decode-body resp)]
      (is (= 200 (:status resp)))
      (is (= "New" (:title updated)))
      (is (= 2024 (:year updated))))))

(deftest delete-book
  (testing "DELETE /books/:id removes the book"
    (let [created (decode-body (*app* (json-request :post "/books"
                                                    {:title "Doomed" :author "X"})))
          id (:id created)
          del (*app* (json-request :delete (str "/books/" id) nil))]
      (is (= 204 (:status del)))
      (is (= 404 (:status (*app* (json-request :get (str "/books/" id) nil))))))))

(deftest missing-book-returns-404
  (testing "GET /books/:id for unknown id returns 404"
    (is (= 404 (:status (*app* (json-request :get "/books/99999" nil)))))))
