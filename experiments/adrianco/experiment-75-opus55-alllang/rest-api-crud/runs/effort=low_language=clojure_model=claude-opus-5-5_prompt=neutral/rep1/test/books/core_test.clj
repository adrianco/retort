(ns books.core-test
  (:require [books.core :as core]
            [books.db :as db]
            [cheshire.core :as json]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing]]
            [ring.mock.request :as mock]))

(defn fresh-app []
  (let [f (java.io.File/createTempFile "books" ".db")]
    (.deleteOnExit f)
    (io/delete-file f)
    (core/app (db/make-ds (.getPath f)))))

(defn req [app method uri & [body]]
  (let [r (app (cond-> (mock/request method uri)
                 body (mock/json-body body)))]
    (assoc r :json (when (seq (:body r)) (json/parse-string (:body r) true)))))

(deftest health
  (let [r (req (fresh-app) :get "/health")]
    (is (= 200 (:status r)))
    (is (= "ok" (get-in r [:json :status])))))

(deftest crud-flow
  (let [app (fresh-app)
        c (req app :post "/books" {:title "Dune" :author "Herbert" :year 1965 :isbn "123"})
        id (get-in c [:json :id])]
    (is (= 201 (:status c)))
    (is (= "Dune" (get-in c [:json :title])))
    (is (= 200 (:status (req app :get (str "/books/" id)))))
    (let [u (req app :put (str "/books/" id) {:title "Dune Messiah" :author "Herbert" :year 1969})]
      (is (= 200 (:status u)))
      (is (= 1969 (get-in u [:json :year]))))
    (is (= 204 (:status (req app :delete (str "/books/" id)))))
    (is (= 404 (:status (req app :get (str "/books/" id)))))
    (is (= 404 (:status (req app :delete (str "/books/" id)))))
    (is (= 404 (:status (req app :put "/books/999" {:title "x" :author "y"}))))))

(deftest validation
  (let [app (fresh-app)]
    (testing "missing title and author"
      (let [r (req app :post "/books" {:year 2000})]
        (is (= 400 (:status r)))
        (is (= 2 (count (get-in r [:json :errors]))))))
    (testing "bad year"
      (is (= 400 (:status (req app :post "/books" {:title "a" :author "b" :year "x"})))))
    (testing "malformed json"
      (is (= 400 (:status (app (-> (mock/request :post "/books" "{bad")
                                   (mock/content-type "application/json")))))))))

(deftest author-filter
  (let [app (fresh-app)]
    (req app :post "/books" {:title "A" :author "X"})
    (req app :post "/books" {:title "B" :author "Y"})
    (req app :post "/books" {:title "C" :author "X"})
    (is (= 3 (count (:json (req app :get "/books")))))
    (is (= ["A" "C"] (map :title (:json (req app :get "/books?author=X")))))))
