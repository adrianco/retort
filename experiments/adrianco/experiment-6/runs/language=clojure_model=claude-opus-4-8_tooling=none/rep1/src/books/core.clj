(ns books.core
  "Application entry point."
  (:require [books.db :as db]
            [books.handler :as handler]
            [ring.adapter.jetty :refer [run-jetty]])
  (:gen-class))

(defn -main
  "Start the HTTP server. Env vars: PORT (default 3000), DB_FILE (default books.db)."
  [& _args]
  (let [port    (Integer/parseInt (or (System/getenv "PORT") "3000"))
        db-file (or (System/getenv "DB_FILE") "books.db")
        ds      (db/make-datasource db-file)]
    (db/init-schema! ds)
    (println (str "Starting books API on port " port " (db: " db-file ")"))
    (run-jetty (handler/make-app ds) {:port port :join? true})))
