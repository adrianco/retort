(ns books.core
  (:require [ring.adapter.jetty :as jetty]
            [books.db :as db]
            [books.routes :as routes])
  (:gen-class))

(defn start-server
  ([] (start-server {}))
  ([{:keys [port db-path join?] :or {port 3000 db-path "books.db" join? true}}]
   (let [ds (db/create-datasource {:dbtype "sqlite" :dbname db-path})]
     (db/init-db! ds)
     (jetty/run-jetty (routes/app ds) {:port port :join? join?}))))

(defn -main [& _args]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))
        db-path (or (System/getenv "DB_PATH") "books.db")]
    (println (str "Starting books API on port " port " (db=" db-path ")"))
    (start-server {:port port :db-path db-path :join? true})))
