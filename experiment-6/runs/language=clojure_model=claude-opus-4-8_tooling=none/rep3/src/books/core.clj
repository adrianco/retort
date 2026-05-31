(ns books.core
  "Application entry point: wires the datasource to the HTTP server."
  (:require [books.db :as db]
            [books.handler :as handler]
            [ring.adapter.jetty :refer [run-jetty]])
  (:gen-class))

(defn start-server
  "Initialise the database and start a Jetty server. Returns the server."
  [{:keys [db-path port join?] :or {db-path "books.db" port 3000 join? true}}]
  (let [ds (db/datasource db-path)]
    (db/init-db! ds)
    (println (str "Starting books API on port " port " (db: " db-path ")"))
    (run-jetty (handler/app ds) {:port port :join? join?})))

(defn -main
  [& args]
  (let [port (if-let [p (first args)] (Long/parseLong p) 3000)]
    (start-server {:port port})))
