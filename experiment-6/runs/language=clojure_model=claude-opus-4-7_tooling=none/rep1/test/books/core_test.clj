(ns books.core-test
  (:require [clojure.test :refer [deftest is testing use-fixtures]]
            [clojure.java.io :as io]
            [books.db :as db]
            [books.routes :as routes]
            [cheshire.core :as json]
            [ring.mock.request :as mock]))

(def ^:dynamic *ds* nil)
(def ^:dynamic *tmpfile* nil)

(defn db-fixture [f]
  (let [tmp (java.io.File/createTempFile "books-test" ".db")]
    (.delete tmp)
    (try
      (let [ds (db/create-datasource {:dbtype "sqlite" :dbname (.getAbsolutePath tmp)})]
        (db/init-db! ds)
        (binding [*ds* ds
                  *tmpfile* tmp]
          (f)))
      (finally
        (.delete tmp)))))

(use-fixtures :each db-fixture)

(defn- parse-body [response]
  (let [body (:body response)]
    (cond
      (nil? body) nil
      (string? body) (when-not (empty? body) (json/parse-string body true))
      (instance? java.io.InputStream body)
      (let [s (slurp (io/reader body))]
        (when-not (empty? s) (json/parse-string s true)))
      :else body)))

(defn- json-request [method uri body]
  (-> (mock/request method uri)
      (mock/content-type "application/json")
      (mock/header "accept" "application/json")
      (mock/body (json/generate-string body))))

(defn- get-request [uri]
  (-> (mock/request :get uri)
      (mock/header "accept" "application/json")))

(deftest health-test
  (testing "health check returns ok"
    (let [app (routes/app *ds*)
          response (app (get-request "/health"))]
      (is (= 200 (:status response)))
      (is (= "ok" (:status (parse-body response)))))))

(deftest book-crud-test
  (testing "create -> get -> list -> update -> delete -> 404"
    (let [app (routes/app *ds*)
          create-resp (app (json-request :post "/books"
                             {:title "Clojure Programming"
                              :author "Chas Emerick"
                              :year 2012
                              :isbn "978-1449394707"}))]
      (is (= 201 (:status create-resp)))
      (let [created (parse-body create-resp)
            book-id (:id created)]
        (is (some? book-id))
        (is (= "Clojure Programming" (:title created)))

        (let [get-resp (app (get-request (str "/books/" book-id)))]
          (is (= 200 (:status get-resp)))
          (is (= "Clojure Programming" (:title (parse-body get-resp)))))

        (let [list-resp (app (get-request "/books"))]
          (is (= 200 (:status list-resp)))
          (is (= 1 (count (parse-body list-resp)))))

        (let [upd-resp (app (json-request :put (str "/books/" book-id)
                              {:title "Clojure Programming (2nd Ed)"
                               :author "Chas Emerick"
                               :year 2013
                               :isbn "978-1449394707"}))]
          (is (= 200 (:status upd-resp)))
          (is (= "Clojure Programming (2nd Ed)" (:title (parse-body upd-resp)))))

        (let [del-resp (app (mock/request :delete (str "/books/" book-id)))]
          (is (= 204 (:status del-resp))))

        (let [after-resp (app (get-request (str "/books/" book-id)))]
          (is (= 404 (:status after-resp))))))))

(deftest validation-test
  (testing "missing title returns 400"
    (let [app (routes/app *ds*)
          response (app (json-request :post "/books" {:author "Anon"}))]
      (is (= 400 (:status response)))
      (is (= "title and author are required"
             (:error (parse-body response))))))
  (testing "blank author returns 400"
    (let [app (routes/app *ds*)
          response (app (json-request :post "/books" {:title "X" :author "  "}))]
      (is (= 400 (:status response))))))

(deftest filter-by-author-test
  (testing "GET /books?author= filters by author"
    (let [app (routes/app *ds*)]
      (app (json-request :post "/books" {:title "A" :author "Alice"}))
      (app (json-request :post "/books" {:title "B" :author "Bob"}))
      (app (json-request :post "/books" {:title "C" :author "Alice"}))
      (let [response (app (get-request "/books?author=Alice"))
            books (parse-body response)]
        (is (= 200 (:status response)))
        (is (= 2 (count books)))
        (is (every? #(= "Alice" (:author %)) books))))))

(deftest not-found-test
  (testing "GET /books/999 returns 404"
    (let [app (routes/app *ds*)
          response (app (get-request "/books/999"))]
      (is (= 404 (:status response))))))
