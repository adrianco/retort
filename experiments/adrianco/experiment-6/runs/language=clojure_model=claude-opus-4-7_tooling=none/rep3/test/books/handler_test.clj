(ns books.handler-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [cheshire.core :as json]
            [ring.mock.request :as mock]
            [books.db :as db]
            [books.handler :as handler]))

(def ^:dynamic *app* nil)

(defn- fresh-db-fixture [f]
  (let [tmp (java.io.File/createTempFile "books-test-" ".db")
        _   (.delete tmp)
        ds  (db/make-datasource {:dbtype "sqlite" :dbname (.getAbsolutePath tmp)})]
    (db/init-schema! ds)
    (try
      (binding [*app* (handler/make-app ds)]
        (f))
      (finally
        (.delete tmp)))))

(use-fixtures :each fresh-db-fixture)

(defn- json-body [body]
  (-> (mock/request :post "/")
      (mock/json-body body)
      :body))

(defn- post-book [m]
  (*app* (-> (mock/request :post "/books")
             (mock/json-body m))))

(defn- parse [resp]
  (when-let [b (:body resp)]
    (json/parse-string (if (string? b) b (slurp b)) true)))

(deftest health-endpoint
  (let [resp (*app* (mock/request :get "/health"))]
    (is (= 200 (:status resp)))
    (is (= {:status "ok"} (parse resp)))))

(deftest create-and-get-book
  (let [resp    (post-book {:title "Dune" :author "Herbert" :year 1965 :isbn "9780441172719"})
        created (parse resp)]
    (is (= 201 (:status resp)))
    (is (= "Dune" (:title created)))
    (is (= "Herbert" (:author created)))
    (is (= 1965 (:year created)))
    (is (some? (:id created)))
    (let [g (*app* (mock/request :get (str "/books/" (:id created))))]
      (is (= 200 (:status g)))
      (is (= "Dune" (:title (parse g)))))))

(deftest create-validation-errors
  (testing "missing title"
    (let [resp (post-book {:author "Someone"})]
      (is (= 400 (:status resp)))
      (is (re-find #"title" (:error (parse resp))))))
  (testing "missing author"
    (let [resp (post-book {:title "Stuff"})]
      (is (= 400 (:status resp)))
      (is (re-find #"author" (:error (parse resp))))))
  (testing "blank title"
    (let [resp (post-book {:title "   " :author "X"})]
      (is (= 400 (:status resp))))))

(deftest list-and-filter-by-author
  (post-book {:title "A" :author "Alice"})
  (post-book {:title "B" :author "Alice"})
  (post-book {:title "C" :author "Bob"})
  (let [all (parse (*app* (mock/request :get "/books")))]
    (is (= 3 (count all))))
  (let [alice (parse (*app* (mock/request :get "/books?author=Alice")))]
    (is (= 2 (count alice)))
    (is (every? #(= "Alice" (:author %)) alice))))

(deftest update-and-delete-book
  (let [created (parse (post-book {:title "Old" :author "Auth"}))
        id      (:id created)
        upd     (*app* (-> (mock/request :put (str "/books/" id))
                           (mock/json-body {:title "New" :author "Auth" :year 2020})))]
    (is (= 200 (:status upd)))
    (is (= "New" (:title (parse upd))))
    (let [del (*app* (mock/request :delete (str "/books/" id)))]
      (is (= 204 (:status del))))
    (let [g (*app* (mock/request :get (str "/books/" id)))]
      (is (= 404 (:status g))))))

(deftest get-missing-returns-404
  (let [resp (*app* (mock/request :get "/books/9999"))]
    (is (= 404 (:status resp)))))
