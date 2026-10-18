(ns book-api.core
  (:gen-class)
  (:require [clojure.string :as str]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [book-api.db :as db]))

(defn- valid-book? [book]
  (and (map? book)
       (string? (:title book)) (not (str/blank? (:title book)))
       (string? (:author book)) (not (str/blank? (:author book)))
       (or (nil? (:year book)) (and (integer? (:year book)) (<= 0 (:year book) 9999)))
       (or (nil? (:isbn book)) (string? (:isbn book)))))

(defn- response [status body]
  {:status status
   :headers {"Content-Type" "application/json; charset=utf-8"}
   :body body})

(defn- parse-id [s]
  (try
    (let [id (Long/parseLong s)] (when (pos? id) id))
    (catch Exception _ nil)))

(defn- uri-id [uri]
  (when-let [[_ value] (re-matches #"/books/([^/]+)" uri)]
    (parse-id value)))

(defn app [request]
  (let [method (:request-method request)
        uri (:uri request)]
    (cond
      (and (= method :get) (= uri "/health"))
      (response 200 {:status "ok"})

      (and (= method :get) (= uri "/books"))
      (response 200 (db/list-books (get-in request [:query-params "author"])))

      (and (= method :post) (= uri "/books"))
      (if (valid-book? (:body request))
        (response 201 (db/create-book! (:body request)))
        (response 400 {:error "title and author are required; year and isbn must be valid"}))

      (and (string? uri) (re-matches #"/books/[^/]+" uri))
      (if-let [id (uri-id uri)]
        (case method
          :get (if-let [book (db/get-book id)] (response 200 book) (response 404 {:error "book not found"}))
          :put (if (valid-book? (:body request))
                 (if-let [book (db/update-book! id (:body request))]
                   (response 200 book)
                   (response 404 {:error "book not found"}))
                 (response 400 {:error "title and author are required; year and isbn must be valid"}))
          :delete (if (db/delete-book! id) (response 204 nil) (response 404 {:error "book not found"}))
          (response 405 {:error "method not allowed"}))
        (response 400 {:error "invalid book id"}))

      :else (response 404 {:error "not found"}))))

(def handler (-> app
                 (wrap-json-body {:keywords? true})
                 wrap-json-response))

(defn -main [& _]
  (db/initialize!)
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))]
    (jetty/run-jetty handler {:port port :join? true})))
