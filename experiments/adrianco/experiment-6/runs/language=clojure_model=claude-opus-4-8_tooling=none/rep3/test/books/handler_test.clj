(ns books.handler-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [books.db :as db]
            [books.handler :as handler]
            [cheshire.core :as json]
            [next.jdbc :as jdbc])
  (:import [java.io ByteArrayInputStream]))

(def ^:dynamic *app* nil)

(defn fresh-app-fixture
  "Give each test a fresh in-memory database + app."
  [f]
  ;; A single open connection so the in-memory DB persists across all queries.
  (with-open [conn (jdbc/get-connection (db/datasource ":memory:"))]
    (db/init-db! conn)
    (binding [*app* (handler/app conn)]
      (f))))

(use-fixtures :each fresh-app-fixture)

(defn- ->body [m]
  (ByteArrayInputStream. (.getBytes (json/generate-string m) "UTF-8")))

(defn- parse [response]
  (when (:body response)
    (json/parse-string (:body response) true)))

(defn- POST [uri m]
  (*app* {:request-method :post :uri uri :body (->body m)}))

(defn- GET [uri & [query]]
  (*app* (cond-> {:request-method :get :uri uri}
           query (assoc :query-string query))))

(defn- PUT [uri m]
  (*app* {:request-method :put :uri uri :body (->body m)}))

(defn- DELETE [uri]
  (*app* {:request-method :delete :uri uri}))

(deftest health-check
  (let [resp (GET "/health")]
    (is (= 200 (:status resp)))
    (is (= "ok" (:status (parse resp))))))

(deftest create-and-fetch-book
  (testing "POST creates a book and returns 201 with an id"
    (let [resp (POST "/books" {:title "Dune" :author "Herbert" :year 1965 :isbn "123"})
          body (parse resp)]
      (is (= 201 (:status resp)))
      (is (some? (:id body)))
      (is (= "Dune" (:title body)))
      (testing "GET by id returns the created book"
        (let [g (GET (str "/books/" (:id body)))]
          (is (= 200 (:status g)))
          (is (= "Herbert" (:author (parse g)))))))))

(deftest validation-requires-title-and-author
  (testing "missing title and author yields 400 with errors"
    (let [resp (POST "/books" {:year 2000})
          body (parse resp)]
      (is (= 400 (:status resp)))
      (is (some #(= "title is required" %) (:errors body)))
      (is (some #(= "author is required" %) (:errors body))))))

(deftest list-and-author-filter
  (POST "/books" {:title "A" :author "Alice"})
  (POST "/books" {:title "B" :author "Bob"})
  (POST "/books" {:title "C" :author "Alice"})
  (testing "list returns all books"
    (is (= 3 (count (parse (GET "/books"))))))
  (testing "author filter narrows the result"
    (let [books (parse (GET "/books" "author=Alice"))]
      (is (= 2 (count books)))
      (is (every? #(= "Alice" (:author %)) books)))))

(deftest update-book
  (let [created (parse (POST "/books" {:title "Old" :author "Auth"}))
        id      (:id created)
        resp    (PUT (str "/books/" id) {:title "New" :author "Auth" :year 2020})]
    (is (= 200 (:status resp)))
    (is (= "New" (:title (parse resp))))
    (is (= 2020 (:year (parse (GET (str "/books/" id))))))))

(deftest delete-book
  (let [created (parse (POST "/books" {:title "Bye" :author "X"}))
        id      (:id created)]
    (is (= 204 (:status (DELETE (str "/books/" id)))))
    (is (= 404 (:status (GET (str "/books/" id)))))))

(deftest missing-book-yields-404
  (is (= 404 (:status (GET "/books/9999"))))
  (is (= 404 (:status (DELETE "/books/9999"))))
  (is (= 404 (:status (PUT "/books/9999" {:title "T" :author "A"})))))
