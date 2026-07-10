(ns book-api.routes
  (:require [compojure.core :refer [defroutes GET POST PUT DELETE]]
            [ring.middleware.defaults :refer [wrap-defaults api-defaults]]
            [ring.middleware.params :as ring-params]
            [ring.middleware.json :as ring-json]
            [book-api.db :as db]
            [cheshire.core :as cheshire]))

(defn book->map [book]
  "Convert a JDBC row map to a clean map for JSON serialization."
  {:id (long (:id book))
   :title (:title book)
   :author (:author book)
   :year (when-let [y (:year book)] (long y))
   :isbn (:isbn book)})

(defn book-response [book]
  {:status 200
   :headers {"Content-Type" "application/json"}
   :body (cheshire/generate-string (book->map book))})

(defn created-response [book]
  {:status 201
   :headers {"Content-Type" "application/json"}
   :body (cheshire/generate-string (book->map book))})

(defn error-response [msg status]
  {:status status
   :headers {"Content-Type" "application/json"}
   :body (cheshire/generate-string {:error msg})})

(defn success-response [msg]
  {:status 200
   :headers {"Content-Type" "application/json"}
   :body (cheshire/generate-string {:message msg})})

(defn books-response [books]
  {:status 200
   :headers {"Content-Type" "application/json"}
   :body (cheshire/generate-string (map book->map books))})

(defn validate-book [params]
  "Validate required fields. Returns [has-error? response]."
  (cond
    (or (nil? (:title params)) ("" = (:title params)))
      [true (error-response "title is required" 400)]
    (or (nil? (:author params)) ("" = (:author params)))
      [true (error-response "author is required" 400)]
    :else [nil nil]))

(defn strip-empty [m]
  "Remove keys whose value is nil or empty string."
  (select-keys m (keep (fn [[k v]]
                         (when (not (or (nil? v) (= v "")))) k)
                       m)))

(defn extract-id [request]
  "Extract the :id route param and parse it as integer."
  (try
    (Integer/parseInt (get-in request [:route-params :id]))
    (catch Exception _
      nil)))

(defroutes api-routes
  (POST "/books" [request]
    (let [params (:json request)
          [err resp] (validate-book params)]
      (if err
        resp
        (let [clean-params (strip-empty params)
              book (db/insert-book
                     (:title clean-params)
                     (:author clean-params)
                     (:year clean-params)
                     (:isbn clean-params))]
          (created-response book)))))

  (GET "/books" [request]
    (let [params (:params request)
          author (when-let [a (:author params)]
                   (if (= a "") nil a))]
      (books-response (db/get-books author))))

  (GET "/books/:id" [request]
    (if-let [id (extract-id request)]
      (let [book (db/get-book-by-id id)]
        (if book
          (book-response book)
          (error-response "Book not found" 404)))
      (error-response "Invalid book ID" 400)))

  (PUT "/books/:id" [request]
    (if-let [id (extract-id request)]
      (let [params (:json request)
            book (db/update-book! id params)]
        (if book
          (book-response book)
          (error-response "Book not found" 404)))
      (error-response "Invalid book ID" 400)))

  (DELETE "/books/:id" [request]
    (if-let [id (extract-id request)]
      (if (db/delete-book! id)
        (success-response "Book deleted successfully")
        (error-response "Book not found" 404))
      (error-response "Invalid book ID" 400)))

  (GET "/health" []
    (success-response "ok")))

(def routes
  (-> api-routes
      (ring-params/wrap-params)
      (ring-json/wrap-json-body)
      (wrap-defaults api-defaults)))
