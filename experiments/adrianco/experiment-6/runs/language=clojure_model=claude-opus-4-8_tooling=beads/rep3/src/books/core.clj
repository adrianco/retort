(ns books.core
  "Application entry point: routes, app wiring, and server startup."
  (:require [books.db :as db]
            [books.handlers :as h]
            [muuntaja.core :as m]
            [reitit.ring :as ring]
            [reitit.ring.middleware.muuntaja :as muuntaja]
            [reitit.ring.middleware.parameters :as parameters]
            [ring.adapter.jetty :as jetty])
  (:gen-class))

(defn routes [ds]
  [["/health" {:get h/health}]
   ["/books"
    {:get  (h/list-books ds)
     :post (h/create-book ds)}]
   ["/books/:id"
    {:get    (h/get-book ds)
     :put    (h/update-book ds)
     :delete (h/delete-book ds)}]])

(defn app
  "Build the Ring handler for the given datasource."
  [ds]
  (ring/ring-handler
   (ring/router
    (routes ds)
    {:data {:muuntaja m/instance
            :middleware [parameters/parameters-middleware
                         muuntaja/format-middleware]}})
   (ring/create-default-handler
    {:not-found (constantly {:status 404
                             :headers {"Content-Type" "application/json"}
                             :body "{\"error\":\"not found\"}"})})))

(defn start-server
  "Initialize the database and start a Jetty server."
  [{:keys [port db-file join?] :or {port 3000 db-file "books.db" join? true}}]
  (let [ds (db/make-datasource db-file)]
    (db/init-schema! ds)
    (println (str "Starting books API on http://localhost:" port))
    (jetty/run-jetty (app ds) {:port port :join? join?})))

(defn -main [& args]
  (let [port (if-let [p (first args)] (Integer/parseInt p) 3000)]
    (start-server {:port port :db-file "books.db"})))
