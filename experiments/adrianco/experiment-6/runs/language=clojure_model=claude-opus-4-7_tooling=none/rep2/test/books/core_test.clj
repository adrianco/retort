(ns books.core-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [cheshire.core :as json]
            [ring.mock.request :as mock]
            [books.core :as core]
            [books.db :as db]))

(defn- with-fresh-db [f]
  (let [tmp (doto (java.io.File/createTempFile "books-test-" ".db")
              (.deleteOnExit))
        ds (db/make-datasource (.getAbsolutePath tmp))]
    (try
      (db/init-schema! ds)
      (core/set-datasource! ds)
      (f)
      (finally
        (.delete tmp)))))

(use-fixtures :each with-fresh-db)

(defn- json-request [method uri body]
  (-> (mock/request method uri)
      (mock/content-type "application/json")
      (mock/body (json/generate-string body))))

(defn- parse-body [response]
  (let [b (:body response)]
    (cond
      (nil? b) nil
      (string? b) (json/parse-string b true)
      :else (json/parse-string (slurp b) true))))

(deftest health-endpoint
  (testing "GET /health returns 200"
    (let [resp (core/app (mock/request :get "/health"))]
      (is (= 200 (:status resp)))
      (is (= {:status "ok"} (parse-body resp))))))

(deftest create-book-success
  (testing "POST /books creates a book and returns 201"
    (let [resp (core/app (json-request :post "/books"
                                       {:title "Dune"
                                        :author "Frank Herbert"
                                        :year 1965
                                        :isbn "9780441172719"}))
          body (parse-body resp)]
      (is (= 201 (:status resp)))
      (is (integer? (:id body)))
      (is (= "Dune" (:title body)))
      (is (= "Frank Herbert" (:author body)))
      (is (= 1965 (:year body)))
      (is (= "9780441172719" (:isbn body))))))

(deftest create-book-validation
  (testing "POST /books returns 400 when title is missing"
    (let [resp (core/app (json-request :post "/books" {:author "X"}))]
      (is (= 400 (:status resp)))
      (is (= "title is required" (:error (parse-body resp))))))
  (testing "POST /books returns 400 when author is missing"
    (let [resp (core/app (json-request :post "/books" {:title "X"}))]
      (is (= 400 (:status resp)))
      (is (= "author is required" (:error (parse-body resp))))))
  (testing "POST /books returns 400 when title is blank"
    (let [resp (core/app (json-request :post "/books" {:title "  " :author "A"}))]
      (is (= 400 (:status resp))))))

(deftest list-and-filter
  (testing "GET /books lists all and filters by author"
    (core/app (json-request :post "/books" {:title "A" :author "Alice"}))
    (core/app (json-request :post "/books" {:title "B" :author "Bob"}))
    (core/app (json-request :post "/books" {:title "C" :author "Alice"}))
    (let [all (parse-body (core/app (mock/request :get "/books")))]
      (is (= 3 (count all))))
    (let [alice (parse-body (core/app (mock/request :get "/books?author=Alice")))]
      (is (= 2 (count alice)))
      (is (every? #(= "Alice" (:author %)) alice)))))

(deftest get-update-delete
  (testing "single-book lifecycle"
    (let [created (parse-body
                   (core/app (json-request :post "/books"
                                           {:title "Old Title"
                                            :author "Auth"
                                            :year 2000})))
          id (:id created)]
      (testing "GET /books/:id returns the book"
        (let [resp (core/app (mock/request :get (str "/books/" id)))]
          (is (= 200 (:status resp)))
          (is (= "Old Title" (:title (parse-body resp))))))
      (testing "PUT /books/:id updates the book"
        (let [resp (core/app (json-request :put (str "/books/" id)
                                           {:title "New Title" :year 2024}))
              body (parse-body resp)]
          (is (= 200 (:status resp)))
          (is (= "New Title" (:title body)))
          (is (= "Auth" (:author body)))
          (is (= 2024 (:year body)))))
      (testing "DELETE /books/:id deletes the book"
        (let [resp (core/app (mock/request :delete (str "/books/" id)))]
          (is (= 204 (:status resp))))
        (let [resp (core/app (mock/request :get (str "/books/" id)))]
          (is (= 404 (:status resp))))))))

(deftest missing-book
  (testing "GET /books/:id returns 404 when not found"
    (let [resp (core/app (mock/request :get "/books/999"))]
      (is (= 404 (:status resp)))))
  (testing "DELETE /books/:id returns 404 when not found"
    (let [resp (core/app (mock/request :delete "/books/999"))]
      (is (= 404 (:status resp)))))
  (testing "PUT /books/:id returns 404 when not found"
    (let [resp (core/app (json-request :put "/books/999" {:title "X"}))]
      (is (= 404 (:status resp))))))
