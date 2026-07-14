(ns books.handler
  "HTTP routes and request handling for the book collection API."
  (:require [books.db :as db]
            [clojure.string :as str]
            [compojure.core :refer [GET POST PUT DELETE routes]]
            [compojure.route :as route]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [ring.middleware.keyword-params :refer [wrap-keyword-params]]
            [ring.middleware.params :refer [wrap-params]]
            [ring.util.response :as resp]))

(defn- parse-id
  "Parse a path id into a long, or nil if it is not a valid integer."
  [s]
  (try (Long/parseLong s) (catch Exception _ nil)))

(defn- blank? [v]
  (or (nil? v) (and (string? v) (str/blank? v))))

(defn- validate
  "Return a seq of validation error messages for a book payload."
  [{:keys [title author]}]
  (cond-> []
    (blank? title)  (conj "title is required")
    (blank? author) (conj "author is required")))

(defn- bad-request [errors]
  (-> (resp/response {:errors errors})
      (resp/status 400)))

(defn- not-found []
  (-> (resp/response {:error "book not found"})
      (resp/status 404)))

(defn create-book [ds body]
  (let [errors (validate body)]
    (if (seq errors)
      (bad-request errors)
      (let [book (db/create-book! ds (select-keys body [:title :author :year :isbn]))]
        (-> (resp/response book)
            (resp/status 201))))))

(defn list-books [ds author]
  (resp/response (db/list-books ds author)))

(defn get-book [ds id-str]
  (if-let [id (parse-id id-str)]
    (if-let [book (db/get-book ds id)]
      (resp/response book)
      (not-found))
    (not-found)))

(defn update-book [ds id-str body]
  (if-let [id (parse-id id-str)]
    (let [errors (validate body)]
      (if (seq errors)
        (bad-request errors)
        (if-let [book (db/update-book! ds id (select-keys body [:title :author :year :isbn]))]
          (resp/response book)
          (not-found))))
    (not-found)))

(defn delete-book [ds id-str]
  (if-let [id (parse-id id-str)]
    (if (db/delete-book! ds id)
      (-> (resp/response {:deleted id}) (resp/status 200))
      (not-found))
    (not-found)))

(defn app-routes
  "Build the Ring handler, closing over the given datasource."
  [ds]
  (-> (routes
        (GET "/health" [] (resp/response {:status "ok"}))

        (POST "/books" {body :body} (create-book ds body))
        (GET "/books" [author] (list-books ds author))
        (GET "/books/:id" [id] (get-book ds id))
        (PUT "/books/:id" {body :body {id :id} :params} (update-book ds id body))
        (DELETE "/books/:id" [id] (delete-book ds id))

        (route/not-found {:error "not found"}))
      (wrap-keyword-params)
      (wrap-params)
      (wrap-json-body {:keywords? true})
      (wrap-json-response)))
