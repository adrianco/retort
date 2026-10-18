(ns books.core
  (:require [books.db :as db]
            [books.handler :as handler]
            [ring.adapter.jetty :as jetty])
  (:gen-class))

(defn -main [& _]
  (let [port (parse-long (or (System/getenv "PORT") "3000"))
        path (or (System/getenv "DB_PATH") "books.db")
        ds   (db/open path)]
    (jetty/run-jetty (handler/app ds) {:port port :join? true})))
