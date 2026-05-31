(ns books.handler-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [cheshire.core :as json]
            [books.db :as db]
            [books.handler :as handler]
            [ring.mock.request :as mock]))

;; Each test run gets its own temporary SQLite file so tests are isolated.
(def ^:dynamic *app* nil)

(defn with-app [f]
  (let [tmp (java.io.File/createTempFile "books-test" ".db")
        ds  (db/make-datasource (.getAbsolutePath tmp))]
    (try
      (db/init-schema! ds)
      (binding [*app* (handler/app-routes ds)]
        (f))
      (finally
        (.delete tmp)))))

(use-fixtures :each with-app)

(defn- json-request
  ([method uri] (json-request method uri nil))
  ([method uri body]
   (cond-> (mock/request method uri)
     body (-> (mock/content-type "application/json")
              (mock/body (json/generate-string body))))))

(defn- parse-body [response]
  (when (seq (:body response))
    (json/parse-string (:body response) true)))

(defn- post-book [book]
  (parse-body (*app* (json-request :post "/books" book))))

(deftest health-check
  (testing "health endpoint returns ok"
    (let [resp (*app* (json-request :get "/health"))]
      (is (= 200 (:status resp)))
      (is (= {:status "ok"} (parse-body resp))))))

(deftest create-book-success
  (testing "creating a valid book returns 201 with an id"
    (let [resp (*app* (json-request :post "/books"
                                    {:title "Clojure" :author "Rich"
                                     :year 2007 :isbn "111"}))
          body (parse-body resp)]
      (is (= 201 (:status resp)))
      (is (some? (:id body)))
      (is (= "Clojure" (:title body)))
      (is (= "Rich" (:author body)))
      (is (= 2007 (:year body))))))

(deftest create-book-validation
  (testing "missing title and author returns 400 with errors"
    (let [resp (*app* (json-request :post "/books" {:year 2020}))
          body (parse-body resp)]
      (is (= 400 (:status resp)))
      (is (some #{"title is required"} (:errors body)))
      (is (some #{"author is required"} (:errors body)))))
  (testing "missing only author returns 400"
    (let [resp (*app* (json-request :post "/books" {:title "X"}))]
      (is (= 400 (:status resp))))))

(deftest list-and-filter-books
  (post-book {:title "A" :author "Alice"})
  (post-book {:title "B" :author "Bob"})
  (post-book {:title "C" :author "Alice"})
  (testing "list all books"
    (let [resp (*app* (json-request :get "/books"))
          body (parse-body resp)]
      (is (= 200 (:status resp)))
      (is (= 3 (count body)))))
  (testing "filter by author"
    (let [resp (*app* (json-request :get "/books?author=Alice"))
          body (parse-body resp)]
      (is (= 200 (:status resp)))
      (is (= 2 (count body)))
      (is (every? #(= "Alice" (:author %)) body)))))

(deftest get-single-book
  (let [created (post-book {:title "Solo" :author "Han"})
        id (:id created)]
    (testing "fetch existing book"
      (let [resp (*app* (json-request :get (str "/books/" id)))]
        (is (= 200 (:status resp)))
        (is (= "Solo" (:title (parse-body resp))))))
    (testing "fetch missing book returns 404"
      (let [resp (*app* (json-request :get "/books/99999"))]
        (is (= 404 (:status resp)))))))

(deftest update-book-test
  (let [created (post-book {:title "Old" :author "Auth" :year 1990})
        id (:id created)]
    (testing "update existing book"
      (let [resp (*app* (json-request :put (str "/books/" id)
                                      {:title "New" :author "Auth" :year 2000}))
            body (parse-body resp)]
        (is (= 200 (:status resp)))
        (is (= "New" (:title body)))
        (is (= 2000 (:year body)))))
    (testing "update missing book returns 404"
      (let [resp (*app* (json-request :put "/books/99999"
                                      {:title "X" :author "Y"}))]
        (is (= 404 (:status resp)))))
    (testing "update with invalid payload returns 400"
      (let [resp (*app* (json-request :put (str "/books/" id) {:title ""}))]
        (is (= 400 (:status resp)))))))

(deftest delete-book-test
  (let [created (post-book {:title "Doomed" :author "Auth"})
        id (:id created)]
    (testing "delete existing book"
      (let [resp (*app* (json-request :delete (str "/books/" id)))]
        (is (= 200 (:status resp))))
      (let [resp (*app* (json-request :get (str "/books/" id)))]
        (is (= 404 (:status resp)))))
    (testing "delete missing book returns 404"
      (let [resp (*app* (json-request :delete "/books/99999"))]
        (is (= 404 (:status resp)))))))
