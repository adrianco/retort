(ns books.handler-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [cheshire.core :as json]
            [ring.mock.request :as mock]
            [books.db :as db]
            [books.handler :as handler]))

(def ^:dynamic *app* nil)
(def ^:dynamic *ds* nil)

(defn- tmp-db-path []
  (let [f (java.io.File/createTempFile "books-test-" ".db")]
    (.deleteOnExit f)
    (.delete f)
    (.getAbsolutePath f)))

(defn test-fixture [f]
  (let [path (tmp-db-path)
        ds (db/init! {:dbtype "sqlite" :dbname path})
        app (handler/make-app ds)]
    (try
      (binding [*app* app *ds* ds]
        (f))
      (finally
        (.delete (java.io.File. path))))))

(use-fixtures :each test-fixture)

(defn- json-body [m]
  (json/generate-string m))

(defn- parse [resp]
  (when-let [body (:body resp)]
    (let [s (if (string? body) body (slurp body))]
      (when-not (clojure.string/blank? s)
        (json/parse-string s true)))))

(defn- post-book [m]
  (*app* (-> (mock/request :post "/books")
             (mock/content-type "application/json")
             (mock/body (json-body m)))))

(deftest health-endpoint
  (testing "GET /health returns ok"
    (let [resp (*app* (mock/request :get "/health"))]
      (is (= 200 (:status resp)))
      (is (= "ok" (:status (parse resp)))))))

(deftest create-and-fetch-book
  (testing "POST /books creates a book and GET /books/{id} returns it"
    (let [resp (post-book {:title "Dune" :author "Frank Herbert"
                           :year 1965 :isbn "9780441172719"})]
      (is (= 201 (:status resp)))
      (let [created (parse resp)]
        (is (some? (:id created)))
        (is (= "Dune" (:title created)))
        (is (= "Frank Herbert" (:author created)))
        (let [get-resp (*app* (mock/request :get (str "/books/" (:id created))))]
          (is (= 200 (:status get-resp)))
          (is (= "Dune" (:title (parse get-resp)))))))))

(deftest list-and-filter-books
  (testing "GET /books lists all and filters by author"
    (post-book {:title "Dune" :author "Frank Herbert" :year 1965})
    (post-book {:title "Foundation" :author "Isaac Asimov" :year 1951})
    (post-book {:title "I, Robot" :author "Isaac Asimov" :year 1950})
    (let [all (parse (*app* (mock/request :get "/books")))
          asimov (parse (*app* (mock/request :get "/books?author=Isaac+Asimov")))]
      (is (= 3 (count all)))
      (is (= 2 (count asimov)))
      (is (every? #(= "Isaac Asimov" (:author %)) asimov)))))

(deftest update-and-delete-book
  (testing "PUT /books/{id} updates and DELETE /books/{id} removes a book"
    (let [created (parse (post-book {:title "Old Title" :author "Anon" :year 2000}))
          id (:id created)
          put-resp (*app* (-> (mock/request :put (str "/books/" id))
                              (mock/content-type "application/json")
                              (mock/body (json-body {:title "New Title"
                                                     :author "Author 2"
                                                     :year 2024
                                                     :isbn "111"}))))
          updated (parse put-resp)]
      (is (= 200 (:status put-resp)))
      (is (= "New Title" (:title updated)))
      (is (= "Author 2" (:author updated)))
      (let [del-resp (*app* (mock/request :delete (str "/books/" id)))]
        (is (= 204 (:status del-resp))))
      (let [get-resp (*app* (mock/request :get (str "/books/" id)))]
        (is (= 404 (:status get-resp)))))))

(deftest validation-errors
  (testing "POST /books without title returns 400"
    (let [resp (post-book {:author "Someone"})]
      (is (= 400 (:status resp)))
      (is (= "title is required" (:error (parse resp))))))
  (testing "POST /books without author returns 400"
    (let [resp (post-book {:title "Untitled"})]
      (is (= 400 (:status resp)))
      (is (= "author is required" (:error (parse resp))))))
  (testing "GET /books/{id} for missing book returns 404"
    (let [resp (*app* (mock/request :get "/books/9999"))]
      (is (= 404 (:status resp))))))
