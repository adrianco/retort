(ns book-api.core
  (:require [compojure.core :refer [defroutes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.json :refer [wrap-json-body]]
            [ring.middleware.params :refer [wrap-params]]
            [book-api.db :as db]
            [book-api.handlers :as h])
  (:gen-class))

(defroutes app-routes
  (GET  "/health"    req (h/health-handler req))
  (POST "/books"     req (h/create-book-handler req))
  (GET  "/books"     req (h/list-books-handler req))
  (GET  "/books/:id" req (h/get-book-handler req))
  (PUT  "/books/:id" req (h/update-book-handler req))
  (DELETE "/books/:id" req (h/delete-book-handler req))
  (route/not-found (h/json-response 404 {:error "Not found"})))

(def app
  (-> app-routes
      (wrap-json-body {:keywords? true})
      wrap-params))

(defn -main [& _args]
  (db/init-db!)
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))]
    (println (str "Book API server starting on port " port))
    (jetty/run-jetty app {:port port :join? true})))
