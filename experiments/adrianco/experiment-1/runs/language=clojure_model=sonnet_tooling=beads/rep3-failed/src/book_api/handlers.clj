(ns book-api.handlers
  (:require [book-api.db :as db]
            [ring.util.response :as resp]))

(defn health-handler [_req]
  {:status 200
   :body {:status "ok"}})

(defn- validate-book-input [params required?]
  (let [title (:title params)
        author (:author params)]
    (when required?
      (cond
        (or (nil? title) (empty? title))
        "title is required"
        (or (nil? author) (empty? author))
        "author is required"))))

(defn list-books-handler [req]
  (let [author (get-in req [:query-params "author"])
        books (db/list-books author)]
    {:status 200
     :body books}))

(defn create-book-handler [req]
  (let [params (:body-params req)
        error (validate-book-input params true)]
    (if error
      {:status 422
       :body {:error error}}
      (let [book (db/create-book!
                   (:title params)
                   (:author params)
                   (:year params)
                   (:isbn params))]
        {:status 201
         :body book}))))

(defn get-book-handler [req]
  (let [id (Integer/parseInt (get-in req [:path-params :id]))
        book (db/get-book id)]
    (if book
      {:status 200 :body book}
      {:status 404 :body {:error "Book not found"}})))

(defn update-book-handler [req]
  (let [id (Integer/parseInt (get-in req [:path-params :id]))
        existing (db/get-book id)]
    (if (nil? existing)
      {:status 404 :body {:error "Book not found"}}
      (let [params (:body-params req)
            error (validate-book-input params false)]
        (if error
          {:status 422 :body {:error error}}
          (let [updated (db/update-book!
                          id
                          (:title params)
                          (:author params)
                          (:year params)
                          (:isbn params))]
            {:status 200 :body updated}))))))

(defn delete-book-handler [req]
  (let [id (Integer/parseInt (get-in req [:path-params :id]))
        existing (db/get-book id)]
    (if (nil? existing)
      {:status 404 :body {:error "Book not found"}}
      (do
        (db/delete-book! id)
        {:status 204 :body nil}))))
