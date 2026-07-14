(ns books.handler
  "HTTP routing, request validation, and JSON responses."
  (:require [compojure.core :refer [defroutes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [ring.middleware.params :refer [wrap-params]]
            [ring.middleware.keyword-params :refer [wrap-keyword-params]]
            [ring.util.response :as resp]
            [books.db :as db]))

(defn- parse-id
  "Parse a path id into a long, or nil if it is not a valid integer."
  [s]
  (try (Long/parseLong s) (catch Exception _ nil)))

(defn- validate-book
  "Return a seq of validation error messages for a book payload."
  [{:keys [title author year]}]
  (cond-> []
    (not (and (string? title) (seq (.trim ^String title))))
    (conj "title is required")

    (not (and (string? author) (seq (.trim ^String author))))
    (conj "author is required")

    (and (some? year) (not (integer? year)))
    (conj "year must be an integer")))

(defn- bad-request [errors]
  (-> (resp/response {:errors errors})
      (resp/status 400)))

(defn- not-found []
  (-> (resp/response {:error "book not found"})
      (resp/status 404)))

(defn create-handler
  "Build the Ring handler closing over the datasource."
  [ds]
  (defroutes routes
    (GET "/health" []
      (resp/response {:status "ok"}))

    (GET "/books" [author]
      (resp/response (db/list-books ds author)))

    (POST "/books" {body :body}
      (let [errors (validate-book body)]
        (if (seq errors)
          (bad-request errors)
          (-> (resp/response (db/create-book! ds body))
              (resp/status 201)))))

    (GET "/books/:id" [id]
      (if-let [pid (parse-id id)]
        (if-let [book (db/get-book ds pid)]
          (resp/response book)
          (not-found))
        (not-found)))

    (PUT "/books/:id" {body :body {id :id} :params}
      (let [pid (parse-id id)
            errors (validate-book body)]
        (cond
          (nil? pid) (not-found)
          (seq errors) (bad-request errors)
          :else (if-let [updated (db/update-book! ds pid body)]
                  (resp/response updated)
                  (not-found)))))

    (DELETE "/books/:id" [id]
      (if-let [pid (parse-id id)]
        (if (db/delete-book! ds pid)
          (-> (resp/response nil) (resp/status 204))
          (not-found))
        (not-found)))

    (route/not-found {:error "not found"})))

(defn app
  "Wrap the routes with JSON request/response middleware."
  [ds]
  (-> (create-handler ds)
      (wrap-keyword-params)
      (wrap-params)
      (wrap-json-body {:keywords? true})
      (wrap-json-response)))
