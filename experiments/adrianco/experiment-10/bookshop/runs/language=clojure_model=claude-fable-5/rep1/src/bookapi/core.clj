(ns bookapi.core
  "Application entrypoint: wires the database to the HTTP server."
  (:require [ring.adapter.jetty :refer [run-jetty]]
            [bookapi.db :as db]
            [bookapi.handler :as handler])
  (:gen-class))

(defn -main [& _args]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))
        db-path (or (System/getenv "DB_PATH") "books.db")
        ds (db/make-datasource db-path)]
    (db/init! ds)
    (println (format "Book API listening on http://localhost:%d (db: %s)" port db-path))
    (run-jetty (handler/app ds) {:port port :join? true})))
