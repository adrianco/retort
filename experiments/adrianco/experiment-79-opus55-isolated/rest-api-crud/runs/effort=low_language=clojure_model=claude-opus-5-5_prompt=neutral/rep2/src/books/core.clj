(ns books.core
  (:require [books.db :as db]
            [books.handler :as handler]
            [ring.adapter.jetty :refer [run-jetty]])
  (:gen-class))

(defn -main [& _]
  (let [port (parse-long (or (System/getenv "PORT") "3000"))
        path (or (System/getenv "DB_PATH") "books.db")
        ds (db/init! (db/datasource path))]
    (println (str "Listening on http://localhost:" port " (database: " path ")"))
    (run-jetty (handler/app ds) {:port port :join? true})))
