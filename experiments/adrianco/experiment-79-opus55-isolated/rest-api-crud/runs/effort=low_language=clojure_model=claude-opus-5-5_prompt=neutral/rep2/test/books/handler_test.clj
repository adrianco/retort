(ns books.handler-test
  (:require [books.db :as db]
            [books.handler :as handler]
            [cheshire.core :as json]
            [clojure.test :refer [deftest is testing use-fixtures]]
            [ring.mock.request :as mock])
  (:import (java.io File)))

(def ^:dynamic *app* nil)

(defn- with-fresh-db [f]
  (let [file (File/createTempFile "books-test" ".db")]
    (try
      (binding [*app* (handler/app (db/init! (db/datasource (.getPath file))))]
        (f))
      (finally (.delete file)))))

(use-fixtures :each with-fresh-db)

(defn- call
  ([method uri] (call method uri nil))
  ([method uri body]
   (let [resp (*app* (cond-> (mock/request method uri)
                       body (-> (mock/body (if (string? body) body (json/generate-string body)))
                                (mock/content-type "application/json"))))]
     (update resp :body #(some-> % (json/parse-string true))))))

(def dune {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441013593"})

(deftest health-check
  (let [resp (call :get "/health")]
    (is (= 200 (:status resp)))
    (is (= {:status "ok"} (:body resp)))
    (is (re-find #"application/json" (get-in resp [:headers "Content-Type"])))))

(deftest create-and-get
  (let [created (call :post "/books" dune)
        id (get-in created [:body :id])]
    (is (= 201 (:status created)))
    (is (integer? id))
    (is (= dune (dissoc (:body created) :id)))
    (let [fetched (call :get (str "/books/" id))]
      (is (= 200 (:status fetched)))
      (is (= (assoc dune :id id) (:body fetched))))))

(deftest create-with-only-required-fields
  (let [resp (call :post "/books" {:title "T" :author "A"})]
    (is (= 201 (:status resp)))
    (is (= {:title "T" :author "A" :year nil :isbn nil} (dissoc (:body resp) :id)))))

(deftest validation
  (testing "missing title and author"
    (let [resp (call :post "/books" {:year 1965})]
      (is (= 400 (:status resp)))
      (is (contains? (get-in resp [:body :details]) :title))
      (is (contains? (get-in resp [:body :details]) :author))))
  (testing "blank title"
    (is (= 400 (:status (call :post "/books" (assoc dune :title "   "))))))
  (testing "non-integer year"
    (let [resp (call :post "/books" (assoc dune :year "soon"))]
      (is (= 400 (:status resp)))
      (is (contains? (get-in resp [:body :details]) :year))))
  (testing "malformed or non-object JSON"
    (is (= 400 (:status (call :post "/books" "{not json"))))
    (is (= 400 (:status (call :post "/books" "[1,2]"))))
    (is (= 400 (:status (*app* (mock/request :post "/books"))))))
  (testing "JSON body sent without a JSON content type is still validated"
    (let [resp (*app* (-> (mock/request :post "/books")
                          (mock/body "{\"title\":\"\"}")
                          (mock/content-type "application/x-www-form-urlencoded")))]
      (is (= 400 (:status resp)))
      (is (re-find #"Validation failed" (:body resp)))))
  (testing "nothing was stored"
    (is (= [] (:body (call :get "/books"))))))

(deftest list-and-filter-by-author
  (call :post "/books" dune)
  (call :post "/books" {:title "Children of Dune" :author "Frank Herbert"})
  (call :post "/books" {:title "Emma" :author "Jane Austen" :year 1815})
  (let [all (call :get "/books")]
    (is (= 200 (:status all)))
    (is (= 3 (count (:body all)))))
  (is (= ["Dune" "Children of Dune"]
         (map :title (:body (call :get "/books?author=Frank%20Herbert")))))
  (is (= ["Emma"] (map :title (:body (call :get "/books?author=jane+austen")))))
  (is (= [] (:body (call :get "/books?author=Nobody")))))

(deftest update-book
  (let [id (get-in (call :post "/books" dune) [:body :id])
        resp (call :put (str "/books/" id) {:title "Dune Messiah" :author "Frank Herbert" :year 1969})]
    (is (= 200 (:status resp)))
    (is (= {:id id :title "Dune Messiah" :author "Frank Herbert" :year 1969 :isbn nil}
           (:body resp)))
    (is (= (:body resp) (:body (call :get (str "/books/" id)))))
    (testing "invalid update is rejected and leaves the book unchanged"
      (is (= 400 (:status (call :put (str "/books/" id) {:title "No author"}))))
      (is (= "Dune Messiah" (get-in (call :get (str "/books/" id)) [:body :title]))))))

(deftest delete-book
  (let [id (get-in (call :post "/books" dune) [:body :id])]
    (is (= 204 (:status (call :delete (str "/books/" id)))))
    (is (= 404 (:status (call :get (str "/books/" id)))))
    (is (= 404 (:status (call :delete (str "/books/" id)))))))

(deftest missing-resources
  (is (= 404 (:status (call :get "/books/999"))))
  (is (= 404 (:status (call :get "/books/abc"))))
  (is (= 404 (:status (call :put "/books/999" dune))))
  (is (= 404 (:status (call :delete "/books/999"))))
  (is (= 404 (:status (call :get "/nope")))))
