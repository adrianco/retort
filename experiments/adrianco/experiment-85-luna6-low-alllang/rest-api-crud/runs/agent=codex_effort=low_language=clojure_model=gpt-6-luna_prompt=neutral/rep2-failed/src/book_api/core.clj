(ns book-api.core
  (:require [clojure.string :as str]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [book-api.db :as db]))

(defn- response [status body]
  {:status status :headers {"Content-Type" "application/json; charset=utf-8"} :body body})

(defn- valid-book? [book]
  (and (map? book)
       (string? (:title book)) (not (str/blank? (:title book)))
       (string? (:author book)) (not (str/blank? (:author book)))))

(defn app [database]
  (-> (fn [{:keys [request-method uri query-params body]}]
        (cond
          (and (= request-method :get) (= uri "/health"))
          (response 200 {:status "ok"})

          (and (= request-method :get) (= uri "/books"))
          (response 200 (db/list-books database (get query-params "author")))

          (and (= request-method :post) (= uri "/books"))
          (if (valid-book? body)
            (response 201 (db/create-book! database body))
            (response 400 {:error "title and author are required"}))

          :else
          (if-let [[_ raw-id] (re-matches #"/books/(\d+)" uri)]
            (let [id (Long/parseLong raw-id)]
              (case request-method
                :get (if-let [book (db/find-book database id)]
                       (response 200 book)
                       (response 404 {:error "book not found"}))
                :put (if-not (valid-book? body)
                       (response 400 {:error "title and author are required"})
                       (if-let [book (db/update-book! database id body)]
                         (response 200 book)
                         (response 404 {:error "book not found"})))
                :delete (if (db/delete-book! database id)
                          (response 204 nil)
                          (response 404 {:error "book not found"}))
                (response 405 {:error "method not allowed"})))
            (response 404 {:error "not found"}))))
      (wrap-json-body {:keywords? true})
      wrap-json-response))

(defn -main [& _]
  (let [database (db/db-spec (or (System/getenv "BOOKS_DB") "books.sqlite"))]
    (db/initialize! database)
    (jetty/run-jetty (app database) {:port (Integer/parseInt (or (System/getenv "PORT") "3000")) :join? true})))
