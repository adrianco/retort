(ns books.api-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [books.core :as core]
            [books.db :as db]
            [cheshire.core :as json]
            [ring.mock.request :as mock]))

;; A fresh in-memory database (and handler) per test.
(def ^:dynamic *app* nil)

(defn fresh-app-fixture [f]
  (let [ds (db/datasource ":memory:")]
    (db/init! ds)
    (binding [*app* (core/app ds)]
      (f))))

(use-fixtures :each fresh-app-fixture)

(defn- json-body [m]
  (-> (mock/request :post "/books")
      (mock/content-type "application/json")
      (mock/body (json/generate-string m))))

(defn- parse [response]
  (when (seq (:body response))
    (json/parse-string (:body response) true)))

(defn- post-book [m]
  (*app* (json-body m)))

(deftest health-check
  (testing "GET /health returns 200 ok"
    (let [resp (*app* (mock/request :get "/health"))]
      (is (= 200 (:status resp)))
      (is (= "ok" (:status (parse resp)))))))

(deftest create-and-fetch-book
  (testing "POST /books creates a book and returns 201 with an id"
    (let [resp (post-book {:title "Dune" :author "Herbert" :year 1965 :isbn "111"})
          book (parse resp)]
      (is (= 201 (:status resp)))
      (is (some? (:id book)))
      (is (= "Dune" (:title book)))
      (testing "GET /books/{id} returns the created book"
        (let [get-resp (*app* (mock/request :get (str "/books/" (:id book))))]
          (is (= 200 (:status get-resp)))
          (is (= "Herbert" (:author (parse get-resp)))))))))

(deftest validation-rejects-missing-fields
  (testing "POST /books without title/author returns 400"
    (let [resp (post-book {:year 2000})]
      (is (= 400 (:status resp)))
      (is (= #{"title is required" "author is required"}
             (set (:errors (parse resp))))))))

(deftest list-and-filter-by-author
  (testing "GET /books lists all and supports ?author= filter"
    (post-book {:title "A" :author "Asimov"})
    (post-book {:title "B" :author "Herbert"})
    (post-book {:title "C" :author "Asimov"})
    (let [all (parse (*app* (mock/request :get "/books")))]
      (is (= 3 (count all))))
    (let [asimov (parse (*app* (mock/request :get "/books?author=Asimov")))]
      (is (= 2 (count asimov)))
      (is (every? #(= "Asimov" (:author %)) asimov)))))

(deftest update-book
  (testing "PUT /books/{id} updates fields"
    (let [book (parse (post-book {:title "Old" :author "Author"}))
          resp (*app* (-> (mock/request :put (str "/books/" (:id book)))
                          (mock/content-type "application/json")
                          (mock/body (json/generate-string
                                       {:title "New" :author "Author" :year 2020}))))]
      (is (= 200 (:status resp)))
      (is (= "New" (:title (parse resp))))
      (is (= 2020 (:year (parse resp)))))))

(deftest delete-book
  (testing "DELETE /books/{id} removes the book"
    (let [book (parse (post-book {:title "Temp" :author "Author"}))
          del  (*app* (mock/request :delete (str "/books/" (:id book))))]
      (is (= 204 (:status del)))
      (let [get-resp (*app* (mock/request :get (str "/books/" (:id book))))]
        (is (= 404 (:status get-resp)))))))

(deftest unknown-book-returns-404
  (testing "GET /books/{id} for a missing id returns 404"
    (let [resp (*app* (mock/request :get "/books/9999"))]
      (is (= 404 (:status resp))))))
