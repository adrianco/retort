(ns books.handler
  (:require [books.db :as db]
            [cheshire.core :as json]
            [clojure.string :as str]
            [compojure.core :refer [routes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.middleware.params :refer [assoc-query-params]]))

(defn- json-response [status body]
  {:status status
   :headers {"Content-Type" "application/json; charset=utf-8"}
   :body (json/generate-string body)})

(defn- error [status message & [details]]
  (json-response status (cond-> {:error message} details (assoc :details details))))

(defn- parse-body
  "Parses the request body as a JSON object. Returns nil if it is not one."
  [request]
  (try
    (let [parsed (some-> (:body request) slurp (json/parse-string true))]
      (when (map? parsed) parsed))
    (catch Exception _ nil)))

(defn validate
  "Returns a map of field -> message for every invalid field of `book`."
  [{:keys [title author year isbn]}]
  (cond-> {}
    (not (and (string? title) (not (str/blank? title))))
    (assoc :title "title is required and must be a non-empty string")

    (not (and (string? author) (not (str/blank? author))))
    (assoc :author "author is required and must be a non-empty string")

    (and (some? year) (not (integer? year)))
    (assoc :year "year must be an integer")

    (and (some? isbn) (not (string? isbn)))
    (assoc :isbn "isbn must be a string")))

(defn- with-valid-book
  "Calls `f` with the cleaned book from the request body, or returns a 400."
  [request f]
  (if-let [body (parse-body request)]
    (let [errors (validate body)]
      (if (seq errors)
        (error 400 "Validation failed" errors)
        (f (-> (select-keys body [:title :author :year :isbn])
               (update :title str/trim)
               (update :author str/trim)))))
    (error 400 "Request body must be a JSON object")))

(defn- parse-id [s]
  (try (Long/parseLong s) (catch NumberFormatException _ nil)))

(def ^:private not-found (error 404 "Book not found"))

(defn- book-routes [ds]
  (routes
   (GET "/health" [] (json-response 200 {:status "ok"}))

   (GET "/books" request
     (let [author (get-in request [:query-params "author"])]
       (json-response 200 (db/list-books ds (when-not (str/blank? author) author)))))

   (POST "/books" request
     (with-valid-book request
       #(json-response 201 (db/create-book! ds %))))

   (GET "/books/:id" [id]
     (if-let [book (some->> (parse-id id) (db/get-book ds))]
       (json-response 200 book)
       not-found))

   (PUT "/books/:id" [id :as request]
     (if-let [id (parse-id id)]
       (with-valid-book request
         #(if-let [book (db/update-book! ds id %)]
            (json-response 200 book)
            not-found))
       not-found))

   (DELETE "/books/:id" [id]
     (if (some->> (parse-id id) (db/delete-book! ds))
       {:status 204 :headers {} :body nil}
       not-found))

   (route/not-found (error 404 "Not found"))))

;; Only the query string is parsed: wrap-params would also consume a
;; form-encoded body, which is what curl sends when no Content-Type is given.
(defn- wrap-query-params [handler]
  (fn [request]
    (handler (assoc-query-params request "UTF-8"))))

(defn- wrap-errors [handler]
  (fn [request]
    (try
      (handler request)
      (catch Exception e
        (binding [*out* *err*] (println "Unhandled error:" (.getMessage e)))
        (error 500 "Internal server error")))))

(defn app
  "Builds the ring handler backed by datasource `ds`."
  [ds]
  (-> (book-routes ds)
      wrap-query-params
      wrap-errors))
