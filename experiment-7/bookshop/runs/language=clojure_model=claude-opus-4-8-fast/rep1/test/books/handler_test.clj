(ns books.handler-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [books.db :as db]
            [books.handler :as handler]
            [cheshire.core :as json]
            [next.jdbc :as jdbc])
  (:import [java.io ByteArrayInputStream]))

;; Each test runs against a fresh in-memory SQLite database.
;; A single connection is held open so the :memory: database survives
;; across queries (each new connection would otherwise see an empty db).
(def ^:dynamic *ds* nil)

(use-fixtures :each
  (fn [f]
    (with-open [conn (jdbc/get-connection {:dbtype "sqlite" :dbname ":memory:"})]
      (db/init-db! conn)
      (binding [*ds* conn]
        (f)))))

(defn- body-stream [m]
  (ByteArrayInputStream. (.getBytes (json/generate-string m))))

(defn- request
  "Invoke the app handler and return [status parsed-body]."
  [method uri & {:keys [body params]}]
  (let [resp ((handler/app *ds*)
              (cond-> {:request-method method :uri uri}
                body (assoc :body (body-stream body))
                params (assoc :query-string params)))]
    [(:status resp) (json/parse-string (:body resp) true)]))

(deftest health-check
  (testing "health endpoint returns ok"
    (let [[status body] (request :get "/health")]
      (is (= 200 status))
      (is (= "ok" (:status body))))))

(deftest create-and-get-book
  (testing "POST creates a book and GET retrieves it"
    (let [[status book] (request :post "/books"
                                 :body {:title "Dune" :author "Herbert"
                                        :year 1965 :isbn "123"})]
      (is (= 201 status))
      (is (= "Dune" (:title book)))
      (is (some? (:id book)))
      (let [[gstatus gbook] (request :get (str "/books/" (:id book)))]
        (is (= 200 gstatus))
        (is (= "Herbert" (:author gbook)))))))

(deftest create-validation
  (testing "missing title and author are rejected"
    (let [[status body] (request :post "/books" :body {:year 2000})]
      (is (= 400 status))
      (is (= #{"title is required" "author is required"} (set (:errors body)))))))

(deftest list-and-filter
  (testing "listing supports author filtering"
    (request :post "/books" :body {:title "A" :author "Alice"})
    (request :post "/books" :body {:title "B" :author "Bob"})
    (request :post "/books" :body {:title "C" :author "Alice"})
    (let [[_ all] (request :get "/books")]
      (is (= 3 (count all))))
    (let [[status filtered] (request :get "/books" :params "author=Alice")]
      (is (= 200 status))
      (is (= 2 (count filtered)))
      (is (every? #(= "Alice" (:author %)) filtered)))))

(deftest update-and-delete
  (testing "PUT updates and DELETE removes a book"
    (let [[_ book] (request :post "/books" :body {:title "Old" :author "X"})
          id (:id book)
          [ustatus updated] (request :put (str "/books/" id)
                                     :body {:title "New" :author "Y" :year 2020})]
      (is (= 200 ustatus))
      (is (= "New" (:title updated)))
      (is (= 2020 (:year updated)))
      (let [[dstatus _] (request :delete (str "/books/" id))]
        (is (= 200 dstatus)))
      (let [[gstatus _] (request :get (str "/books/" id))]
        (is (= 404 gstatus))))))

(deftest missing-book-404
  (testing "unknown id returns 404"
    (let [[status _] (request :get "/books/9999")]
      (is (= 404 status)))))
