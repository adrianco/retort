(ns books.handlers
  "Request handlers for the book collection API."
  (:require [books.db :as db]
            [clojure.string :as str]))

(defn- parse-id
  "Parse a path id string to a long, or nil if it is not a valid integer."
  [s]
  (try
    (Long/parseLong s)
    (catch Exception _ nil)))

(defn- blank?
  [s]
  (or (nil? s) (and (string? s) (str/blank? s))))

(defn- validate-book
  "Return a vector of validation error messages for a book payload."
  [{:keys [title author year]}]
  (cond-> []
    (blank? title)  (conj "title is required")
    (blank? author) (conj "author is required")
    (and (some? year) (not (integer? year))) (conj "year must be an integer")))

(defn- ok      [body] {:status 200 :body body})
(defn- created [body] {:status 201 :body body})
(defn- bad-request [errors] {:status 400 :body {:errors errors}})
(defn- not-found []     {:status 404 :body {:error "book not found"}})

(defn health [_]
  (ok {:status "ok"}))

(defn create-book [ds]
  (fn [request]
    (let [body   (:body-params request)
          errors (validate-book body)]
      (if (seq errors)
        (bad-request errors)
        (created (db/create-book! ds body))))))

(defn list-books [ds]
  (fn [request]
    (let [author (get-in request [:query-params "author"])]
      (ok (db/list-books ds author)))))

(defn get-book [ds]
  (fn [request]
    (if-let [id (parse-id (get-in request [:path-params :id]))]
      (if-let [book (db/get-book ds id)]
        (ok book)
        (not-found))
      (not-found))))

(defn update-book [ds]
  (fn [request]
    (if-let [id (parse-id (get-in request [:path-params :id]))]
      (let [body   (:body-params request)
            errors (validate-book body)]
        (cond
          (seq errors)            (bad-request errors)
          :else (if-let [updated (db/update-book! ds id body)]
                  (ok updated)
                  (not-found))))
      (not-found))))

(defn delete-book [ds]
  (fn [request]
    (if-let [id (parse-id (get-in request [:path-params :id]))]
      (if (db/delete-book! ds id)
        {:status 204 :body nil}
        (not-found))
      (not-found))))
