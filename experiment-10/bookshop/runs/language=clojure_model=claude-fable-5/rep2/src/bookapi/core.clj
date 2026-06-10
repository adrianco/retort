(ns bookapi.core
  (:require [bookapi.db :as db]
            [bookapi.handler :as handler]
            [ring.adapter.jetty :as jetty])
  (:gen-class))

(defn -main [& _args]
  (let [port    (Integer/parseInt (or (System/getenv "PORT") "3000"))
        db-path (or (System/getenv "DB_PATH") "books.db")
        ds      (db/make-datasource db-path)]
    (db/init! ds)
    (println (str "Book API listening on http://localhost:" port
                  " (database: " db-path ")"))
    (jetty/run-jetty (handler/make-app ds) {:port port :join? true})))
