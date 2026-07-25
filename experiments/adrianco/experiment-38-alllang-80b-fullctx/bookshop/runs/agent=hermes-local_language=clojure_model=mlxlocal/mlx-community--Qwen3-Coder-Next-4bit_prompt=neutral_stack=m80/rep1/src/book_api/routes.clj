(ns book-api.routes
  (:require [compojure.api.sweet :as api]
            [ring.util.http-response :as response]
            [book-api.handlers :as handlers]))

(defroutes app-routes
  (api/POST "/books" []
            :summary "Create a new book"
            :body [params ::api/any]
            (handlers/create-book-handler params))
  (api/GET "/books" []
           :summary "List all books"
           :query-params [query-params ::api/any]
           (handlers/list-books-handler query-params))
  (api/GET "/books/:id" []
           :summary "Get a single book"
           :path-params [id ::api/any]
           (handlers/get-book-handler id))
  (api/PUT "/books/:id" []
           :summary "Update a book"
           :path-params [id ::api/any]
           :body [params ::api/any]
           (handlers/update-book-handler id params))
  (api/DELETE "/books/:id" []
              :summary "Delete a book"
              :path-params [id ::api/any]
              (handlers/delete-book-handler id))
  (api/GET "/health" []
           :summary "Health check endpoint"
           (handlers/health-handler nil))
  (api/ANY "/*" []
           (handlers/not-found-handler {})))

(def app
  (api/reify-routes app-routes))
