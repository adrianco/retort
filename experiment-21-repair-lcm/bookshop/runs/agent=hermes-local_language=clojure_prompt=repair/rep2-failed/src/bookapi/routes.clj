(ns bookapi.routes
  (:require [bookapi.handlers :as handlers]
            [ring.middleware.json :as json]
            [ring.middleware.params :as params]
            [ring.middleware.content-type :refer [wrap-content-type]]
            [ring.middleware.file-info :refer [wrap-file-info]]))

(defn app-handler [request]
  (let [method (:request-method request)
        uri (:uri request)
        base-uri (when (re-matches #"/books/\d+" uri)
                   (re-find #"/books/(\d+)" uri))]
    (cond
      ;; GET /health
      (and (= method :get) (= uri "/health"))
      (handlers/health)

      ;; POST /books
      (and (= method :post) (= uri "/books"))
      (handlers/create-book request)

      ;; GET /books (list)
      (and (= method :get) (= uri "/books"))
      (handlers/list-books request)

      ;; GET /books/:id
      (and (= method :get) base-uri)
      (handlers/get-book
        (assoc request :route-params {:id (second base-uri)}))

      ;; PUT /books/:id
      (and (= method :put) (re-matches #"/books/\d+" uri))
      (handlers/update-book
        (assoc request :route-params {:id (second (re-find #"/books/(\d+)" uri))}))

      ;; DELETE /books/:id
      (and (= method :delete) (re-matches #"/books/\d+" uri))
      (handlers/delete-book
        (assoc request :route-params {:id (second (re-find #"/books/(\d+)" uri))}))

      ;; Fallback
      :else
      (handlers/not-found "Not found")))

(def app
  (-> app-handler
      (json/wrap-json-body {:keywords? true :ignore-keys #{"id"}})
      params/wrap-params
      wrap-content-type
      wrap-file-info))
