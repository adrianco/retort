(ns bookapi.handler
  (:require [clojure.string :as str]
            [compojure.core :refer [routes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [ring.middleware.params :refer [wrap-params]]
            [ring.util.response :as resp]
            [bookapi.db :as db]))

(defn- validate-book
  "Return a vector of validation error messages (empty when valid)."
  [body]
  (cond-> []
    (not (map? body))
    (conj "request body must be a JSON object")

    (and (map? body) (str/blank? (str (:title body))))
    (conj "title is required")

    (and (map? body) (str/blank? (str (:author body))))
    (conj "author is required")

    (and (map? body) (some? (:year body)) (not (integer? (:year body))))
    (conj "year must be an integer")))

(defn- parse-id [s]
  (try (Long/parseLong s) (catch NumberFormatException _ nil)))

(defn- book-fields [body]
  (select-keys body [:title :author :year :isbn]))

(defn- not-found-body []
  {:error "book not found"})

(defn app-routes [ds]
  (routes
    (GET "/health" []
      (resp/response {:status "ok"}))

    (POST "/books" {body :body}
      (let [errors (validate-book body)]
        (if (seq errors)
          (-> (resp/response {:errors errors}) (resp/status 400))
          (-> (resp/response (db/create-book! ds (book-fields body)))
              (resp/status 201)))))

    (GET "/books" {params :query-params}
      (resp/response (db/list-books ds (get params "author"))))

    (GET "/books/:id" [id]
      (if-let [book (some->> (parse-id id) (db/get-book ds))]
        (resp/response book)
        (-> (resp/response (not-found-body)) (resp/status 404))))

    (PUT "/books/:id" {body :body {:keys [id]} :params}
      (let [errors (validate-book body)]
        (cond
          (seq errors)
          (-> (resp/response {:errors errors}) (resp/status 400))

          :else
          (if-let [book (some-> (parse-id id)
                                (as-> i (db/update-book! ds i (book-fields body))))]
            (resp/response book)
            (-> (resp/response (not-found-body)) (resp/status 404))))))

    (DELETE "/books/:id" [id]
      (if (some->> (parse-id id) (db/delete-book! ds))
        {:status 204 :headers {} :body nil}
        (-> (resp/response (not-found-body)) (resp/status 404))))

    (route/not-found {:body {:error "not found"}})))

(defn make-app
  "Build the Ring handler for the given datasource."
  [ds]
  (-> (app-routes ds)
      wrap-params
      (wrap-json-body {:keywords? true})
      wrap-json-response))
