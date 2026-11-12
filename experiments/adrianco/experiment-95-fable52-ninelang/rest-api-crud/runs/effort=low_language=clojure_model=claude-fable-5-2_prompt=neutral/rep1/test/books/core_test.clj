(ns books.core-test
  (:require [books.core :as core]
            [books.db :as db]
            [cheshire.core :as json]
            [clojure.test :refer [deftest is testing use-fixtures]]
            [ring.mock.request :as mock])
  (:import (java.io File)))

(def ^:dynamic *app* nil)

(use-fixtures :each
  (fn [t]
    (let [f (File/createTempFile "books-test" ".db")]
      (try
        (binding [*app* (core/app (db/init! (db/datasource (.getPath f))))]
          (t))
        (finally (.delete f))))))

(defn- call
  ([method uri] (call method uri nil))
  ([method uri body]
   (let [resp (*app* (cond-> (mock/request method uri)
                       body (mock/body (if (string? body) body (json/generate-string body)))))]
     (update resp :body #(when (seq %) (json/parse-string % true))))))

(def dune {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441172719"})

(deftest health-test
  (let [r (call :get "/health")]
    (is (= 200 (:status r)))
    (is (= {:status "ok"} (:body r)))))

(deftest create-and-get-test
  (let [r (call :post "/books" dune)
        id (get-in r [:body :id])]
    (is (= 201 (:status r)))
    (is (= dune (dissoc (:body r) :id)))
    (is (= "application/json; charset=utf-8" (get-in r [:headers "Content-Type"])))
    (let [g (call :get (str "/books/" id))]
      (is (= 200 (:status g)))
      (is (= (assoc dune :id id) (:body g))))))

(deftest optional-fields-test
  (let [r (call :post "/books" {:title "T" :author "A"})]
    (is (= 201 (:status r)))
    (is (nil? (get-in r [:body :year])))
    (is (nil? (get-in r [:body :isbn])))))

(deftest validation-test
  (testing "missing title and author"
    (let [r (call :post "/books" {:year 2000})]
      (is (= 400 (:status r)))
      (is (= 2 (count (get-in r [:body :details]))))))
  (testing "blank title"
    (is (= 400 (:status (call :post "/books" {:title "  " :author "A"})))))
  (testing "missing author"
    (is (= 400 (:status (call :post "/books" {:title "T"})))))
  (testing "bad year type"
    (is (= 400 (:status (call :post "/books" {:title "T" :author "A" :year "x"})))))
  (testing "malformed / non-object / empty JSON"
    (is (= 400 (:status (call :post "/books" "{not json"))))
    (is (= 400 (:status (call :post "/books" "[1,2]"))))
    (is (= 400 (:status (call :post "/books")))))
  (testing "nothing was stored"
    (is (= [] (:body (call :get "/books"))))))

(deftest form-content-type-body-test
  (testing "JSON body is accepted even with curl's default content type"
    (let [r (*app* (-> (mock/request :post "/books")
                       (mock/body (json/generate-string dune))
                       (mock/content-type "application/x-www-form-urlencoded")))]
      (is (= 201 (:status r))))))

(deftest list-and-filter-test
  (call :post "/books" dune)
  (call :post "/books" {:title "Emma" :author "Jane Austen" :year 1815})
  (call :post "/books" {:title "Children of Dune" :author "Frank Herbert"})
  (is (= 3 (count (:body (call :get "/books")))))
  (let [r (call :get "/books?author=Frank%20Herbert")]
    (is (= 200 (:status r)))
    (is (= ["Dune" "Children of Dune"] (map :title (:body r)))))
  (is (= [] (:body (call :get "/books?author=Nobody")))))

(deftest update-test
  (let [id (get-in (call :post "/books" dune) [:body :id])
        r (call :put (str "/books/" id) {:title "Dune Messiah" :author "Frank Herbert" :year 1969})]
    (is (= 200 (:status r)))
    (is (= {:id id :title "Dune Messiah" :author "Frank Herbert" :year 1969 :isbn nil} (:body r)))
    (is (= "Dune Messiah" (get-in (call :get (str "/books/" id)) [:body :title])))
    (is (= 400 (:status (call :put (str "/books/" id) {:title "No author"}))))
    (is (= 404 (:status (call :put "/books/9999" dune))))))

(deftest delete-test
  (let [id (get-in (call :post "/books" dune) [:body :id])]
    (is (= 204 (:status (call :delete (str "/books/" id)))))
    (is (= 404 (:status (call :get (str "/books/" id)))))
    (is (= 404 (:status (call :delete (str "/books/" id)))))))

(deftest not-found-test
  (is (= 404 (:status (call :get "/books/9999"))))
  (is (= 404 (:status (call :get "/books/abc"))))
  (is (= 404 (:status (call :get "/nope")))))
