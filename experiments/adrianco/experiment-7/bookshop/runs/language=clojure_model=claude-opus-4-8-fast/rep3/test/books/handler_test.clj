(ns books.handler-test
  "Integration tests exercising the Ring handler against an in-memory SQLite DB."
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [books.db :as db]
            [books.handler :as handler]
            [cheshire.core :as json])
  (:import [java.io ByteArrayInputStream]))

(def ^:dynamic *handler* nil)

(defn handler-fixture
  "Provide a fresh in-memory database and handler for each test."
  [f]
  (let [ds (db/make-datasource ":memory:")]
    (db/init-schema! ds)
    (binding [*handler* (handler/make-handler ds)]
      (f))))

(use-fixtures :each handler-fixture)

(defn- body-stream [m]
  (ByteArrayInputStream. (.getBytes (json/generate-string m))))

(defn- request
  "Issue a request to the handler. opts may include :body (a map) and :query-string."
  [method uri & {:keys [body query-string]}]
  (let [resp (*handler* (cond-> {:request-method method :uri uri}
                          body         (assoc :body (body-stream body))
                          query-string (assoc :query-string query-string)))]
    (update resp :body #(when (and % (not= "" %)) (json/parse-string % true)))))

(deftest health-check
  (testing "health endpoint reports ok"
    (let [resp (request :get "/health")]
      (is (= 200 (:status resp)))
      (is (= "ok" (get-in resp [:body :status]))))))

(deftest create-and-fetch-book
  (testing "a created book can be fetched by id"
    (let [created (request :post "/books"
                           :body {:title "Clojure" :author "Hickey" :year 2007 :isbn "123"})
          id      (get-in created [:body :id])]
      (is (= 201 (:status created)))
      (is (some? id))
      (is (= "Clojure" (get-in created [:body :title])))
      (let [fetched (request :get (str "/books/" id))]
        (is (= 200 (:status fetched)))
        (is (= "Hickey" (get-in fetched [:body :author])))))))

(deftest validation-rejects-missing-fields
  (testing "missing title and author yields a 400 with errors"
    (let [resp (request :post "/books" :body {:year 2020})]
      (is (= 400 (:status resp)))
      (is (= #{"title is required" "author is required"}
             (set (get-in resp [:body :errors])))))))

(deftest list-and-filter-by-author
  (testing "listing supports an author filter"
    (request :post "/books" :body {:title "A" :author "Ann"})
    (request :post "/books" :body {:title "B" :author "Bob"})
    (request :post "/books" :body {:title "C" :author "Ann"})
    (let [all (request :get "/books")]
      (is (= 200 (:status all)))
      (is (= 3 (count (:body all)))))
    (let [filtered (request :get "/books" :query-string "author=Ann")]
      (is (= 200 (:status filtered)))
      (is (= 2 (count (:body filtered))))
      (is (every? #(= "Ann" (:author %)) (:body filtered))))))

(deftest update-book
  (testing "an existing book can be updated"
    (let [created (request :post "/books" :body {:title "Old" :author "Auth"})
          id      (get-in created [:body :id])
          updated (request :put (str "/books/" id)
                           :body {:title "New" :author "Auth" :year 2024})]
      (is (= 200 (:status updated)))
      (is (= "New" (get-in updated [:body :title])))
      (is (= 2024 (get-in updated [:body :year]))))))

(deftest update-missing-book-404
  (testing "updating a non-existent book returns 404"
    (let [resp (request :put "/books/999" :body {:title "X" :author "Y"})]
      (is (= 404 (:status resp))))))

(deftest delete-book
  (testing "a book can be deleted and is then absent"
    (let [created (request :post "/books" :body {:title "Doomed" :author "Auth"})
          id      (get-in created [:body :id])
          del     (request :delete (str "/books/" id))]
      (is (= 204 (:status del)))
      (is (= 404 (:status (request :get (str "/books/" id))))))))

(deftest get-missing-book-404
  (testing "fetching an unknown id returns 404"
    (is (= 404 (:status (request :get "/books/424242"))))))
