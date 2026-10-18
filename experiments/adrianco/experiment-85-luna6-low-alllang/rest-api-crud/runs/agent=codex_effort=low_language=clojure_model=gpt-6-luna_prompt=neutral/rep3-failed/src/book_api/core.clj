(ns book-api.core
  (:require [cheshire.core :as json]
            [compojure.core :refer [defroutes GET POST PUT DELETE ANY]]
            [compojure.route :as route]
            [ring.adapter.jetty :refer [run-jetty]]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [book-api.db :as db]))

(defn- response [status body]
  {:status status :headers {"Content-Type" "application/json; charset=utf-8"} :body body})

(defn- valid-book? [book]
  (and (map? book)
       (string? (:title book)) (not (clojure.string/blank? (:title book)))
       (string? (:author book)) (not (clojure.string/blank? (:author book)))
       (or (nil? (:year book)) (integer? (:year book)))
       (or (nil? (:isbn book)) (string? (:isbn book)))))

(defroutes app-routes
  (GET "/health" [] (response 200 {:status "ok"}))
  (POST "/books" req
    (let [book (:body req)]
      (if (valid-book? book)
        (response 201 (db/create-book (select-keys book [:title :author :year :isbn])))
        (response 400 {:error "title and author are required; year must be an integer and isbn a string"}))))
  (GET "/books" req (response 200 (db/all-books (get-in req [:params :author]))))
  (GET "/books/:id" [id]
    (if-let [book (db/find-book (parse-long id))]
      (response 200 book)
      (response 404 {:error "Book not found"})))
  (PUT "/books/:id" [id :as req]
    (let [book (:body req)]
      (if-not (valid-book? book)
        (response 400 {:error "title and author are required; year must be an integer and isbn a string"})
        (if-let [updated (db/update-book (parse-long id) (select-keys book [:title :author :year :isbn]))]
          (response 200 updated)
          (response 404 {:error "Book not found"})))))
  (DELETE "/books/:id" [id]
    (if (db/delete-book (parse-long id))
      (response 204 nil)
      (response 404 {:error "Book not found"})))
  (route/not-found (response 404 {:error "Not found"})))

(def app (-> app-routes wrap-json-response (wrap-json-body {:keywords? true})))

(defn -main [& _]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))]
    (run-jetty app {:port port :join? true})))
