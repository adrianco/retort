(ns book-api.core-test
  (:require [clojure.string :as str]
            [clojure.test :refer :all]
            [cheshire.core :as json]
            [book-api.core :as api]
            [book-api.db :as db])
  (:import [java.io ByteArrayInputStream]))

(use-fixtures :each (fn [f] (db/reset-db!) (try (f) (finally (db/reset-db!)))))

(defn request [method uri & [body]]
  (let [[path query] (str/split uri #"\?" 2)
        response (api/app {:request-method method :uri path :query-string query :headers {"content-type" "application/json"}
                           :body (when body (ByteArrayInputStream. (.getBytes (json/generate-string body) "UTF-8")))} )]
    (update response :body #(if (string? %) (json/parse-string % true) %))))

(deftest health-check
  (is (= 200 (:status (request :get "/health"))))
  (is (= {"status" "ok"} (json/parse-string (:body (api/app {:request-method :get :uri "/health"}))))))

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

(deftest query-params-work-through-ring-middleware
  (request :post "/books" {:title "Dune" :author "Frank Herbert"})
  (request :post "/books" {:title "Foundation" :author "Isaac Asimov"})
  (let [result (request :get "/books?author=Isaac%20Asimov")]
    (is (= 200 (:status result)))
    (is (= ["Foundation"] (mapv :title (:body result))))))

(deftest bad-identifiers-and-invalid-fields-return-client-errors
  (is (= 404 (:status (request :get "/books/not-a-number"))))
  (is (= 404 (:status (request :delete "/books/999999999999999999999999999999"))))
  (is (= 400 (:status (request :post "/books" {:title "   " :author "Someone"}))))
  (is (= 400 (:status (request :post "/books" {:title "Book" :author "Someone" :year "2020"})))))
