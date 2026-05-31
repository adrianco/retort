(ns books.core-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [books.core :as core]
            [books.db :as db]
            [cheshire.core :as json]
            [ring.mock.request :as mock]))

(def ^:dynamic *app* nil)

(defn- temp-db-path []
  (let [f (java.io.File/createTempFile "books-test-" ".db")]
    (.deleteOnExit f)
    (.delete f)
    (.getAbsolutePath f)))

(defn fresh-app-fixture [f]
  (let [path (temp-db-path)
        ds (db/make-datasource path)]
    (db/init-schema! ds)
    (try
      (binding [*app* (core/app ds)]
        (f))
      (finally
        (.delete (java.io.File. path))))))

(use-fixtures :each fresh-app-fixture)

(defn- json-body [m]
  (json/generate-string m))

(defn- parse [resp]
  (some-> resp :body (json/parse-string true)))

(defn- post-book [body]
  (*app* (-> (mock/request :post "/books")
             (mock/content-type "application/json")
             (mock/body (json-body body)))))

(deftest health-endpoint
  (testing "GET /health returns 200 ok"
    (let [resp (*app* (mock/request :get "/health"))]
      (is (= 200 (:status resp)))
      (is (= {:status "ok"} (parse resp))))))

(deftest create-and-get-book
  (testing "POST /books creates a book and GET /books/:id returns it"
    (let [create-resp (post-book {:title "Dune" :author "Herbert" :year 1965 :isbn "111"})
          created (parse create-resp)]
      (is (= 201 (:status create-resp)))
      (is (some? (:id created)))
      (is (= "Dune" (:title created)))
      (let [get-resp (*app* (mock/request :get (str "/books/" (:id created))))
            fetched (parse get-resp)]
        (is (= 200 (:status get-resp)))
        (is (= "Dune" (:title fetched)))
        (is (= "Herbert" (:author fetched)))
        (is (= 1965 (:year fetched)))))))

(deftest validation-rejects-missing-fields
  (testing "POST /books without title returns 400"
    (let [resp (post-book {:author "Someone"})]
      (is (= 400 (:status resp)))
      (is (re-find #"title" (:error (parse resp))))))
  (testing "POST /books without author returns 400"
    (let [resp (post-book {:title "Untitled"})]
      (is (= 400 (:status resp)))
      (is (re-find #"author" (:error (parse resp)))))))

(deftest list-with-author-filter
  (testing "GET /books?author=X filters results"
    (post-book {:title "A" :author "Alice"})
    (post-book {:title "B" :author "Bob"})
    (post-book {:title "C" :author "Alice"})
    (let [all (parse (*app* (mock/request :get "/books")))
          alice (parse (*app* (mock/request :get "/books?author=Alice")))]
      (is (= 3 (count all)))
      (is (= 2 (count alice)))
      (is (every? #(= "Alice" (:author %)) alice)))))

(deftest update-and-delete-book
  (testing "PUT updates a book; DELETE removes it"
    (let [created (parse (post-book {:title "Old" :author "X"}))
          id (:id created)
          upd-resp (*app* (-> (mock/request :put (str "/books/" id))
                              (mock/content-type "application/json")
                              (mock/body (json-body {:title "New" :author "X" :year 2020}))))
          updated (parse upd-resp)]
      (is (= 200 (:status upd-resp)))
      (is (= "New" (:title updated)))
      (is (= 2020 (:year updated)))
      (let [del-resp (*app* (mock/request :delete (str "/books/" id)))]
        (is (= 204 (:status del-resp))))
      (let [missing (*app* (mock/request :get (str "/books/" id)))]
        (is (= 404 (:status missing)))))))

(deftest get-missing-book-returns-404
  (testing "GET /books/999 on empty db returns 404"
    (let [resp (*app* (mock/request :get "/books/999"))]
      (is (= 404 (:status resp))))))
