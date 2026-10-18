(ns books.api-test
  (:require [clojure.test :refer [deftest is testing use-fixtures]]
            [cheshire.core :as json]
            [ring.mock.request :as mock]
            [books.db :as db]
            [books.handler :as handler]))

(def ^:dynamic *app* nil)

(defn- with-temp-db [f]
  (let [file (java.io.File/createTempFile "books-test" ".db")]
    (try
      (binding [*app* (handler/app (db/datasource (.getAbsolutePath file)))]
        (f))
      (finally
        (.delete file)))))

(use-fixtures :each with-temp-db)

(defn- request
  "Sends a request through the app. Returns {:status :body} with body parsed from JSON when present."
  ([method uri] (request method uri nil))
  ([method uri body]
   (let [req (cond-> (mock/request method uri)
               body (-> (mock/content-type "application/json")
                        (mock/body (json/generate-string body))))
         resp (*app* req)]
     {:status (:status resp)
      :body (when-let [b (:body resp)]
              (json/parse-string b true))})))

(defn- create! [book]
  (:body (request :post "/books" book)))

(def dune {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441013593"})

(deftest health-check
  (let [{:keys [status body]} (request :get "/health")]
    (is (= 200 status))
    (is (= {:status "ok"} body))))

(deftest create-and-get-book
  (testing "POST returns 201 with the created book including an id"
    (let [{:keys [status body]} (request :post "/books" dune)]
      (is (= 201 status))
      (is (pos-int? (:id body)))
      (is (= "Dune" (:title body)))
      (is (= 1965 (:year body)))
      (testing "GET /books/{id} returns the same book"
        (let [got (request :get (str "/books/" (:id body)))]
          (is (= 200 (:status got)))
          (is (= body (:body got))))))))

(deftest create-validates-required-fields
  (testing "missing title and author are rejected with 422"
    (let [{:keys [status body]} (request :post "/books" {:year 2000})]
      (is (= 422 status))
      (is (= ["title is required" "author is required"] (:details body)))))
  (testing "blank title is rejected"
    (is (= 422 (:status (request :post "/books" {:title "  " :author "A"})))))
  (testing "non-integer year is rejected"
    (is (= 422 (:status (request :post "/books" {:title "T" :author "A" :year "1999"})))))
  (testing "non-object body is rejected with 400"
    (is (= 400 (:status (*app* (-> (mock/request :post "/books")
                                   (mock/content-type "application/json")
                                   (mock/body "[1,2]"))))))))

(deftest list-books-with-author-filter
  (create! dune)
  (create! {:title "Emma" :author "Jane Austen"})
  (create! {:title "Persuasion" :author "Jane Austen"})
  (testing "GET /books lists everything"
    (is (= 3 (count (:body (request :get "/books"))))))
  (testing "GET /books?author= filters by author"
    (let [books (:body (request :get "/books?author=Jane%20Austen"))]
      (is (= #{"Emma" "Persuasion"} (set (map :title books))))))
  (testing "author filter with no matches returns an empty list"
    (is (= [] (:body (request :get "/books?author=Nobody"))))))

(deftest update-book
  (let [id (:id (create! dune))
        updated {:title "Dune Messiah" :author "Frank Herbert" :year 1969}]
    (testing "PUT replaces the book and returns 200"
      (let [{:keys [status body]} (request :put (str "/books/" id) updated)]
        (is (= 200 status))
        (is (= id (:id body)))
        (is (= "Dune Messiah" (:title body)))
        (is (nil? (:isbn body)))))
    (testing "PUT on a missing id returns 404"
      (is (= 404 (:status (request :put "/books/99999" updated)))))
    (testing "PUT with invalid data returns 422 and leaves the book unchanged"
      (is (= 422 (:status (request :put (str "/books/" id) {:author "X"}))))
      (is (= "Dune Messiah" (:title (:body (request :get (str "/books/" id)))))))))

(deftest delete-book
  (let [id (:id (create! dune))]
    (testing "DELETE returns 204"
      (is (= 204 (:status (request :delete (str "/books/" id))))))
    (testing "the book is gone afterwards"
      (is (= 404 (:status (request :get (str "/books/" id))))))
    (testing "deleting again returns 404"
      (is (= 404 (:status (request :delete (str "/books/" id))))))))

(deftest unknown-routes-and-ids
  (is (= 404 (:status (request :get "/books/abc"))))
  (is (= 404 (:status (request :get "/nope"))))
  (is (= 405 (:status (request :patch "/books"))))
  (is (= 400 (:status (*app* (-> (mock/request :post "/books")
                                 (mock/content-type "application/json")
                                 (mock/body "{not json")))))))
