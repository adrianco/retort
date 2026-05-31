(ns books.handler
  (:require [compojure.core :refer [defroutes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [ring.middleware.params :refer [wrap-params]]
            [ring.util.response :as resp]
            [books.db :as db]))

(defn- json-response
  ([status body]
   (-> (resp/response body)
       (resp/status status)
       (resp/header "Content-Type" "application/json"))))

(defn- parse-id [s]
  (try (Long/parseLong s) (catch Exception _ nil)))

(defn- validate-book [{:keys [title author year]}]
  (cond
    (or (nil? title) (and (string? title) (clojure.string/blank? title)))
    "title is required"

    (or (nil? author) (and (string? author) (clojure.string/blank? author)))
    "author is required"

    (and (some? year) (not (integer? year)))
    "year must be an integer"

    :else nil))

(defn create-book-handler [ds]
  (fn [req]
    (let [body (:body req)
          err (validate-book body)]
      (if err
        (json-response 400 {:error err})
        (let [book (db/create-book ds body)]
          (json-response 201 book))))))

(defn list-books-handler [ds]
  (fn [req]
    (let [author (get-in req [:query-params "author"])
          books (db/list-books ds author)]
      (json-response 200 books))))

(defn get-book-handler [ds]
  (fn [req]
    (let [id (parse-id (get-in req [:params :id]))]
      (if-let [book (and id (db/get-book ds id))]
        (json-response 200 book)
        (json-response 404 {:error "Book not found"})))))

(defn update-book-handler [ds]
  (fn [req]
    (let [id (parse-id (get-in req [:params :id]))
          body (:body req)
          err (validate-book body)]
      (cond
        (nil? id) (json-response 404 {:error "Book not found"})
        err (json-response 400 {:error err})
        :else
        (if-let [book (db/update-book ds id body)]
          (json-response 200 book)
          (json-response 404 {:error "Book not found"}))))))

(defn delete-book-handler [ds]
  (fn [req]
    (let [id (parse-id (get-in req [:params :id]))]
      (if (and id (db/delete-book ds id))
        (json-response 204 nil)
        (json-response 404 {:error "Book not found"})))))

(defn health-handler [_req]
  (json-response 200 {:status "ok"}))

(defn make-app [ds]
  (let [routes (compojure.core/routes
                (GET "/health" [] health-handler)
                (POST "/books" [] (create-book-handler ds))
                (GET "/books" [] (list-books-handler ds))
                (GET "/books/:id" [] (get-book-handler ds))
                (PUT "/books/:id" [] (update-book-handler ds))
                (DELETE "/books/:id" [] (delete-book-handler ds))
                (route/not-found {:error "Not found"}))]
    (-> routes
        (wrap-json-body {:keywords? true})
        wrap-json-response
        wrap-params)))
