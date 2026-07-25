(ns book-api.routes
  (:require [compojure.core :refer [defroutes GET POST PUT DELETE]]
            [compojure.route :as route]
            [book-api.db :as db]
            [cheshire.core :as json]))

(defn parse-string [s]
  (Integer/parseInt s))

(defn validate-book [data]
  (let [errors (cond-> []
                   (not (:title data)) (conj "Title is required")
                   (not (:author data)) (conj "Author is required"))
        valid? (empty? errors)]
    {:valid? valid? :errors errors}))

(defn book->response [book]
  {:id       (:id book)
   :title    (:title book)
   :author   (:author book)
   :year     (:year book)
   :isbn     (:isbn book)})

(defn books->response [books]
  (map book->response books))

(defn parse-body [request]
  (let [body (:body request)]
    (if (seq body)
      (json/parse-stream body true)
      {})))

(defn json-response [status data]
  {:status status
   :headers {"Content-Type" "application/json"}
   :body (json/generate-string data)})

(defroutes app-routes
  (GET "/health" []
    (json-response 200 {:status "healthy"}))

  (POST "/books" request
    (let [data (parse-body request)
          {:keys [valid? errors]} (validate-book data)]
      (if valid?
        (let [book (db/create-book data)
              book-response (book->response book)]
          (json-response 201 book-response))
        (json-response 400 {:errors errors}))))

  (GET "/books" request
    (let [author (get-in request [:query-params :author])]
      (if author
        (let [books (db/get-books-by-author author)]
          (json-response 200 (books->response books)))
        (let [books (db/get-all-books)]
          (json-response 200 (books->response books))))))

  (GET "/books/:id" [id]
    (let [book (db/get-book-by-id (parse-string id))]
      (if book
        (json-response 200 (book->response book))
        (json-response 404 {:error "Book not found"}))))

  (PUT "/books/:id" request
    (let [id (parse-string (get-in request [:route-params :id]))
          data (parse-body request)
          book (db/get-book-by-id id)]
      (if book
        (let [updated (db/update-book id data)
              book-response (book->response updated)]
          (json-response 200 book-response))
        (json-response 404 {:error "Book not found"}))))

  (DELETE "/books/:id" [id]
    (let [book (db/get-book-by-id (parse-string id))]
      (if book
        (do (db/delete-book (parse-string id))
            {:status 204 :headers {} :body ""})
        (json-response 404 {:error "Book not found"}))))

  (route/not-found "Not Found"))
