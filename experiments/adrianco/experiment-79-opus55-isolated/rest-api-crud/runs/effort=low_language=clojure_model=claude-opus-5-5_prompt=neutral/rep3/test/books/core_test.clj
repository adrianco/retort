(ns books.core-test
  (:require [books.core :as core]
            [books.db :as db]
            [cheshire.core :as json]
            [clojure.test :refer [deftest is testing use-fixtures]]
            [ring.mock.request :as mock])
  (:import (java.io File)))

(def ^:dynamic *app* nil)

(use-fixtures :each
  (fn [f]
    (let [file (File/createTempFile "books-test" ".db")]
      (try
        (binding [*app* (core/make-app (db/init! (db/datasource (.getPath file))))]
          (f))
        (finally (.delete file))))))

(defn- call
  ([method uri] (call method uri nil))
  ([method uri body]
   (let [resp (*app* (cond-> (mock/request method uri)
                       body (-> (mock/content-type "application/json")
                                (mock/body (if (string? body) body (json/generate-string body))))))]
     (update resp :body #(some-> % (json/parse-string true))))))

(def dune {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441013593"})

(deftest health-test
  (let [resp (call :get "/health")]
    (is (= 200 (:status resp)))
    (is (= {:status "ok"} (:body resp)))
    (is (re-find #"application/json" (get-in resp [:headers "Content-Type"])))))

(deftest create-and-get-test
  (let [created (call :post "/books" dune)
        id (get-in created [:body :id])]
    (is (= 201 (:status created)))
    (is (integer? id))
    (is (= dune (dissoc (:body created) :id)))
    (let [fetched (call :get (str "/books/" id))]
      (is (= 200 (:status fetched)))
      (is (= (assoc dune :id id) (:body fetched))))))

(deftest optional-fields-test
  (let [resp (call :post "/books" {:title "T" :author "A"})]
    (is (= 201 (:status resp)))
    (is (nil? (get-in resp [:body :year])))
    (is (nil? (get-in resp [:body :isbn])))))

(deftest validation-test
  (testing "missing title"
    (let [resp (call :post "/books" {:author "A"})]
      (is (= 400 (:status resp)))
      (is (= 1 (count (get-in resp [:body :details]))))))
  (testing "missing author"
    (is (= 400 (:status (call :post "/books" {:title "T"})))))
  (testing "blank title"
    (is (= 400 (:status (call :post "/books" {:title "  " :author "A"})))))
  (testing "non-integer year"
    (is (= 400 (:status (call :post "/books" {:title "T" :author "A" :year "x"})))))
  (testing "malformed JSON"
    (is (= 400 (:status (call :post "/books" "{not json")))))
  (testing "non-object JSON"
    (is (= 400 (:status (call :post "/books" "[1,2]")))))
  (testing "JSON sent without a JSON content type is still validated"
    (let [resp (*app* (-> (mock/request :post "/books")
                          (mock/content-type "application/x-www-form-urlencoded")
                          (mock/body "{}")))]
      (is (= 400 (:status resp)))
      (is (re-find #"Validation failed" (:body resp)))))
  (testing "nothing was stored"
    (is (= [] (:body (call :get "/books"))))))

(deftest list-and-filter-test
  (call :post "/books" dune)
  (call :post "/books" {:title "Emma" :author "Jane Austen" :year 1815})
  (call :post "/books" {:title "Persuasion" :author "Jane Austen" :year 1817})
  (is (= 3 (count (:body (call :get "/books")))))
  (let [resp (call :get "/books?author=Jane%20Austen")]
    (is (= 200 (:status resp)))
    (is (= ["Emma" "Persuasion"] (map :title (:body resp)))))
  (is (= [] (:body (call :get "/books?author=Nobody")))))

(deftest update-test
  (let [id (get-in (call :post "/books" dune) [:body :id])
        resp (call :put (str "/books/" id) (assoc dune :title "Dune Messiah" :year 1969))]
    (is (= 200 (:status resp)))
    (is (= "Dune Messiah" (get-in resp [:body :title])))
    (is (= 1969 (get-in (call :get (str "/books/" id)) [:body :year])))
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
