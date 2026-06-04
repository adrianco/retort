(ns books.core
  "Application entry point — wires the database and starts the HTTP server."
  (:require [books.db :as db]
            [books.handler :as handler]
            [ring.adapter.jetty :refer [run-jetty]])
  (:gen-class))

(defn start-server
  "Initialize the database and start a Jetty server. Returns the server."
  [{:keys [port db-spec join?] :or {port 3000 join? true}}]
  (let [ds (db/datasource (or db-spec db/default-db))]
    (db/init-db! ds)
    (run-jetty (handler/app ds) {:port port :join? join?})))

(defn -main
  "Start the book API on the port given by PORT (default 3000)."
  [& _args]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))]
    (println (str "Starting book API on port " port))
    (start-server {:port port})))
