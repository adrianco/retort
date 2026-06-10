(ns bookapi.core
  (:require [ring.adapter.jetty :refer [run-jetty]]
            [bookapi.db :as db]
            [bookapi.handler :refer [make-app]])
  (:gen-class))

(defn -main [& _args]
  (let [port    (Integer/parseInt (or (System/getenv "PORT") "3000"))
        db-path (or (System/getenv "DB_PATH") "books.db")
        ds      (db/make-datasource db-path)]
    (db/init! ds)
    (println (str "Book API listening on http://localhost:" port " (db: " db-path ")"))
    (run-jetty (make-app ds) {:port port :join? true})))
