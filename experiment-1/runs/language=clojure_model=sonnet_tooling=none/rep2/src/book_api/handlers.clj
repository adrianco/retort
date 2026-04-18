(ns book-api.handlers
  (:require [book-api.db :as db]
            [cheshire.core :as json]))

(defn json-response
  ([status body]
   {:status  status
    :headers {"Content-Type" "application/json"}
    :body    (json/generate-string body)}))

(defn- validate-book [book]
  (cond
    (not (seq (:title book)))  "title is required"
    (not (seq (:author book))) "author is required"
    :else nil))

(defn health-handler [_req]
  (json-response 200 {:status "ok"}))

(defn create-book-handler [req]
  (let [book  (or (:body req) {})
        error (validate-book book)]
    (if error
      (json-response 400 {:error error})
      (json-response 201 (db/create-book! book)))))

(defn list-books-handler [req]
  (let [author (get-in req [:query-params "author"])]
    (json-response 200 (db/get-books author))))

(defn get-book-handler [req]
  (let [id   (try (Integer/parseInt (-> req :params :id)) (catch Exception _ nil))
        book (when id (db/get-book id))]
    (if book
      (json-response 200 book)
      (json-response 404 {:error "Book not found"}))))

(defn update-book-handler [req]
  (let [id    (try (Integer/parseInt (-> req :params :id)) (catch Exception _ nil))
        book  (or (:body req) {})
        error (validate-book book)]
    (cond
      (nil? id) (json-response 404 {:error "Book not found"})
      error     (json-response 400 {:error error})
      :else     (let [updated (db/update-book! id book)]
                  (if updated
                    (json-response 200 updated)
                    (json-response 404 {:error "Book not found"}))))))

(defn delete-book-handler [req]
  (let [id       (try (Integer/parseInt (-> req :params :id)) (catch Exception _ nil))
        existing (when id (db/get-book id))]
    (if existing
      (do (db/delete-book! id)
          {:status 204 :headers {} :body ""})
      (json-response 404 {:error "Book not found"}))))
