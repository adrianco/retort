(ns books.core
  "Application entry point: wires up the database and starts the Jetty server."
  (:require [books.db :as db]
            [books.handler :as handler]
            [ring.adapter.jetty :as jetty])
  (:gen-class))

(defn start-server
  "Initialise the database and start a Jetty server. Returns the server."
  [{:keys [port db-path join?] :or {port 3000 db-path "books.db" join? true}}]
  (let [ds (db/make-datasource db-path)]
    (db/init-schema! ds)
    (println (str "Starting books API on http://localhost:" port))
    (jetty/run-jetty (handler/make-handler ds) {:port port :join? join?})))

(defn -main
  "CLI entry point. Reads PORT and DB_PATH from the environment."
  [& _args]
  (let [port    (Integer/parseInt (or (System/getenv "PORT") "3000"))
        db-path (or (System/getenv "DB_PATH") "books.db")]
    (start-server {:port port :db-path db-path :join? true})))
