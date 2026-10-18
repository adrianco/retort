(ns book-api.core
  "Entry point: starts the book API server.
  Environment variables: PORT (default 3000), DB_PATH (default books.db)."
  (:require [book-api.db :as db]
            [book-api.handler :as handler]
            [ring.adapter.jetty :as jetty]))

(defn -main [& _]
  (let [port (Long/parseLong (or (System/getenv "PORT") "3000"))
        db-path (or (System/getenv "DB_PATH") "books.db")
        ds (db/make-datasource db-path)]
    (println (str "Book API listening on port " port " (db: " db-path ")"))
    (jetty/run-jetty (handler/make-handler ds) {:port port :join? true})))
