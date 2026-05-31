(ns books.handlers
  "Ring handlers for the book collection API."
  (:require [books.db :as db]
            [books.validation :as validation]))

(defn- parse-id [s]
  (try (Long/parseLong s) (catch Exception _ nil)))

(defn health [_]
  {:status 200 :body {:status "ok"}})

(defn create-book [ds]
  (fn [request]
    (let [body (:body-params request)
          errors (validation/validate-book body)]
      (if (seq errors)
        {:status 400 :body {:errors errors}}
        {:status 201 :body (db/create-book! ds body)}))))

(defn list-books [ds]
  (fn [request]
    (let [author (get-in request [:query-params "author"])]
      {:status 200 :body (db/list-books ds author)})))

(defn get-book [ds]
  (fn [request]
    (let [id (parse-id (get-in request [:path-params :id]))]
      (if-let [book (and id (db/get-book ds id))]
        {:status 200 :body book}
        {:status 404 :body {:error "book not found"}}))))

(defn update-book [ds]
  (fn [request]
    (let [id (parse-id (get-in request [:path-params :id]))
          body (:body-params request)
          errors (validation/validate-book body)]
      (cond
        (nil? id) {:status 404 :body {:error "book not found"}}
        (seq errors) {:status 400 :body {:errors errors}}
        :else (if-let [book (db/update-book! ds id body)]
                {:status 200 :body book}
                {:status 404 :body {:error "book not found"}})))))

(defn delete-book [ds]
  (fn [request]
    (let [id (parse-id (get-in request [:path-params :id]))]
      (if (and id (db/delete-book! ds id))
        {:status 204 :body nil}
        {:status 404 :body {:error "book not found"}}))))
