(ns book-api.core-test
  (:require [clojure.test :refer :all]
            [cheshire.core :as json]
            [book-api.core :as core]
            [book-api.db :as db]))

(defn body [response]
  (if (string? (:body response)) (json/parse-string (:body response) true) (:body response)))

(defn fixture-app [f]
  (let [file (java.io.File/createTempFile "books-test" ".sqlite")
        database (db/db-spec (.getAbsolutePath file))]
    (try
      (db/initialize! database)
      (f database (core/app database))
      (finally
        (.delete file)))))

(deftest create-list-and-filter-books
  (fixture-app (fn [_ app]
    (is (= 201 (:status (app {:request-method :post :uri "/books" :body {:title "Dune" :author "Frank Herbert" :year 1965}}))))
    (is (= 201 (:status (app {:request-method :post :uri "/books" :body {:title "Foundation" :author "Isaac Asimov"}}))))
    (is (= 2 (count (body (app {:request-method :get :uri "/books"})))))
    (is (= 1 (count (body (app {:request-method :get :uri "/books" :query-params {"author" "frank herbert"}}))))))))

(deftest validate-required-fields-and-health
  (fixture-app (fn [_ app]
    (is (= 400 (:status (app {:request-method :post :uri "/books" :body {:title "No author"}}))))
    (is (= 200 (:status (app {:request-method :get :uri "/health"})))))))

(deftest get-update-delete-book
  (fixture-app (fn [_ app]
    (let [created (body (app {:request-method :post :uri "/books" :body {:title "Old" :author "Writer"}}))
          id (:id created)
          path (str "/books/" id)]
      (is (= 200 (:status (app {:request-method :get :uri path}))))
      (is (= "New" (:title (body (app {:request-method :put :uri path :body {:title "New" :author "Writer"}})))))
      (is (= 204 (:status (app {:request-method :delete :uri path}))))
      (is (= 404 (:status (app {:request-method :get :uri path}))))))))
