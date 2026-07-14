(ns book-api.core
  (:gen-class)
  (:require [ring.adapter.jetty :as jetty]
            [book-api.db :as db]
            [book-api.routes :as routes]))

(defn -main
  "Start the HTTP server on the given port (default 3000)."
  [& [port]]
  (let [port (Integer/parseInt (or port "3000"))]
    (db/init-db!)
    (println "Starting book-api server on port" port)
    (jetty/run-jetty #'routes/routes
      {:port port :join? true})))
