(ns book-service.core
  (:require [book-service.db :as db]
            [cheshire.core :as json]
            [clojure.string :as string]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.params :refer [wrap-params]]))

(defn json-response
  ([status body] {:status status
                  :headers {"Content-Type" "application/json; charset=utf-8"}
                  :body (json/generate-string body)})
  ([body] (json-response 200 body)))

(defn read-json [request]
  (try
    (when-let [body (:body request)]
      (json/parse-stream (java.io.InputStreamReader. body) true))
    (catch Exception _ ::invalid-json)))

(defn valid-book? [book]
  (and (map? book)
       (string? (:title book)) (not (string/blank? (:title book)))
       (string? (:author book)) (not (string/blank? (:author book)))
       (or (nil? (:year book)) (integer? (:year book)))
       (or (nil? (:isbn book)) (string? (:isbn book)))))

(defn invalid-book-response []
  (json-response 400 {:error "title and author are required; year must be an integer and isbn must be a string"}))

(defn parse-id [s]
  (when (re-matches #"[1-9][0-9]*" s)
    (Long/parseLong s)))

(defn app [database-url]
  (db/initialize! database-url)
  (wrap-params
   (fn [request]
     (let [method (:request-method request)
           uri (:uri request)
           id-match (re-matches #"/books/([^/]+)" uri)
           id (some-> id-match second parse-id)]
       (cond
         (and (= method :get) (= uri "/health"))
         (json-response {:status "ok"})

         (and (= method :get) (= uri "/books"))
         (json-response (db/list-books database-url (get-in request [:params "author"])))

         (and (= method :post) (= uri "/books"))
         (let [book (read-json request)]
           (if (valid-book? book)
             (json-response 201 (db/create-book! database-url book))
             (invalid-book-response)))

         (and (= method :get) id-match (nil? id)) (json-response 400 {:error "invalid book id"})
         (and (= method :put) id-match (nil? id)) (json-response 400 {:error "invalid book id"})
         (and (= method :delete) id-match (nil? id)) (json-response 400 {:error "invalid book id"})

         (and (= method :get) id)
         (if-let [book (db/get-book database-url id)] (json-response book) (json-response 404 {:error "book not found"}))

         (and (= method :put) id)
         (let [book (read-json request)]
           (if-not (valid-book? book)
             (invalid-book-response)
             (if-let [updated (db/update-book! database-url id book)]
               (json-response updated)
               (json-response 404 {:error "book not found"}))))

         (and (= method :delete) id)
         (if (db/delete-book! database-url id)
           {:status 204 :body ""}
           (json-response 404 {:error "book not found"}))

         :else (json-response 404 {:error "not found"}))))))

(defn -main [& _]
  (let [database-url (or (System/getenv "DATABASE_URL") "jdbc:sqlite:books.db")
        port (Integer/parseInt (or (System/getenv "PORT") "3000"))]
    (println (str "Book service listening on port " port))
    (jetty/run-jetty (app database-url) {:port port :join? true})))
