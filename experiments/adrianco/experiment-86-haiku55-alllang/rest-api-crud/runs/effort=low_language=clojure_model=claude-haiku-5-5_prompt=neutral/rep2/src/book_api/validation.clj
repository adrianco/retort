(ns book-api.validation
  "Input validation for book payloads."
  (:require [clojure.string :as str]))

(defn- blank-string? [v]
  (or (not (string? v)) (str/blank? v)))

(defn validate-book
  "Validates a book map with keys :title :author :year :isbn.
  Title and author are required non-blank strings; year (if present) must be an
  integer; isbn (if present) must be a string. Returns nil when valid, otherwise
  a map of field keyword to error message."
  [{:keys [title author year isbn]}]
  (let [errors (cond-> {}
                 (blank-string? title) (assoc :title "title is required and must be a non-empty string")
                 (blank-string? author) (assoc :author "author is required and must be a non-empty string")
                 (and (some? year) (not (integer? year))) (assoc :year "year must be an integer")
                 (and (some? isbn) (not (string? isbn))) (assoc :isbn "isbn must be a string"))]
    (when (seq errors) errors)))

(defn normalize-book
  "Trims string fields and keeps only the known book keys. Assumes the book is valid."
  [{:keys [title author year isbn]}]
  {:title (str/trim title)
   :author (str/trim author)
   :year year
   :isbn (some-> isbn str/trim)})
