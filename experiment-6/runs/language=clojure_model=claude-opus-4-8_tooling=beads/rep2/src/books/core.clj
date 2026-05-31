(ns books.core
  "Application entry point."
  (:require [ring.adapter.jetty :as jetty]
            [books.db :as db]
            [books.handler :as handler])
  (:gen-class))

(defn start-server
  "Initialise the database and start a Jetty server. Returns the server."
  [{:keys [port db-path join?] :or {port 3000 db-path "books.db" join? false}}]
  (let [ds (db/make-datasource db-path)]
    (db/init-schema! ds)
    (jetty/run-jetty (handler/app ds) {:port port :join? join?})))

(defn -main
  [& args]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))
        db-path (or (System/getenv "DB_PATH") "books.db")]
    (println (str "Starting books API on port " port " (db: " db-path ")"))
    (start-server {:port port :db-path db-path :join? true})))
