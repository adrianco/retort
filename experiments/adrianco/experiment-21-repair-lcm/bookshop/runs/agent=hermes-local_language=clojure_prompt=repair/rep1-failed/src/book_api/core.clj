(ns book-api.core
  (:require [book-api.handler :as handler]
            [book-api.db :as db]
            [ring.adapter.jetty :as jetty]))

(defn -main [& [port]]
  (db/init-db!)
  (jetty/run-jetty handler/app
                   {:port (or (some-> port Long/parseLong) 3000)
                    :join? false}))
