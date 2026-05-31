(ns books.handlers
  "Request handlers and validation for the book API."
  (:require [books.db :as db]))

(defn- error
  "Build a JSON error response with the given status."
  [status message]
  {:status status :body {:error message}})

(defn- validate
  "Validate a book payload. Returns a vector of error strings (empty if valid).
   Title and author are required; year, when present, must be an integer."
  [{:keys [title author year]}]
  (cond-> []
    (or (nil? title) (and (string? title) (clojure.string/blank? title)))
    (conj "title is required")

    (or (nil? author) (and (string? author) (clojure.string/blank? author)))
    (conj "author is required")

    (and (some? year) (not (integer? year)))
    (conj "year must be an integer")))

(defn- parse-id
  "Parse a path id string into a long, or nil if invalid."
  [s]
  (try (Long/parseLong s) (catch Exception _ nil)))

(defn health
  "Liveness check."
  [_]
  {:status 200 :body {:status "ok"}})

(defn create-book [ds]
  (fn [request]
    (let [body   (:body-params request)
          errors (validate body)]
      (if (seq errors)
        (error 400 (clojure.string/join "; " errors))
        {:status 201 :body (db/create-book! ds body)}))))

(defn list-books [ds]
  (fn [request]
    (let [author (get-in request [:query-params "author"])]
      {:status 200 :body (db/list-books ds author)})))

(defn get-book [ds]
  (fn [request]
    (if-let [id (parse-id (get-in request [:path-params :id]))]
      (if-let [book (db/get-book ds id)]
        {:status 200 :body book}
        (error 404 "book not found"))
      (error 400 "invalid id"))))

(defn update-book [ds]
  (fn [request]
    (if-let [id (parse-id (get-in request [:path-params :id]))]
      (let [body   (:body-params request)
            errors (validate body)]
        (if (seq errors)
          (error 400 (clojure.string/join "; " errors))
          (if-let [book (db/update-book! ds id body)]
            {:status 200 :body book}
            (error 404 "book not found"))))
      (error 400 "invalid id"))))

(defn delete-book [ds]
  (fn [request]
    (if-let [id (parse-id (get-in request [:path-params :id]))]
      (if (db/delete-book! ds id)
        {:status 204 :body nil}
        (error 404 "book not found"))
      (error 400 "invalid id"))))
