(ns books.core
  (:require [ring.adapter.jetty :refer [run-jetty]]
            [books.db :as db]
            [books.handler :as handler]))

(defn -main [& _]
  (let [port    (parse-long (or (System/getenv "PORT") "3000"))
        db-path (or (System/getenv "DB_PATH") "books.db")
        ds      (db/datasource db-path)]
    (println (str "Books API listening on http://localhost:" port " (db: " db-path ")"))
    (run-jetty (handler/app ds) {:port port :join? true})))
