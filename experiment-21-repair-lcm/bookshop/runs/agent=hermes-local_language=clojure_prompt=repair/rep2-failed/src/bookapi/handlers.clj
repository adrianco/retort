(ns bookapi.handlers
  (:require [bookapi.db :as db]))

(defn- make-response [status body]
  {:status status
   :headers {"Content-Type" "application/json"}
   :body body})

(defn- ok [data]
  (make-response 200 data))

(defn- created [data]
  (make-response 201 data))

(defn- no-content []
  (make-response 204 nil))

(defn- not-found [msg]
  (make-response 404 {:error msg}))

(defn- bad-request [msg]
  (make-response 400 {:error msg}))

(defn health []
  (ok {:status "ok" :db (if (db/db-connected?) "connected" "disconnected")}))

(defn create-book [request]
  (let [{:keys [title author year isbn] :as params} (get-in request [:body])]
    (if (or (nil? title) (empty? (str title)))
      (bad-request "title is required")
      (if (or (nil? author) (empty? (str author)))
        (bad-request "author is required")
        (let [book (cond-> {:title title :author author}
                     year (assoc :year (Integer/parseInt (str year)))
                     isbn (assoc :isbn isbn))
              result (db/insert-book book)]
          (created result))))))

(defn list-books [request]
  (let [author (:author (get-in request [:query-params]))]
    (if author
      (ok (db/get-book-by-author author))
      (ok (db/get-all-books)))))

(defn get-book [request]
  (let [id (Integer/parseInt (:id (:route-params request)))]
    (if-let [book (db/get-book-by-id id)]
      (ok book)
      (not-found (str "Book with id " id " not found")))))

(defn update-book [request]
  (let [id (Integer/parseInt (:id (:route-params request)))
        book-data (get-in request [:body])
        existing (db/get-book-by-id id)]
    (if (nil? existing)
      (not-found (str "Book with id " id " not found"))
      (let [result (db/update-book id book-data)]
        (ok result)))))

(defn delete-book [request]
  (let [id (Integer/parseInt (:id (:route-params request)))
        existing (db/get-book-by-id id)]
    (if (nil? existing)
      (not-found (str "Book with id " id " not found"))
      (do
        (db/delete-book id)
        (no-content)))))
