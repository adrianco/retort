(ns book-api.core
  (:require [book-api.db :as db]
            [book-api.routes :as routes]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.json :as json-middleware])
  (:gen-class))

(def app
  (json-middleware/wrap-json-body routes/app-routes
                                  {:keywords? true
                                   :big-decimal? true}))

(defn -main []
  (db/init-db)
  (println "Starting server on port 3000...")
  (jetty/run-jetty app {:port 3000 :join? false}))
