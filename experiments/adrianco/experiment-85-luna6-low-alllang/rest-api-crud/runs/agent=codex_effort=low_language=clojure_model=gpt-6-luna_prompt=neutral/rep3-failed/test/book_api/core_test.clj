(ns book-api.core-test
  (:require [clojure.test :refer :all]
            [cheshire.core :as json]
            [book-api.core :as api]
            [book-api.db :as db])
  (:import [java.io ByteArrayInputStream]))

(use-fixtures :each (fn [f] (db/reset-db!) (try (f) (finally (db/reset-db!)))))

(defn request [method uri & [body]]
  (let [response (api/app {:request-method method :uri uri :headers {"content-type" "application/json"}
                           :body (when body (ByteArrayInputStream. (.getBytes (json/generate-string body) "UTF-8")))} )]
    (update response :body #(if (string? %) (json/parse-string % true) %))))

(deftest health-check
  (is (= 200 (:status (request :get "/health")))))

(deftest create-requires-title-and-author
  (is (= 400 (:status (request :post "/books" {:title "Only title"}))))
  (is (= 201 (:status (request :post "/books" {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "123"}))))
  (is (= "Dune" (:title (:body (request :get "/books/1"))))))

(deftest author-filter-and-crud
  (request :post "/books" {:title "Dune" :author "Frank Herbert"})
  (request :post "/books" {:title "Foundation" :author "Isaac Asimov"})
  (is (= 1 (count (:body (request :get "/books?author=Frank%20Herbert")))))
  (is (= 200 (:status (request :put "/books/1" {:title "Dune Messiah" :author "Frank Herbert"}))))
  (is (= "Dune Messiah" (:title (:body (request :get "/books/1")))))
  (is (= 204 (:status (request :delete "/books/1"))))
  (is (= 404 (:status (request :get "/books/1")))))
