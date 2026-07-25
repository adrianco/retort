(ns book-api.core
  (:require [book-api.routes :as routes]
            [book-api.db :as db]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.json :as json-middleware]))

(defn init []
  (db/init-db)
  (println "Database initialized"))

(defn ^:dev/after-load reload []
  (init))

(defn -main []
  (init)
  (println "Starting Book API server on port 3000...")
  (jetty/run-jetty
    (-> routes/app
        (json-middleware/wrap-json-body {:keywords? true})
        json-middleware/wrap-json-response)
    {:port 3000
     :join? false}))
