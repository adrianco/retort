(ns bookapi.handler
  (:require [bookapi.db :as db]
            [cheshire.core :as json]
            [clojure.string :as str]
            [compojure.core :refer [routes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.middleware.params :refer [wrap-params]]))

(defn- json-response [status body]
  {:status  status
   :headers {"Content-Type" "application/json"}
   :body    (json/generate-string body)})

(defn- parse-body
  "Returns the parsed JSON body, or ::invalid if it cannot be parsed."
  [request]
  (try
    (some-> (:body request) slurp not-empty (json/parse-string true))
    (catch Exception _ ::invalid)))

(defn- validation-error
  "Returns an error message string if the book payload is invalid, else nil."
  [book]
  (cond
    (= book ::invalid)
    "Request body must be valid JSON"

    (not (map? book))
    "Request body must be a JSON object"

    (or (not (string? (:title book))) (str/blank? (:title book)))
    "title is required and must be a non-empty string"

    (or (not (string? (:author book))) (str/blank? (:author book)))
    "author is required and must be a non-empty string"

    (and (some? (:year book)) (not (integer? (:year book))))
    "year must be an integer"

    (and (some? (:isbn book)) (not (string? (:isbn book))))
    "isbn must be a string"))

(defn- parse-id [s]
  (try (Long/parseLong s) (catch Exception _ nil)))

(defn- with-book-payload
  "Parses and validates the request body, then calls (f book).
  Responds 400 on validation failure."
  [request f]
  (let [book (parse-body request)]
    (if-let [err (validation-error book)]
      (json-response 400 {:error err})
      (f book))))

(defn- not-found-response []
  (json-response 404 {:error "Book not found"}))

(defn- app-routes [ds]
  (routes
   (GET "/health" []
     (json-response 200 {:status "ok"}))

   (POST "/books" request
     (with-book-payload request
       (fn [book]
         (json-response 201 (db/create-book! ds book)))))

   (GET "/books" [author]
     (json-response 200 (db/list-books ds author)))

   (GET "/books/:id" [id]
     (if-let [book (some->> (parse-id id) (db/get-book ds))]
       (json-response 200 book)
       (not-found-response)))

   (PUT "/books/:id" request
     (if-let [id (parse-id (get-in request [:params :id]))]
       (with-book-payload request
         (fn [book]
           (if-let [updated (db/update-book! ds id book)]
             (json-response 200 updated)
             (not-found-response))))
       (not-found-response)))

   (DELETE "/books/:id" [id]
     (if (some->> (parse-id id) (db/delete-book! ds))
       {:status 204 :headers {} :body nil}
       (not-found-response)))

   (route/not-found (json-response 404 {:error "Not found"}))))

(defn make-app [ds]
  (wrap-params (app-routes ds)))
