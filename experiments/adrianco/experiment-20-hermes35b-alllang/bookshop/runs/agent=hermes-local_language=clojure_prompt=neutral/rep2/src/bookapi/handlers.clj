(ns bookapi.handlers
  (:require [bookapi.db :as db]
            [ring.util.response :as response]
            [ring.middleware.json :as json]))

(defn- ok [data]
  (-> (response/status 200)
      (response/content-type "application/json")
      (response/body data)))

(defn- created [data]
  (-> (response/status 201)
      (response/content-type "application/json")
      (response/body data)))

(defn- no-content []
  (response/status 204))

(defn- not-found [msg]
  (-> (response/status 404)
      (response/content-type "application/json")
      (response/body {:error msg})))

(defn- bad-request [msg]
  (-> (response/status 400)
      (response/content-type "application/json")
      (response/body {:error msg})))

(defn health [_]
  (ok {:status "ok" :db (if (db/db-connected?) "connected" "disconnected")}))

(defn create-book [request]
  (let [{:keys [title author year isbn] :as params} (get-in request [:body])
        _ (cond
            (or (empty? (str title)) (nil? title))
            (bad-request "title is required")
            (or (empty? (str author)) (nil? author))
            (bad-request "author is required"))]
    (if (= 4 (count (filter #(nil? %) [title author])))
      (let [book (cond-> {:title title :author author}
                   year (assoc :year (Integer/parseInt (str year)))
                   isbn (assoc :isbn isbn))
            result (db/insert-book book)]
        (created result))
      (ok (db/insert-book {:title title :author author})))
    (let [book (cond-> {:title title :author author}
                 year (assoc :year (Integer/parseInt (str year)))
                 isbn (assoc :isbn isbn))
          result (db/insert-book book)]
      (created result))))

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
