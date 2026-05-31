(ns books.core
  "Routing, middleware, and server entry point for the book API."
  (:require [books.db :as db]
            [books.handlers :as h]
            [muuntaja.core :as m]
            [reitit.ring :as ring]
            [reitit.ring.middleware.muuntaja :as muuntaja]
            [reitit.ring.middleware.parameters :as parameters]
            [ring.adapter.jetty :as jetty])
  (:gen-class))

(defn app
  "Build the Ring handler backed by the given datasource."
  [ds]
  (ring/ring-handler
    (ring/router
      [["/health" {:get h/health}]
       ["/books"
        {:get  (h/list-books ds)
         :post (h/create-book ds)}]
       ["/books/:id"
        {:get    (h/get-book ds)
         :put    (h/update-book ds)
         :delete (h/delete-book ds)}]]
      {:data {:muuntaja   m/instance
              :middleware [parameters/parameters-middleware
                           muuntaja/format-middleware]}})
    (ring/create-default-handler
      {:not-found (constantly {:status 404 :body "{\"error\":\"not found\"}"})})))

(defn start
  "Initialise the schema and start a Jetty server. Returns the server."
  [{:keys [db-spec port join?] :or {db-spec db/default-db-spec port 3000 join? true}}]
  (let [ds (db/datasource db-spec)]
    (db/init-schema! ds)
    (jetty/run-jetty (app ds) {:port port :join? join?})))

(defn -main [& _]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))]
    (println (str "Starting book API on port " port))
    (start {:port port :join? true})))
