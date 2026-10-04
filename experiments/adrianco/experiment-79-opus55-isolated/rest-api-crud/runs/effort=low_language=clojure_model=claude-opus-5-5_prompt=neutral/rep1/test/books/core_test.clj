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
        (binding [*app* (core/app (db/init! (db/datasource (.getPath file))))]
          (f))
        (finally (.delete file))))))

(defn- call
  ([method uri] (call method uri nil))
  ([method uri body]
   (let [resp (*app* (cond-> (mock/request method uri)
                       body (-> (mock/body (if (string? body) body (json/generate-string body)))
                                (mock/content-type "application/json"))))]
     (assoc resp :json (when (seq (:body resp)) (json/parse-string (:body resp) true))))))

(def dune {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441013593"})

(deftest health-test
  (let [resp (call :get "/health")]
    (is (= 200 (:status resp)))
    (is (= {:status "ok"} (:json resp)))
    (is (re-find #"application/json" (get-in resp [:headers "Content-Type"])))))

(deftest create-and-get-test
  (let [created (call :post "/books" dune)
        id      (get-in created [:json :id])]
    (is (= 201 (:status created)))
    (is (integer? id))
    (is (= dune (dissoc (:json created) :id)))
    (let [fetched (call :get (str "/books/" id))]
      (is (= 200 (:status fetched)))
      (is (= (assoc dune :id id) (:json fetched))))))

(deftest optional-fields-test
  (let [resp (call :post "/books" {:title "T" :author "A"})]
    (is (= 201 (:status resp)))
    (is (nil? (get-in resp [:json :year])))
    (is (nil? (get-in resp [:json :isbn])))))

(deftest validation-test
  (testing "missing title"
    (let [resp (call :post "/books" {:author "A"})]
      (is (= 400 (:status resp)))
      (is (contains? (get-in resp [:json :details]) :title))))
  (testing "missing author"
    (let [resp (call :post "/books" {:title "T"})]
      (is (= 400 (:status resp)))
      (is (contains? (get-in resp [:json :details]) :author))))
  (testing "blank title and wrong types"
    (let [resp (call :post "/books" {:title "  " :author "A" :year "abc" :isbn 5})]
      (is (= 400 (:status resp)))
      (is (= #{:title :year :isbn} (set (keys (get-in resp [:json :details])))))))
  (testing "malformed or non-object JSON"
    (is (= 400 (:status (call :post "/books" "{not json"))))
    (is (= 400 (:status (call :post "/books" "[1,2]"))))
    (is (= 400 (:status (call :post "/books")))))
  (testing "nothing was stored"
    (is (= [] (:json (call :get "/books"))))))

(deftest list-and-filter-test
  (call :post "/books" dune)
  (call :post "/books" {:title "Children of Dune" :author "Frank Herbert" :year 1976})
  (call :post "/books" {:title "Emma" :author "Jane Austen" :year 1815})
  (is (= 3 (count (:json (call :get "/books")))))
  (let [resp (call :get "/books?author=Frank%20Herbert")]
    (is (= 200 (:status resp)))
    (is (= ["Dune" "Children of Dune"] (map :title (:json resp)))))
  (is (= [] (:json (call :get "/books?author=Nobody")))))

(deftest update-test
  (let [id   (get-in (call :post "/books" dune) [:json :id])
        resp (call :put (str "/books/" id) {:title "Dune Messiah" :author "Frank Herbert" :year 1969})]
    (is (= 200 (:status resp)))
    (is (= {:id id :title "Dune Messiah" :author "Frank Herbert" :year 1969 :isbn nil}
           (:json resp)))
    (is (= "Dune Messiah" (get-in (call :get (str "/books/" id)) [:json :title])))
    (testing "invalid update is rejected and leaves the book unchanged"
      (is (= 400 (:status (call :put (str "/books/" id) {:title "" :author "X"}))))
      (is (= "Dune Messiah" (get-in (call :get (str "/books/" id)) [:json :title]))))
    (testing "unknown id"
      (is (= 404 (:status (call :put "/books/9999" dune)))))))

(deftest body-parsed-regardless-of-content-type-test
  (let [resp (*app* (-> (mock/request :post "/books")
                        (mock/body (json/generate-string dune))
                        (mock/content-type "application/x-www-form-urlencoded")))]
    (is (= 201 (:status resp)))))

(deftest delete-test
  (let [id (get-in (call :post "/books" dune) [:json :id])]
    (is (= 204 (:status (call :delete (str "/books/" id)))))
    (is (= 404 (:status (call :get (str "/books/" id)))))
    (is (= 404 (:status (call :delete (str "/books/" id)))))))

(deftest not-found-test
  (is (= 404 (:status (call :get "/books/9999"))))
  (is (= 404 (:status (call :get "/books/abc"))))
  (is (= 404 (:status (call :get "/nope")))))
