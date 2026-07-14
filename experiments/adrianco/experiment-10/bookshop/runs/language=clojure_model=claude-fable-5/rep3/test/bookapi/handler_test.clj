(ns bookapi.handler-test
  (:require [clojure.test :refer [deftest is testing use-fixtures]]
            [cheshire.core :as json]
            [ring.mock.request :as mock]
            [bookapi.db :as db]
            [bookapi.handler :refer [make-app]])
  (:import [java.io File]))

(def ^:dynamic *app* nil)

(defn with-test-app [f]
  (let [tmp (File/createTempFile "books-test" ".db")
        ds  (db/make-datasource (.getAbsolutePath tmp))]
    (db/init! ds)
    (binding [*app* (make-app ds)]
      (try (f)
           (finally (.delete tmp))))))

(use-fixtures :each with-test-app)

(defn- parse-body [response]
  (some-> (:body response) (json/parse-string true)))

(defn- json-request [method uri body]
  (-> (mock/request method uri)
      (mock/content-type "application/json")
      (mock/body (json/generate-string body))))

(defn- create-book! [book]
  (*app* (json-request :post "/books" book)))

(deftest health-check
  (let [response (*app* (mock/request :get "/health"))]
    (is (= 200 (:status response)))
    (is (= {:status "ok"} (parse-body response)))))

(deftest create-book
  (testing "valid book is created with 201"
    (let [response (create-book! {:title "SICP" :author "Abelson" :year 1985 :isbn "0-262-01077-1"})
          body     (parse-body response)]
      (is (= 201 (:status response)))
      (is (pos-int? (:id body)))
      (is (= "SICP" (:title body)))
      (is (= "Abelson" (:author body)))
      (is (= 1985 (:year body)))
      (is (= "0-262-01077-1" (:isbn body)))))

  (testing "missing title and author returns 400 with errors"
    (let [response (create-book! {:year 2020})
          body     (parse-body response)]
      (is (= 400 (:status response)))
      (is (= #{"title is required" "author is required"} (set (:errors body))))))

  (testing "non-integer year returns 400"
    (let [response (create-book! {:title "X" :author "Y" :year "not-a-year"})]
      (is (= 400 (:status response))))))

(deftest list-books
  (create-book! {:title "Book A" :author "Alice"})
  (create-book! {:title "Book B" :author "Bob"})
  (create-book! {:title "Book C" :author "Alice"})

  (testing "lists all books"
    (let [response (*app* (mock/request :get "/books"))
          body     (parse-body response)]
      (is (= 200 (:status response)))
      (is (= 3 (count body)))))

  (testing "filters by author"
    (let [response (*app* (mock/request :get "/books" {:author "Alice"}))
          body     (parse-body response)]
      (is (= 200 (:status response)))
      (is (= 2 (count body)))
      (is (every? #(= "Alice" (:author %)) body)))))

(deftest get-book-by-id
  (let [created (parse-body (create-book! {:title "Clojure" :author "Halloway"}))
        id      (:id created)]
    (testing "returns existing book"
      (let [response (*app* (mock/request :get (str "/books/" id)))]
        (is (= 200 (:status response)))
        (is (= created (parse-body response)))))

    (testing "404 for unknown id"
      (is (= 404 (:status (*app* (mock/request :get "/books/99999"))))))

    (testing "404 for non-numeric id"
      (is (= 404 (:status (*app* (mock/request :get "/books/abc"))))))))

(deftest update-book
  (let [id (:id (parse-body (create-book! {:title "Old" :author "Author"})))]
    (testing "updates an existing book"
      (let [response (*app* (json-request :put (str "/books/" id)
                                          {:title "New" :author "Author" :year 2024 :isbn "123"}))
            body     (parse-body response)]
        (is (= 200 (:status response)))
        (is (= "New" (:title body)))
        (is (= 2024 (:year body)))))

    (testing "validation applies on update"
      (is (= 400 (:status (*app* (json-request :put (str "/books/" id) {:title "Only title"}))))))

    (testing "404 for unknown id"
      (is (= 404 (:status (*app* (json-request :put "/books/99999"
                                               {:title "T" :author "A"}))))))))

(deftest delete-book
  (let [id (:id (parse-body (create-book! {:title "Doomed" :author "Nobody"})))]
    (testing "deletes an existing book"
      (is (= 204 (:status (*app* (mock/request :delete (str "/books/" id))))))
      (is (= 404 (:status (*app* (mock/request :get (str "/books/" id)))))))

    (testing "404 for unknown id"
      (is (= 404 (:status (*app* (mock/request :delete "/books/99999"))))))))
