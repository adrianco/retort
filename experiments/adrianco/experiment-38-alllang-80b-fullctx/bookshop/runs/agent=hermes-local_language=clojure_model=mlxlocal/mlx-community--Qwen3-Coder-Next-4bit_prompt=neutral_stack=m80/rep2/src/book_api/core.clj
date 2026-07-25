(ns book-api.core
  (:require [book-api.handler :as handler]
            [ring.adapter.jetty :as jetty])
  (:gen-class))

(defn -main []
  "Start the Ring server"
  (println "Starting Book API server on port 3000...")
  (jetty/run-jetty handler/handler {:port 3000 :join? true}))
