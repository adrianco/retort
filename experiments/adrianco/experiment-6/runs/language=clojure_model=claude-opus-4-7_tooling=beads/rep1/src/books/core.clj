(ns books.core
  (:require [books.db :as db]
            [books.handler :as handler]
            [ring.adapter.jetty :as jetty])
  (:gen-class))

(defn- env [k default]
  (or (System/getenv k) default))

(defn start
  "Initialize the database and start a Jetty server.

  Options:
    :port    HTTP port (default 3000 or env PORT)
    :db-file SQLite file (default books.db or env DB_FILE)
    :join?   block calling thread (default true)"
  ([] (start {}))
  ([{:keys [port db-file join?]
     :or   {join? true}}]
   (let [port    (Integer/parseInt (str (or port (env "PORT" "3000"))))
         db-file (or db-file (env "DB_FILE" "books.db"))
         ds      (db/ds db-file)]
     (db/init-schema! ds)
     (println (str "Books API listening on http://localhost:" port " (db: " db-file ")"))
     (jetty/run-jetty (handler/app-routes ds)
                      {:port port :join? join?}))))

(defn -main [& _args]
  (start))
