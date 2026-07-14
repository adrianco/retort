(ns books.core
  (:require [ring.adapter.jetty :as jetty]
            [books.db :as db]
            [books.handler :as handler])
  (:gen-class))

(defn -main [& args]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))
        ds   (db/make-datasource db/default-spec)]
    (db/init-schema! ds)
    (println (str "Starting server on port " port))
    (jetty/run-jetty (handler/make-app ds) {:port port :join? true})))
