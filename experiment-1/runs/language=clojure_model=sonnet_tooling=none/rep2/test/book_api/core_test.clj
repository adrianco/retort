(ns book-api.core-test
  (:require [clojure.test :refer [deftest is use-fixtures testing]]
            [ring.mock.request :as mock]
            [cheshire.core :as json]
            [next.jdbc :as jdbc]
            [book-api.core :refer [app]]
            [book-api.db :as db]))

;; ---------------------------------------------------------------------------
;; Test fixture — use a fresh file-based SQLite DB for each test
;; ---------------------------------------------------------------------------

(def ^:private test-db-path "/tmp/book_api_test.db")

(defn- setup-test-db! []
  (reset! db/ds (jdbc/get-datasource {:dbtype "sqlite" :dbname test-db-path}))
  (jdbc/execute! @db/ds ["DROP TABLE IF EXISTS books"])
  (db/init-db!))

(defn- teardown-test-db! []
  (.delete (java.io.File. test-db-path)))

(use-fixtures :each
  (fn [f]
    (setup-test-db!)
    (try (f) (finally (teardown-test-db!)))))

;; ---------------------------------------------------------------------------
;; Helper
;; ---------------------------------------------------------------------------

(defn- parse-body [response]
  (json/parse-string (:body response) true))

(defn- json-post [path body]
  (app (-> (mock/request :post path)
           (mock/json-body body))))

;; ---------------------------------------------------------------------------
;; Health check
;; ---------------------------------------------------------------------------

(deftest test-health-check
  (let [resp (app (mock/request :get "/health"))]
    (is (= 200 (:status resp)))
    (is (= {:status "ok"} (parse-body resp)))))

;; ---------------------------------------------------------------------------
;; Create book
;; ---------------------------------------------------------------------------

(deftest test-create-book-success
  (let [resp (json-post "/books" {:title "Clojure for the Brave and True"
                                  :author "Daniel Higginbotham"
                                  :year   2015
                                  :isbn   "978-1-59327-591-4"})]
    (is (= 201 (:status resp)))
    (let [body (parse-body resp)]
      (is (integer? (:id body)))
      (is (= "Clojure for the Brave and True" (:title body)))
      (is (= "Daniel Higginbotham" (:author body)))
      (is (= 2015 (:year body))))))

(deftest test-create-book-missing-title
  (let [resp (json-post "/books" {:author "Someone" :year 2020})]
    (is (= 400 (:status resp)))
    (is (= "title is required" (:error (parse-body resp))))))

(deftest test-create-book-missing-author
  (let [resp (json-post "/books" {:title "Some Title" :year 2020})]
    (is (= 400 (:status resp)))
    (is (= "author is required" (:error (parse-body resp))))))

;; ---------------------------------------------------------------------------
;; List books
;; ---------------------------------------------------------------------------

(deftest test-list-books-empty
  (let [resp (app (mock/request :get "/books"))]
    (is (= 200 (:status resp)))
    (is (= [] (parse-body resp)))))

(deftest test-list-books-returns-all
  (db/create-book! {:title "Book A" :author "Author One" :year 2020 :isbn "111"})
  (db/create-book! {:title "Book B" :author "Author Two" :year 2021 :isbn "222"})
  (let [resp (app (mock/request :get "/books"))
        body (parse-body resp)]
    (is (= 200 (:status resp)))
    (is (= 2 (count body)))))

(deftest test-list-books-author-filter
  (db/create-book! {:title "Book A" :author "Alice Smith" :year 2020 :isbn "111"})
  (db/create-book! {:title "Book B" :author "Bob Jones"   :year 2021 :isbn "222"})
  (let [resp (app (mock/request :get "/books?author=Alice"))
        body (parse-body resp)]
    (is (= 200 (:status resp)))
    (is (= 1 (count body)))
    (is (= "Alice Smith" (:author (first body))))))

;; ---------------------------------------------------------------------------
;; Get single book
;; ---------------------------------------------------------------------------

(deftest test-get-book-found
  (let [book (db/create-book! {:title "Specific Book" :author "Author" :year 2022 :isbn "333"})
        resp (app (mock/request :get (str "/books/" (:id book))))]
    (is (= 200 (:status resp)))
    (is (= "Specific Book" (:title (parse-body resp))))))

(deftest test-get-book-not-found
  (let [resp (app (mock/request :get "/books/9999"))]
    (is (= 404 (:status resp)))
    (is (= "Book not found" (:error (parse-body resp))))))

;; ---------------------------------------------------------------------------
;; Update book
;; ---------------------------------------------------------------------------

(deftest test-update-book-success
  (let [book (db/create-book! {:title "Old Title" :author "Author" :year 2020 :isbn "444"})
        resp (app (-> (mock/request :put (str "/books/" (:id book)))
                      (mock/json-body {:title "New Title" :author "Author" :year 2021 :isbn "444"})))]
    (is (= 200 (:status resp)))
    (is (= "New Title" (:title (parse-body resp))))))

(deftest test-update-book-not-found
  (let [resp (app (-> (mock/request :put "/books/9999")
                      (mock/json-body {:title "Title" :author "Author"})))]
    (is (= 404 (:status resp)))))

;; ---------------------------------------------------------------------------
;; Delete book
;; ---------------------------------------------------------------------------

(deftest test-delete-book-success
  (let [book (db/create-book! {:title "To Delete" :author "Author" :year 2020 :isbn "555"})
        resp (app (mock/request :delete (str "/books/" (:id book))))]
    (is (= 204 (:status resp)))
    ;; confirm it is gone
    (is (= 404 (:status (app (mock/request :get (str "/books/" (:id book)))))))))

(deftest test-delete-book-not-found
  (let [resp (app (mock/request :delete "/books/9999"))]
    (is (= 404 (:status resp)))))
