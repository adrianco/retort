(ns books.core
  (:require [books.db :as db]
            [books.handlers :as h]
            [reitit.ring :as ring]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.params :refer [wrap-params]])
  (:gen-class))

(defn app
  "Build the ring handler around the given datasource."
  [ds]
  (-> (ring/ring-handler
        (ring/router
          [["/health" {:get h/health-handler}]
           ["/books"
            {:get  (fn [req] (h/list-books-handler req ds))
             :post (fn [req] (h/create-book-handler req ds))}]
           ["/books/:id"
            {:get    (fn [req] (h/get-book-handler req ds))
             :put    (fn [req] (h/update-book-handler req ds))
             :delete (fn [req] (h/delete-book-handler req ds))}]])
        (ring/create-default-handler
          {:not-found (constantly
                        {:status 404
                         :headers {"Content-Type" "application/json"}
                         :body "{\"error\":\"Not found\"}"})}))
      wrap-params))

(defn start-server
  ([] (start-server {:port 3000 :db-path "books.db"}))
  ([{:keys [port db-path] :or {port 3000 db-path "books.db"}}]
   (let [ds (db/make-datasource db-path)]
     (db/init-schema! ds)
     (println (str "Starting Books API on http://localhost:" port " (db=" db-path ")"))
     (jetty/run-jetty (app ds) {:port port :join? false}))))

(defn -main [& args]
  (let [port (or (some-> (System/getenv "PORT") Integer/parseInt) 3000)
        db-path (or (System/getenv "DB_PATH") "books.db")]
    (start-server {:port port :db-path db-path})))
