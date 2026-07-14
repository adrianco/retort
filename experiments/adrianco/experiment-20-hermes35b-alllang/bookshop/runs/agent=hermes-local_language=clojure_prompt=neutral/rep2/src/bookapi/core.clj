(ns bookapi.core
  (:require [bookapi.db :as db]
            [bookapi.routes :as routes]
            [ring.adapter.jetty :as jetty]))

(defn -main [& [port]]
  (let [port (Integer/parseInt (or port "3000"))]
    (db/init-db!)
    (println (str "Starting server on port " port))
    (jetty/run-jetty routes/app {:port port :join? false}))
  (System/exit 0))
