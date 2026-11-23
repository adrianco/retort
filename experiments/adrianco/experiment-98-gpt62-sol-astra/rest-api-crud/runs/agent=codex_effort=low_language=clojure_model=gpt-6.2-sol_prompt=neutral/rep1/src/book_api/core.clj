(ns book-api.core
  (:require [book-api.db :as db]
            [cheshire.core :as json]
            [clojure.string :as str]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.params :refer [wrap-params]])
  (:import [java.sql SQLException])
  (:gen-class))

(defn- response [status body]
  {:status status
   :headers {"Content-Type" "application/json; charset=utf-8"}
   :body (json/generate-string body)})

(defn- not-found []
  (response 404 {:error "Not found"}))

(defn- method-not-allowed [allowed]
  (assoc-in (response 405 {:error "Method not allowed"})
            [:headers "Allow"] allowed))

(defn- validation-error [{:strs [title author year isbn] :as book}]
  (cond
    (not (map? book)) "Expected a JSON object"
    (or (not (string? title)) (str/blank? title)) "Title is required"
    (or (not (string? author)) (str/blank? author)) "Author is required"
    (and (some? year)
         (not (and (integer? year) (<= Long/MIN_VALUE year Long/MAX_VALUE))))
    "Year must be an integer"
    (and (some? isbn) (not (string? isbn))) "ISBN must be a string"))

(defn- with-book [request save]
  (let [book (try
               (some-> (:body request) (slurp :encoding "UTF-8") json/parse-string-strict)
               (catch com.fasterxml.jackson.core.JsonProcessingException _
                 ::invalid-json))]
    (if (= ::invalid-json book)
      (response 400 {:error "Malformed JSON"})
      (if-let [error (validation-error book)]
        (response 400 {:error error})
        (save (update-keys (select-keys book ["title" "author" "year" "isbn"])
                           keyword))))))

(defn- collection-route [url {:keys [request-method query-params] :as request}]
  (case request-method
    :get (let [author (get query-params "author")]
           (if (or (nil? author) (string? author))
             (response 200 (db/list-books url author))
             (response 400 {:error "Supply at most one author filter"})))
    :post (with-book request
            (fn [book]
              (let [created (db/create! url book)]
                (assoc-in (response 201 created)
                          [:headers "Location"] (str "/books/" (:id created))))))
    (method-not-allowed "GET, POST")))

(defn- book-route [url id {:keys [request-method] :as request}]
  (case request-method
    :get (if-let [book (db/get-book url id)]
           (response 200 book)
           (not-found))
    :put (with-book request
           (fn [book]
             (if-let [updated (db/update! url id book)]
               (response 200 updated)
               (not-found))))
    :delete (if (db/delete! url id)
              {:status 204 :headers {} :body nil}
              (not-found))
    (method-not-allowed "GET, PUT, DELETE")))

(defn make-app [url]
  (db/init! url)
  (let [handler (wrap-params
                 (fn [{:keys [uri request-method] :as request}]
                   (case uri
                     "/health" (if (= :get request-method)
                                 (response 200 {:status "ok"})
                                 (method-not-allowed "GET"))
                     "/books" (collection-route url request)
                     (if-let [id (some-> (re-matches #"/books/([0-9]+)" uri)
                                         second parse-long)]
                       (book-route url id request)
                       (not-found)))))]
    (fn [request]
      (try
        (handler request)
        (catch SQLException e
          (binding [*out* *err*]
            (println "SQLite error" (.getMessage e)))
          (response 500 {:error "Database error"}))))))

(defn -main [& _]
  (let [port (parse-long (or (System/getenv "PORT") "3000"))
        path (or (System/getenv "BOOK_DB_PATH") "books.sqlite")]
    (jetty/run-jetty (make-app (str "jdbc:sqlite:" path))
                     {:port port :join? true})))
