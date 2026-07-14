(ns books.core
  (:require [ring.adapter.jetty :as jetty]
            [books.db :as db]
            [books.handler :as handler])
  (:gen-class))

(defn -main
  [& args]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))
        ds (db/init!)]
    (println (str "Starting books API on port " port))
    (jetty/run-jetty (handler/make-app ds) {:port port :join? true})))
