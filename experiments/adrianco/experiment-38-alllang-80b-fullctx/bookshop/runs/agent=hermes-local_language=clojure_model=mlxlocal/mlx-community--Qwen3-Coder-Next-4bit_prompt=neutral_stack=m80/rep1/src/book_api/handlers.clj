(ns book-api.handlers
  (:require [compojure.api.sweet :as api]
            [ring.util.http-response :as response]
            [ring.util.http-status :as status]
            [cheshire.core :as json]
            [book-api.db :as db]
            [book-api.schema :as schema]))

(defn health-handler [_]
  {:status 200
   :body {:status "ok"
          :service "book-api"}})

(defn create-book-handler [params]
  (try
    (schema/validate-book-params params)
    (let [book (db/create-book params)]
      (response/created book))
    (catch clojure.lang.ExceptionInfo e
      (let [{:keys [errors]} (ex-data e)]
        (response/bad-request {:errors errors})))
    (catch Exception e
      (response/internal-server-error {:error (.getMessage e)}))))

(defn list-books-handler [query-params]
  (try
    (let [books (db/get-books query-params)]
      (response/ok books))
    (catch Exception e
      (response/internal-server-error {:error (.getMessage e)}))))

(defn get-book-handler [id]
  (try
    (schema/validate-book-id id)
    (let [book (db/get-book id)]
      (if book
        (response/ok book)
        (response/not-found {:error "Book not found"})))
    (catch clojure.lang.ExceptionInfo e
      (response/bad-request {:errors {:id (.getMessage e)}}))
    (catch Exception e
      (response/internal-server-error {:error (.getMessage e)}))))

(defn update-book-handler [id params]
  (try
    (schema/validate-book-id id)
    (schema/validate-book-params params)
    (let [existing (db/get-book id)]
      (if existing
        (let [book (db/update-book id params)]
          (response/ok book))
        (response/not-found {:error "Book not found"})))
    (catch clojure.lang.ExceptionInfo e
      (let [{:keys [errors]} (ex-data e)]
        (response/bad-request {:errors errors})))
    (catch Exception e
      (response/internal-server-error {:error (.getMessage e)}))))

(defn delete-book-handler [id]
  (try
    (schema/validate-book-id id)
    (let [existing (db/get-book id)]
      (if existing
        (do
          (db/delete-book id)
          (response/no-content))
        (response/not-found {:error "Book not found"})))
    (catch clojure.lang.ExceptionInfo e
      (response/bad-request {:errors {:id (.getMessage e)}}))
    (catch Exception e
      (response/internal-server-error {:error (.getMessage e)}))))

(defn not-found-handler [req]
  (response/not-found {:error "Endpoint not found"}))
