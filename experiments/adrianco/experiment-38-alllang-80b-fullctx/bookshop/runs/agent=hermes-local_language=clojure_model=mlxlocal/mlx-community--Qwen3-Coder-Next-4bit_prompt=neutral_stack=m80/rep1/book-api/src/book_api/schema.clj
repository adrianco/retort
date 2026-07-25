(ns book-api.schema
  (:require [schema.core :as s]))

(s/defschema Book
  "A book in the collection"
  {:id s/Int
   :title s/Str
   :author s/Str
   :year s/Int
   :isbn s/Str})

(s/defschema BookParams
  "Parameters for creating/updating a book"
  {:title s/Str
   :author s/Str
   (s/optional-key :year) s/Int
   (s/optional-key :isbn) s/Str})

(defn validate-book-params [params]
  (let [errors (cond-> {}
                  (not (contains? params :title))
                  (assoc :title "Title is required")
                  (not (contains? params :author))
                  (assoc :author "Author is required")
                  (and (contains? params :year)
                       (not (integer? (:year params))))
                  (assoc :year "Year must be an integer")
                  (and (contains? params :isbn)
                       (string? (:isbn params))
                       (empty? (:isbn params)))
                  (assoc :isbn "ISBN cannot be empty"))]
    (if (empty? errors)
      (s/validate BookParams params)
      (throw (ex-info "Validation failed" {:errors errors}))))

(defn validate-book-id [id]
  (if (and (integer? id) (pos? id))
    id
    (throw (ex-info "Invalid book ID" {:error "Book ID must be a positive integer"}))))
