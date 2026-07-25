(ns book-api.handler
  (:require [book-api.db :as db]
            [cheshire.core :as json]
            [ring.middleware.params :as params])
  (:import [java.sql SQLException]))

(defn validate-book [book]
  "Validate book data - title and author are required"
  (let [errors (cond-> []
                   (not (:title book)) (conj "Title is required")
                   (not (:author book)) (conj "Author is required")
                   (and (:title book) (> (count (:title book)) 255)) (conj "Title must be 255 characters or less")
                   (and (:author book) (> (count (:author book)) 255)) (conj "Author must be 255 characters or less")
                   (:isbn book) (conj (when (not (re-matches #"[0-9]{10}|[0-9]{13}" (:isbn book)))
                                         "ISBN must be 10 or 13 digits")))]
    (if (seq errors)
      {:valid? false :errors errors}
      {:valid? true})))

(defn json-response [status data]
  "Create a JSON response with the given status and data"
  {:status status
   :headers {"Content-Type" "application/json"}
   :body (json/generate-string data)})

(defn parse-json-body [body]
  "Parse JSON body string to map"
  (try
    (json/parse-string body true)
    (catch Exception e
      {})))

(defn health-handler [request]
  "Health check endpoint"
  (json-response 200 {:status "healthy"}))

(defn books-list-handler [request]
  "List all books with optional author filter"
  (let [author (get-in request [:query-params :author])]
    (if author
      (let [books (db/get-books-by-author author)]
        (json-response 200 {:books books :count (count books)}))
      (let [books (db/get-all-books)]
        (json-response 200 {:books books :count (count books)})))))

(defn books-create-handler [request]
  "Create a new book"
  (let [body (parse-json-body (:body request))
        validation (validate-book body)]
    (if (:valid? validation)
      (let [result (db/create-book body)]
        (if (:success result)
          (json-response 201 {:message "Book created" :id (:last-insert-id result)})
          (json-response 400 {:error (:error result)})))
      (json-response 400 {:errors (:errors validation)}))))

(defn books-read-handler [request]
  "Get a single book by ID"
  (let [id (get-in request [:route-params :id])
        book (db/get-book-by-id id)]
    (if (seq book)
      (json-response 200 {:book book})
      (json-response 404 {:error "Book not found"}))))

(defn books-update-handler [request]
  "Update a book by ID"
  (let [id (get-in request [:route-params :id])
        body (parse-json-body (:body request))
        validation (validate-book body)]
    (if (:valid? validation)
      (let [result (db/update-book id body)]
        (if (:success result)
          (json-response 200 {:message "Book updated"})
          (json-response 400 {:error (:error result)})))
      (json-response 400 {:errors (:errors validation)}))))

(defn books-delete-handler [request]
  "Delete a book by ID"
  (let [id (get-in request [:route-params :id])]
    (db/delete-book id)
    (json-response 204 {})))

(defn route-request [request]
  "Route the request to the appropriate handler"
  (let [method (:request-method request)
        path (:uri request)]
    (cond
      (and (= :get method) (= path "/health"))
      (health-handler request)

      (and (= :get method) (= path "/books"))
      (books-list-handler request)

      (and (= :post method) (= path "/books"))
      (books-create-handler request)

      (and (= :get method) (re-matches #"/books/\d+" path))
      (books-read-handler request)

      (and (= :put method) (re-matches #"/books/\d+" path))
      (books-update-handler request)

      (and (= :delete method) (re-matches #"/books/\d+" path))
      (books-delete-handler request)

      :else
      (json-response 404 {:error "Not found"}))))

(def handler
  (-> route-request
      params/wrap-params))
