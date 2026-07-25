(ns book-api.core
  "Entry point: wire up the database and start the Jetty server."
  (:require [book-api.db :as db]
            [book-api.handler :as handler]
            [ring.adapter.jetty :as jetty])
  (:gen-class))

(def default-port 3000)
(def default-db-path "books.db")

(defn- env
  [k default]
  (or (System/getenv k) default))

(defn start-server
  "Start Jetty and return the server instance.
  Options: :port, :db-path, :join? (block the calling thread)."
  [{:keys [port db-path join?]
    :or   {port default-port, db-path default-db-path, join? false}}]
  (let [ds (db/migrate! (db/datasource db-path))]
    (println (format "book-api listening on http://localhost:%d (db: %s)" port db-path))
    (jetty/run-jetty (handler/app ds) {:port port :join? join?})))

(defn -main [& _args]
  (start-server
   {:port    (Long/parseLong (env "PORT" (str default-port)))
    :db-path (env "BOOK_API_DB" default-db-path)
    :join?   true}))
