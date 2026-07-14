(ns book-api.core-test
  (:require [clojure.test :refer :all]
            [book-api.db :as db]
            [book-api.routes :as routes]
            [ring.mock.request :as mock]
            [cheshire.core :as cheshire])
  (:import [java.io File]))

(defn parse-body [response]
  "Parse JSON body from response map."
  (cheshire/parse-string (:body response) true))

(defn send-request [request]
  "Send a ring request through the routes handler."
  (routes/routes request))

(defn json-request [method uri body-map]
  "Create a JSON request map with the given method, URI, and body."
  (-> (mock/request method uri)
      (assoc :content-type "application/json")
      (assoc :body (cheshire/generate-string body-map))))

(defn clean-db-path []
  "Remove the SQLite db file if it exists."
  (let [f (File. "books.db")]
    (when (.exists f)
      (.delete f))))

(defn init-test-db []
  "Initialize test database and remove stale file."
  (clean-db-path)
  (db/init-db!))

(use-fixtures :each
  (fn [f]
    (init-test-db)
    (f)))

;; ==================== HEALTH CHECK ====================

(deftest test-health-check
  (testing "GET /health returns 200 with ok status"
    (let [resp (send-request (mock/request :get "/health"))
          body (parse-body resp)]
      (is (= 200 (:status resp)))
      (is (= "ok" (:message body))))))

;; ==================== CREATE BOOK ====================

(deftest test-create-book-success
  (testing "POST /books creates a new book"
    (let [req (json-request :post "/books"
                {:title "The Hobbit"
                 :author "J.R.R. Tolkien"
                 :year 1937
                 :isbn "978-0547928227"})
          resp (send-request req)
          body (parse-body resp)]
      (is (= 201 (:status resp)))
      (is (= "The Hobbit" (:title body)))
      (is (= "J.R.R. Tolkien" (:author body)))
      (is (= 1937 (:year body)))
      (is (= "978-0547928227" (:isbn body)))
      (is (number? (:id body))))))

(deftest test-create-book-required-fields
  (testing "POST /books without title returns 400"
    (let [req (json-request :post "/books"
                {:author "Jane Austen"})
          resp (send-request req)
          body (parse-body resp)]
      (is (= 400 (:status resp)))
      (is (= "title is required" (:error body)))))
  (testing "POST /books without author returns 400"
    (let [req (json-request :post "/books"
                {:title "Some Book"})
          resp (send-request req)
          body (parse-body resp)]
      (is (= 400 (:status resp)))
      (is (= "author is required" (:error body))))))

;; ==================== LIST BOOKS ====================

(deftest test-list-books
  (testing "GET /books returns all books"
    (let [req1 (json-request :post "/books"
                   {:title "Book One"
                    :author "Author A"
                    :year 2020})
          resp1 (send-request req1)]
      (is (= 201 (:status resp1))))
    (let [req2 (json-request :post "/books"
                   {:title "Book Two"
                    :author "Author B"
                    :year 2021})
          resp2 (send-request req2)]
      (is (= 201 (:status resp2))))
    (let [resp (send-request (mock/request :get "/books"))
          body (parse-body resp)]
      (is (= 200 (:status resp)))
      (is (= 2 (count body))))))

(deftest test-list-books-filter-by-author
  (testing "GET /books with author filter returns only matching books"
    (let [req1 (json-request :post "/books"
                   {:title "Tolkien Book"
                    :author "J.R.R. Tolkien"
                    :year 1954})
          _ (send-request req1)]
      (is (= 201 (:status (send-request req1)))))
    (let [req2 (json-request :post "/books"
                   {:title "Love Story"
                    :author "Jane Austen"
                    :year 1813})
          _ (send-request req2)]
      (is (= 201 (:status (send-request req2)))))
    (let [resp (send-request
                (-> (mock/request :get "/books")
                    (assoc :query-params {"author" "J.R.R. Tolkien"})))
          body (parse-body resp)]
      (is (= 200 (:status resp)))
      (is (= 1 (count body)))
      (is (= "J.R.R. Tolkien" (get-in body [0 :author]))))))

;; ==================== GET BOOK BY ID ====================

(deftest test-get-book-by-id
  (testing "GET /books/:id returns the book"
    (let [req (json-request :post "/books"
                {:title "Dune"
                 :author "Frank Herbert"
                 :year 1965
                 :isbn "978-0441172719"})
          resp (send-request req)
          body (parse-body resp)
          book-id (:id body)]
      (is (= 201 (:status resp)))
      (let [resp2 (send-request (mock/request :get (str "/books/" book-id)))
            body2 (parse-body resp2)]
        (is (= 200 (:status resp2)))
        (is (= "Dune" (:title body2)))
        (is (= "Frank Herbert" (:author body2)))
        (is (= 1965 (:year body2)))))))

(deftest test-get-book-not-found
  (testing "GET /books/9999 returns 404"
    (let [resp (send-request (mock/request :get "/books/9999"))
          body (parse-body resp)]
      (is (= 404 (:status resp)))
      (is (= "Book not found" (:error body))))))

;; ==================== UPDATE BOOK ====================

(deftest test-update-book
  (testing "PUT /books/:id updates the book"
    (let [req (json-request :post "/books"
                {:title "Neuromancer"
                 :author "William Gibson"
                 :year 1984})
          resp (send-request req)
          body (parse-body resp)
          book-id (:id body)]
      (is (= 201 (:status resp)))
      (let [resp2 (send-request
                   (-> (mock/request :put (str "/books/" book-id))
                       (assoc :content-type "application/json")
                       (assoc :body (cheshire/generate-string
                                     {:title "Neuromancer"
                                      :author "William Gibson"
                                      :year 1984
                                      :isbn "978-0441569595"}))))
            body2 (parse-body resp2)]
        (is (= 200 (:status resp2)))
        (is (= "978-0441569595" (:isbn body2)))))))

;; ==================== DELETE BOOK ====================

(deftest test-delete-book
  (testing "DELETE /books/:id removes the book"
    (let [req (json-request :post "/books"
                {:title "1984"
                 :author "George Orwell"
                 :year 1949})
          resp (send-request req)
          body (parse-body resp)
          book-id (:id body)]
      (is (= 201 (:status resp)))
      (let [resp2 (send-request (mock/request :delete (str "/books/" book-id)))
            body2 (parse-body resp2)]
        (is (= 200 (:status resp2)))
        (is (= "Book deleted successfully" (:message body2))))
      (let [resp3 (send-request (mock/request :get (str "/books/" book-id)))
            body3 (parse-body resp3)]
        (is (= 404 (:status resp3)))))))

(deftest test-delete-book-not-found
  (testing "DELETE /books/9999 returns 404"
    (let [resp (send-request (mock/request :delete "/books/9999"))
          body (parse-body resp)]
      (is (= 404 (:status resp)))
      (is (= "Book not found" (:error body))))))
