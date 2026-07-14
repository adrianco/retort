(ns books.core
  "Application entry point: wire up the DB and start the Jetty server."
  (:require [books.db :as db]
            [books.handler :as handler]
            [ring.adapter.jetty :refer [run-jetty]])
  (:gen-class))

(def ^:private default-port 3000)
(def ^:private db-path "books.db")

(defn -main [& args]
  (let [port (Integer/parseInt (or (first args)
                                   (System/getenv "PORT")
                                   (str default-port)))
        ds (db/make-datasource db-path)]
    (db/init-schema! ds)
    (println (str "Starting Books API on http://localhost:" port))
    (run-jetty (handler/app-routes ds) {:port port :join? true})))
