(ns books.core
  (:require [books.db :as db]
            [cheshire.core :as json]
            [clojure.string :as str]
            [compojure.core :refer [routes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.params :as params])
  (:gen-class))

(defn- json-response [status body]
  {:status status
   :headers {"Content-Type" "application/json; charset=utf-8"}
   :body (json/generate-string body)})

(defn- error [status msg & [details]]
  (json-response status (cond-> {:error msg} details (assoc :details details))))

(defn- parse-id [s]
  (when (and s (re-matches #"\d{1,18}" s)) (parse-long s)))

(defn- read-body
  "Parses the request body as a JSON object. Returns ::invalid when the body
  is not a JSON object."
  [req]
  (try
    (let [raw (some-> (:body req) slurp)
          v (when-not (str/blank? raw) (json/parse-string raw true))]
      (if (map? v) v ::invalid))
    (catch Exception _ ::invalid)))

(defn validate
  "Returns a seq of error messages for a book payload, or nil when valid."
  [{:keys [title author year isbn]}]
  (seq
   (cond-> []
     (not (and (string? title) (not (str/blank? title))))
     (conj "title is required and must be a non-empty string")
     (not (and (string? author) (not (str/blank? author))))
     (conj "author is required and must be a non-empty string")
     (not (or (nil? year) (integer? year)))
     (conj "year must be an integer")
     (not (or (nil? isbn) (string? isbn)))
     (conj "isbn must be a string"))))

(defn- with-book-body
  "Calls (f book) with the validated payload, or returns a 400 response."
  [req f]
  (let [body (read-body req)]
    (if (= body ::invalid)
      (error 400 "Request body must be a JSON object")
      (if-let [errs (validate body)]
        (error 400 "Validation failed" errs)
        (f (-> (select-keys body [:title :author :year :isbn])
               (update :title str/trim)
               (update :author str/trim)))))))

(def ^:private not-found (error 404 "Book not found"))

(defn app
  "Builds the ring handler backed by datasource `ds`."
  [ds]
  ;; Query params are parsed per-route rather than with wrap-params, which
  ;; would consume form-encoded request bodies (curl -d's default type).
  (routes
       (GET "/health" [] (json-response 200 {:status "ok"}))
       (GET "/books" req
         (let [author (get-in (params/assoc-query-params req "UTF-8")
                              [:query-params "author"])]
           (json-response 200 (db/list-books ds (when-not (str/blank? author) author)))))
       (POST "/books" req
         (with-book-body req #(json-response 201 (db/create-book! ds %))))
       (GET "/books/:id" [id]
         (if-let [book (some->> (parse-id id) (db/get-book ds))]
           (json-response 200 book)
           not-found))
       (PUT "/books/:id" [id :as req]
         (if-let [id (parse-id id)]
           (with-book-body req
             #(if-let [book (db/update-book! ds id %)]
                (json-response 200 book)
                not-found))
           not-found))
       (DELETE "/books/:id" [id]
         (if (some->> (parse-id id) (db/delete-book! ds))
           {:status 204 :headers {} :body nil}
           not-found))
       (route/not-found (error 404 "Not found"))))

(defn -main [& _]
  (let [port (parse-long (or (System/getenv "PORT") "3000"))
        path (or (System/getenv "DB_PATH") "books.db")
        ds (db/init! (db/datasource path))]
    (println (str "Listening on http://localhost:" port " (db: " path ")"))
    (jetty/run-jetty (app ds) {:port port :join? true})))
