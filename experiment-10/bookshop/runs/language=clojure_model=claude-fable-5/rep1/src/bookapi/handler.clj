(ns bookapi.handler
  "Ring handler and routes for the book collection API."
  (:require [clojure.string :as str]
            [compojure.core :refer [routes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [ring.middleware.params :refer [wrap-params]]
            [bookapi.db :as db]))

(defn- json-response
  ([status body] {:status status
                  :headers {}
                  :body body}))

(defn- parse-id [s]
  (try
    (Long/parseLong s)
    (catch NumberFormatException _ nil)))

(defn- validate-book
  "Return a vector of validation error messages for a book payload."
  [body]
  (cond-> []
    (not (map? body))
    (conj "request body must be a JSON object")

    (and (map? body)
         (not (and (string? (:title body)) (not (str/blank? (:title body))))))
    (conj "title is required and must be a non-empty string")

    (and (map? body)
         (not (and (string? (:author body)) (not (str/blank? (:author body))))))
    (conj "author is required and must be a non-empty string")

    (and (map? body)
         (some? (:year body))
         (not (integer? (:year body))))
    (conj "year must be an integer")

    (and (map? body)
         (some? (:isbn body))
         (not (string? (:isbn body))))
    (conj "isbn must be a string")))

(defn- book-params [body]
  (select-keys body [:title :author :year :isbn]))

(defn- create-book [ds body]
  (let [errors (validate-book body)]
    (if (seq errors)
      (json-response 400 {:errors errors})
      (json-response 201 (db/create-book! ds (book-params body))))))

(defn- list-books [ds query-params]
  (json-response 200 (db/list-books ds {:author (get query-params "author")})))

(defn- get-book [ds id-str]
  (if-let [book (some->> (parse-id id-str) (db/get-book ds))]
    (json-response 200 book)
    (json-response 404 {:error "book not found"})))

(defn- update-book [ds id-str body]
  (let [errors (validate-book body)]
    (cond
      (seq errors)
      (json-response 400 {:errors errors})

      :else
      (if-let [book (some->> (parse-id id-str)
                             (#(db/update-book! ds % (book-params body))))]
        (json-response 200 book)
        (json-response 404 {:error "book not found"})))))

(defn- delete-book [ds id-str]
  (if (some->> (parse-id id-str) (db/delete-book! ds))
    {:status 204 :headers {} :body nil}
    (json-response 404 {:error "book not found"})))

(defn app
  "Build the Ring handler over the given datasource."
  [ds]
  (-> (routes
        (GET "/health" [] (json-response 200 {:status "ok"}))
        (POST "/books" {body :body} (create-book ds body))
        (GET "/books" {query-params :query-params} (list-books ds query-params))
        (GET "/books/:id" [id] (get-book ds id))
        (PUT "/books/:id" {body :body {:keys [id]} :params} (update-book ds id body))
        (DELETE "/books/:id" [id] (delete-book ds id))
        (route/not-found (json-response 404 {:error "not found"})))
      (wrap-json-body {:keywords? true})
      wrap-params
      wrap-json-response))
