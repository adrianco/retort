(ns books.routes
  (:require [reitit.ring :as ring]
            [reitit.ring.middleware.muuntaja :as muuntaja]
            [reitit.ring.middleware.parameters :as parameters]
            [muuntaja.core :as m]
            [books.handlers :as h]))

(defn app [ds]
  (ring/ring-handler
    (ring/router
      [["/health" {:get h/health}]
       ["/books" {:get (h/list-books ds)
                  :post (h/create-book ds)}]
       ["/books/:id" {:get (h/get-book ds)
                      :put (h/update-book ds)
                      :delete (h/delete-book ds)}]]
      {:data {:muuntaja m/instance
              :middleware [parameters/parameters-middleware
                           muuntaja/format-middleware]}})
    (ring/create-default-handler
      {:not-found (constantly {:status 404
                               :headers {"Content-Type" "application/json"}
                               :body "{\"error\":\"Not found\"}"})})))
