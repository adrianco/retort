(ns book-api.core
  (:require [ring.adapter.jetty :as jetty]
            [reitit.ring :as ring]
            [reitit.ring.middleware.muuntaja :as muuntaja]
            [muuntaja.core :as m]
            [book-api.db :as db]
            [book-api.handlers :as handlers])
  (:gen-class))

(def app
  (ring/ring-handler
   (ring/router
    [["/health" {:get handlers/health-handler}]
     ["/books"
      {:get handlers/list-books-handler
       :post handlers/create-book-handler}]
     ["/books/:id"
      {:get handlers/get-book-handler
       :put handlers/update-book-handler
       :delete handlers/delete-book-handler}]]
    {:data {:muuntaja m/instance
            :middleware [muuntaja/format-middleware]}})
   (ring/create-default-handler)))

(defn -main [& args]
  (db/init-db!)
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))]
    (println (str "Starting server on port " port))
    (jetty/run-jetty app {:port port :join? true})))
