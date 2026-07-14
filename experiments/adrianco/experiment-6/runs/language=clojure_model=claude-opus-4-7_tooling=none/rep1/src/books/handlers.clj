(ns books.handlers
  (:require [clojure.string :as str]
            [books.db :as db]))

(defn- blank-string? [s]
  (or (not (string? s)) (str/blank? s)))

(defn- valid-book? [{:keys [title author]}]
  (and (not (blank-string? title))
       (not (blank-string? author))))

(defn- parse-id [s]
  (try (Long/parseLong s) (catch Exception _ nil)))

(defn- bad-request [msg]
  {:status 400 :body {:error msg}})

(defn- not-found []
  {:status 404 :body {:error "Book not found"}})

(defn health [_]
  {:status 200 :body {:status "ok"}})

(defn create-book [ds]
  (fn [request]
    (let [body (:body-params request)]
      (if (valid-book? body)
        {:status 201 :body (db/create-book! ds body)}
        (bad-request "title and author are required")))))

(defn list-books [ds]
  (fn [request]
    (let [author (or (get-in request [:query-params "author"])
                     (get-in request [:query-params :author]))]
      {:status 200 :body (db/list-books ds author)})))

(defn get-book [ds]
  (fn [request]
    (if-let [id (parse-id (get-in request [:path-params :id]))]
      (if-let [book (db/get-book ds id)]
        {:status 200 :body book}
        (not-found))
      (bad-request "invalid id"))))

(defn update-book [ds]
  (fn [request]
    (let [id (parse-id (get-in request [:path-params :id]))
          body (:body-params request)]
      (cond
        (nil? id)
        (bad-request "invalid id")
        (not (valid-book? body))
        (bad-request "title and author are required")
        (nil? (db/get-book ds id))
        (not-found)
        :else
        (do (db/update-book! ds id body)
            {:status 200 :body (db/get-book ds id)})))))

(defn delete-book [ds]
  (fn [request]
    (if-let [id (parse-id (get-in request [:path-params :id]))]
      (if (db/delete-book! ds id)
        {:status 204 :body nil}
        (not-found))
      (bad-request "invalid id"))))
