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

(defn- not-found []
  (json-response 404 {:error "Book not found"}))

(defn- parse-body
  "Parses the request body as a JSON object. Returns ::invalid if it is not one."
  [request]
  (try
    (let [parsed (some-> (:body request) slurp (json/parse-string true))]
      (if (map? parsed) parsed ::invalid))
    (catch Exception _ ::invalid)))

(defn- required-string-error [book field]
  (let [v (get book field)]
    (when-not (and (string? v) (not (str/blank? v)))
      (str (name field) " is required and must be a non-empty string"))))

(defn validate-book
  "Returns a vector of validation error messages, empty when `book` is valid."
  [{:keys [year isbn] :as book}]
  (cond-> []
    (required-string-error book :title) (conj (required-string-error book :title))
    (required-string-error book :author) (conj (required-string-error book :author))
    (not (or (nil? year) (integer? year))) (conj "year must be an integer")
    (not (or (nil? isbn) (string? isbn))) (conj "isbn must be a string")))

(defn- with-valid-book
  "Calls `f` with the parsed book when the request body is valid, else returns a 400."
  [request f]
  (let [body (parse-body request)]
    (if (= ::invalid body)
      (json-response 400 {:error "Request body must be a JSON object"})
      (let [errors (validate-book body)]
        (if (seq errors)
          (json-response 400 {:error "Validation failed" :details errors})
          (f (select-keys body [:title :author :year :isbn])))))))

(defn app-routes [ds]
  (routes
   (GET "/health" [] (json-response 200 {:status "ok"}))
   (GET "/books" [author]
     (json-response 200 (db/list-books ds author)))
   (POST "/books" request
     (with-valid-book request
       #(json-response 201 (db/create-book! ds %))))
   (GET "/books/:id" [id :<< parse-long]
     (if-let [book (db/get-book ds id)]
       (json-response 200 book)
       (not-found)))
   (PUT "/books/:id" [id :<< parse-long :as request]
     (with-valid-book request
       #(if-let [book (db/update-book! ds id %)]
          (json-response 200 book)
          (not-found))))
   (DELETE "/books/:id" [id :<< parse-long]
     (if (db/delete-book! ds id)
       {:status 204 :headers {} :body nil}
       (not-found)))
   (route/not-found (json-response 404 {:error "Not found"}))))

(defn- wrap-errors [handler]
  (fn [request]
    (try
      (handler request)
      (catch Exception e
        (binding [*out* *err*] (println "Unhandled error:" (ex-message e)))
        (json-response 500 {:error "Internal server error"})))))

;; Only the query string is parsed; ring's wrap-params would also consume
;; form-encoded bodies, which here are always expected to be JSON.
(defn- wrap-query-params [handler]
  (fn [request]
    (handler (params/assoc-query-params request "UTF-8"))))

(defn make-app
  "Builds the Ring handler backed by datasource `ds`."
  [ds]
  (-> (app-routes ds) wrap-query-params wrap-errors))

(defn -main [& _]
  (let [port (parse-long (or (System/getenv "PORT") "3000"))
        path (or (System/getenv "DB_PATH") "books.db")
        ds (db/init! (db/datasource path))]
    (println (str "Listening on http://localhost:" port " (db: " path ")"))
    (jetty/run-jetty (make-app ds) {:port port :join? true})))
