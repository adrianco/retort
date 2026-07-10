(ns bookapi.routes
  (:require [bookapi.handlers :as handlers]
            [compojure.core :refer [defroutes GET POST PUT DELETE routes]]
            [ring.middleware.json :as json]
            [ring.middleware.params :as params]
            [ring.middleware.content-type :refer [wrap-content-type]]
            [ring.middleware.file-info :refer [wrap-file-info]]
            [ring.middleware.session :as session]))

(defroutes app-routes
  (GET "/health" [] (handlers/health))
  (GET "/books" request (handlers/list-books request))
  (GET "/books/:id" request (handlers/get-book request))
  (POST "/books" request (handlers/create-book request))
  (PUT "/books/:id" request (handlers/update-book request))
  (DELETE "/books/:id" request (handlers/delete-book request)))

(def app
  (-> app-routes
      (json/wrap-json-body {:keywords? true :ignore-keys #{"id"}})
      params/wrap-params
      json/wrap-json-response
      wrap-content-type
      wrap-file-info))
