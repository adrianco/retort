(ns books.core
  "REST API for managing a book collection."
  (:require [books.db :as db]
            [cheshire.core :as json]
            [clojure.string :as str]
            [compojure.core :refer [routes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.params :refer [assoc-query-params]])
  (:gen-class))

(defn- respond
  ([status] {:status status :headers {} :body ""})
  ([status body]
   {:status status
    :headers {"Content-Type" "application/json; charset=utf-8"}
    :body (json/generate-string body)}))

(defn- error [status message & [details]]
  (respond status (cond-> {:error message} details (assoc :details details))))

(defn- parse-id [s]
  (when (re-matches #"\d{1,18}" s) (parse-long s)))

(defn- parse-body
  "Returns the request's JSON body as a map, or ::invalid if it is not a JSON object."
  [request]
  (try
    (let [body (some-> (:body request) slurp (json/parse-string true))]
      (if (map? body) body ::invalid))
    (catch Exception _ ::invalid)))

(defn validate
  "Returns a map of field -> error message; empty when the book is valid."
  [{:keys [title author year isbn]}]
  (cond-> {}
    (not (and (string? title) (not (str/blank? title))))
    (assoc :title "title is required and must be a non-empty string")

    (not (and (string? author) (not (str/blank? author))))
    (assoc :author "author is required and must be a non-empty string")

    (not (or (nil? year) (integer? year)))
    (assoc :year "year must be an integer")

    (not (or (nil? isbn) (string? isbn)))
    (assoc :isbn "isbn must be a string")))

(defn- with-valid-book
  "Calls `f` with the validated book from the request body, or returns a 400."
  [request f]
  (let [body (parse-body request)]
    (if (= ::invalid body)
      (error 400 "Request body must be a JSON object")
      (let [errors (validate body)]
        (if (seq errors)
          (error 400 "Validation failed" errors)
          (f (-> (select-keys body [:title :author :year :isbn])
                 (update :title str/trim)
                 (update :author str/trim))))))))

(defn- with-id
  "Calls `f` with the numeric id, or returns a 404 when the id is malformed."
  [id f]
  (if-let [id (parse-id id)]
    (f id)
    (error 404 "Book not found")))

(defn- wrap-errors [handler]
  (fn [request]
    (try
      (handler request)
      (catch Exception e
        (binding [*out* *err*] (println "Unhandled error:" (ex-message e)))
        (error 500 "Internal server error")))))

(defn- wrap-query-params
  "Parses the query string only, leaving the body unread whatever its content type."
  [handler]
  (fn [request]
    (handler (assoc-query-params request "UTF-8"))))

(defn app
  "Builds the Ring handler backed by datasource `ds`."
  [ds]
  (-> (routes
       (GET "/health" [] (respond 200 {:status "ok"}))

       (GET "/books" request
         (let [author (get-in request [:query-params "author"])]
           (respond 200 (db/list-books ds (when-not (str/blank? author) author)))))

       (POST "/books" request
         (with-valid-book request
           #(respond 201 (db/create-book! ds %))))

       (GET "/books/:id" [id]
         (with-id id
           #(if-let [book (db/get-book ds %)]
              (respond 200 book)
              (error 404 "Book not found"))))

       (PUT "/books/:id" [id :as request]
         (with-id id
           (fn [id]
             (with-valid-book request
               #(if-let [book (db/update-book! ds id %)]
                  (respond 200 book)
                  (error 404 "Book not found"))))))

       (DELETE "/books/:id" [id]
         (with-id id
           #(if (db/delete-book! ds %)
              (respond 204)
              (error 404 "Book not found"))))

       (route/not-found (error 404 "Not found")))
      wrap-query-params
      wrap-errors))

(defn -main [& _]
  (let [port (parse-long (or (System/getenv "PORT") "3000"))
        path (or (System/getenv "DB_PATH") "books.db")
        ds   (db/init! (db/datasource path))]
    (println (str "Books API listening on http://localhost:" port " (db: " path ")"))
    (jetty/run-jetty (app ds) {:port port :join? true})))
