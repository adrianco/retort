(ns books.handler-test
  (:require [books.db :as db]
            [books.handler :as handler]
            [cheshire.core :as json]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing use-fixtures]]
            [ring.mock.request :as mock]))

(def ^:dynamic *app* nil)
(def ^:dynamic *ds* nil)

(defn- tmp-db-file []
  (let [f (java.io.File/createTempFile "books-test-" ".db")]
    (.deleteOnExit f)
    (.getAbsolutePath f)))

(defn- with-fresh-db [f]
  (let [path (tmp-db-file)
        ds   (db/ds path)]
    (db/reset! ds)
    (binding [*ds*  ds
              *app* (handler/app-routes ds)]
      (try
        (f)
        (finally
          (io/delete-file (io/file path) true))))))

(use-fixtures :each with-fresh-db)

(defn- request [method uri & [body params]]
  (let [r (mock/request method uri)
        r (if params (mock/query-string r params) r)
        r (if body
            (-> r
                (mock/body (json/generate-string body))
                (mock/content-type "application/json"))
            r)]
    (*app* r)))

(defn- parse-body [response]
  (let [b (:body response)]
    (cond
      (nil? b)     nil
      (string? b)  (when (seq b) (json/parse-string b true))
      :else        (json/parse-string (slurp b) true))))

(deftest health-endpoint
  (testing "GET /health returns 200 with status ok"
    (let [resp (request :get "/health")]
      (is (= 200 (:status resp)))
      (is (= {:status "ok"} (parse-body resp))))))

(deftest create-book-success
  (testing "POST /books creates a book and returns 201"
    (let [resp (request :post "/books"
                        {:title "The Pragmatic Programmer"
                         :author "Andrew Hunt"
                         :year 1999
                         :isbn "978-0201616224"})
          body (parse-body resp)]
      (is (= 201 (:status resp)))
      (is (integer? (:id body)))
      (is (= "The Pragmatic Programmer" (:title body)))
      (is (= "Andrew Hunt" (:author body)))
      (is (= 1999 (:year body)))
      (is (= "978-0201616224" (:isbn body))))))

(deftest create-book-validation
  (testing "POST /books without title returns 400"
    (let [resp (request :post "/books" {:author "Someone"})]
      (is (= 400 (:status resp)))
      (is (some #(= "title is required" %) (:errors (parse-body resp))))))
  (testing "POST /books without author returns 400"
    (let [resp (request :post "/books" {:title "A Book"})]
      (is (= 400 (:status resp)))
      (is (some #(= "author is required" %) (:errors (parse-body resp))))))
  (testing "POST /books with blank title returns 400"
    (let [resp (request :post "/books" {:title "   " :author "X"})]
      (is (= 400 (:status resp))))))

(deftest list-books-and-filter
  (db/insert-book! *ds* {:title "Book A" :author "Alice" :year 2001 :isbn "A1"})
  (db/insert-book! *ds* {:title "Book B" :author "Bob"   :year 2002 :isbn "B1"})
  (db/insert-book! *ds* {:title "Book C" :author "Alice" :year 2003 :isbn "A2"})
  (testing "GET /books returns all books"
    (let [resp (request :get "/books")
          body (parse-body resp)]
      (is (= 200 (:status resp)))
      (is (= 3 (count body)))))
  (testing "GET /books?author=Alice filters by author"
    (let [resp (request :get "/books" nil {:author "Alice"})
          body (parse-body resp)]
      (is (= 200 (:status resp)))
      (is (= 2 (count body)))
      (is (every? #(= "Alice" (:author %)) body)))))

(deftest get-update-delete-book
  (let [created (parse-body (request :post "/books"
                                     {:title "Original Title"
                                      :author "Author One"
                                      :year 2020
                                      :isbn "111"}))
        id      (:id created)]
    (testing "GET /books/:id returns the book"
      (let [resp (request :get (str "/books/" id))]
        (is (= 200 (:status resp)))
        (is (= "Original Title" (:title (parse-body resp))))))
    (testing "GET /books/:id with unknown id returns 404"
      (is (= 404 (:status (request :get "/books/99999")))))
    (testing "PUT /books/:id updates the book"
      (let [resp (request :put (str "/books/" id)
                          {:title "New Title"
                           :author "Author One"
                           :year 2021
                           :isbn "111"})
            body (parse-body resp)]
        (is (= 200 (:status resp)))
        (is (= "New Title" (:title body)))
        (is (= 2021 (:year body)))))
    (testing "PUT /books/:id on missing id returns 404"
      (is (= 404 (:status (request :put "/books/99999"
                                   {:title "x" :author "y"})))))
    (testing "DELETE /books/:id removes the book"
      (let [resp (request :delete (str "/books/" id))]
        (is (= 204 (:status resp))))
      (is (= 404 (:status (request :get (str "/books/" id))))))
    (testing "DELETE /books/:id on missing id returns 404"
      (is (= 404 (:status (request :delete "/books/99999")))))))

(deftest invalid-id-returns-400
  (testing "non-numeric id returns 400"
    (is (= 400 (:status (request :get "/books/abc"))))
    (is (= 400 (:status (request :delete "/books/abc"))))))
