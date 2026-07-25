(ns book-api.handler
  "Routes and request handlers for the book collection API."
  (:require [book-api.db :as db]
            [book-api.middleware :as mw]
            [book-api.validation :as v]
            [clojure.string :as str]
            [compojure.core :refer [ANY DELETE GET POST PUT routes]]
            [ring.middleware.params :refer [wrap-params]]))

;; ---------------------------------------------------------------------------
;; Response helpers

(defn- respond [status body] {:status status :headers {} :body body})

(def ^:private not-found
  (respond 404 {:error "Book not found"}))

(defn- invalid [errors]
  (respond 400 {:error "Validation failed" :details errors}))

(defn- conflict [isbn]
  (respond 409 {:error (str "A book with isbn " isbn " already exists")}))

;; ---------------------------------------------------------------------------
;; Handlers

(defn- create-book [ds request]
  (let [{:keys [book errors]} (v/validate-book (:json-body request))]
    (cond
      errors                        (invalid errors)
      (db/isbn-owner ds (:isbn book)) (conflict (:isbn book))
      :else
      (let [created (db/insert-book! ds book)]
        (-> (respond 201 created)
            (assoc-in [:headers "Location"] (str "/books/" (:id created))))))))

(defn- list-books [ds request]
  (let [author (some-> (get-in request [:query-params "author"]) str/trim not-empty)]
    (respond 200 (db/list-books ds {:author author}))))

(defn- get-book [ds id-str]
  (if-let [id (v/parse-id id-str)]
    (if-let [book (db/find-book ds id)]
      (respond 200 book)
      not-found)
    not-found))

(defn- update-book [ds id-str request]
  (if-let [id (v/parse-id id-str)]
    (let [{:keys [book errors]} (v/validate-book (:json-body request))]
      (cond
        errors (invalid errors)

        ;; The isbn may stay on this book, but must not be taken by another.
        (when-let [owner (db/isbn-owner ds (:isbn book))] (not= owner id))
        (conflict (:isbn book))

        :else (if-let [updated (db/update-book! ds id book)]
                (respond 200 updated)
                not-found)))
    not-found))

(defn- delete-book [ds id-str]
  (let [id (v/parse-id id-str)]
    (if (and id (db/delete-book! ds id))
      {:status 204 :headers {} :body nil}
      not-found)))

(defn- health [ds]
  (let [ok? (try (db/ping ds) (catch Exception _ false))]
    (respond (if ok? 200 503)
             {:status   (if ok? "ok" "degraded")
              :database (if ok? "up" "down")})))

;; ---------------------------------------------------------------------------
;; Routing

(defn app-routes [ds]
  (routes
   (GET    "/health"     []                (health ds))
   (POST   "/books"      request           (create-book ds request))
   (GET    "/books"      request           (list-books ds request))
   (GET    "/books/:id"  [id]              (get-book ds id))
   (PUT    "/books/:id"  [id :as request]  (update-book ds id request))
   (DELETE "/books/:id"  [id]              (delete-book ds id))
   (ANY    "*"           []                (respond 404 {:error "Not found"}))))

(defn app
  "Build the fully wrapped Ring handler for datasource `ds`."
  [ds]
  (-> (app-routes ds)
      wrap-params
      mw/wrap-json-body
      mw/wrap-json-response
      mw/wrap-errors))
