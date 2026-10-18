(ns book-api.core
  (:require [clojure.string :as str]
            [compojure.core :refer [defroutes GET POST PUT DELETE ANY]]
            [compojure.route :as route]
            [ring.adapter.jetty :refer [run-jetty]]
            [ring.middleware.params :refer [wrap-params]]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [book-api.db :as db]))

(defn- response [status body]
  {:status status :headers {"Content-Type" "application/json; charset=utf-8"} :body body})

(defn- valid-book? [book]
  (and (map? book)
       (string? (:title book)) (not (str/blank? (:title book)))
       (string? (:author book)) (not (str/blank? (:author book)))
       (or (nil? (:year book)) (integer? (:year book)))
       (or (nil? (:isbn book)) (string? (:isbn book)))))

(defn- parse-id [id]
  (when (and (string? id) (re-matches #"[1-9][0-9]*" id))
    (try (Long/parseLong id) (catch NumberFormatException _ nil))))

(defroutes app-routes
  (GET "/health" [] (response 200 {:status "ok"}))
  (POST "/books" req
    (let [book (:body req)]
      (if (valid-book? book)
        (response 201 (db/create-book (select-keys book [:title :author :year :isbn])))
        (response 400 {:error "title and author are required; year must be an integer and isbn a string"}))))
  (GET "/books" req (response 200 (db/all-books (or (get-in req [:query-params :author])
                                                     (get-in req [:params "author"])
                                                     (get-in req [:params :author])))))
  (GET "/books/:id" [id]
    (if-let [book (some-> (parse-id id) db/find-book)]
      (response 200 book)
      (response 404 {:error "Book not found"})))
  (PUT "/books/:id" [id :as req]
    (let [book (:body req)
          book-id (parse-id id)]
      (if-not (and book-id (valid-book? book))
        (response 400 {:error "title and author are required; year must be an integer and isbn a string"})
        (if-let [updated (db/update-book book-id (select-keys book [:title :author :year :isbn]))]
          (response 200 updated)
          (response 404 {:error "Book not found"})))))
  (DELETE "/books/:id" [id]
    (if (some-> (parse-id id) db/delete-book)
      (response 204 nil)
      (response 404 {:error "Book not found"})))
  (route/not-found (response 404 {:error "Not found"})))

(def app (wrap-json-response
          (wrap-json-body
           (wrap-params app-routes)
           {:keywords? true})))

(defn -main [& _]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))]
    (run-jetty app {:port port :join? true})))
