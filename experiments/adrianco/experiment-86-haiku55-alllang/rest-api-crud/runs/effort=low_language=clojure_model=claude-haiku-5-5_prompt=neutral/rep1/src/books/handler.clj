(ns books.handler
  (:require [cheshire.core :as json]
            [clojure.string :as str]
            [ring.middleware.params :refer [wrap-params]]
            [books.db :as db]))

(defn- respond
  ([status]
   {:status status :headers {}  :body nil})
  ([status body]
   {:status status
    :headers {"Content-Type" "application/json; charset=utf-8"}
    :body (json/generate-string body)}))

(defn- error [status msg]
  (respond status {:error msg}))

(defn- not-found [] (error 404 "book not found"))

(defn- method-not-allowed [] (error 405 "method not allowed"))

(defn- non-blank? [s]
  (and (string? s) (not (str/blank? s))))

(defn- parse-body
  "Parses the request body as a JSON object. Returns the map, or nil if the body is not a JSON object."
  [req]
  (try
    (let [parsed (json/parse-string (if-let [b (:body req)] (slurp b) "") true)]
      (when (map? parsed) parsed))
    (catch Exception _ nil)))

(defn validation-errors
  "Returns a vector of human-readable validation errors for a book map (empty when valid)."
  [{:keys [title author year isbn]}]
  (cond-> []
    (not (non-blank? title))  (conj "title is required")
    (not (non-blank? author)) (conj "author is required")
    (and (some? year) (not (integer? year))) (conj "year must be an integer")
    (and (some? isbn) (not (string? isbn)))  (conj "isbn must be a string")))

(defn- book-fields [m]
  (select-keys m [:title :author :year :isbn]))

(defn- with-valid-book
  "Parses and validates the JSON body, then calls (f book). Responds 400/422 on failure."
  [req f]
  (if-let [m (parse-body req)]
    (let [book (book-fields m)
          errs (validation-errors book)]
      (if (empty? errs)
        (f book)
        (respond 422 {:error "validation failed" :details errs})))
    (error 400 "request body must be a JSON object")))

(defn- book-id
  "Extracts the numeric id from /books/{id}, or nil."
  [uri]
  (when-let [[_ id] (re-matches #"/books/(\d+)" uri)]
    (parse-long id)))

(defn- handle [ds {:keys [request-method uri] :as req}]
  (let [id (book-id uri)]
    (cond
      (= uri "/health")
      (if (= request-method :get)
        (respond 200 {:status "ok"})
        (method-not-allowed))

      (= uri "/books")
      (case request-method
        :get  (let [author (get-in req [:query-params "author"])]
                (respond 200 (if (some? author)
                               (db/list-books ds author)
                               (db/list-books ds))))
        :post (with-valid-book req
                (fn [book]
                  (respond 201 (db/create-book! ds book))))
        (method-not-allowed))

      id
      (case request-method
        :get    (if-let [book (db/get-book ds id)]
                  (respond 200 book)
                  (not-found))
        :put    (with-valid-book req
                  (fn [book]
                    (if-let [updated (db/update-book! ds id book)]
                      (respond 200 updated)
                      (not-found))))
        :delete (if (db/delete-book! ds id)
                  (respond 204)
                  (not-found))
        (method-not-allowed))

      :else (error 404 "not found"))))

(defn app
  "Builds the Ring handler backed by the given datasource."
  [ds]
  (-> (fn [req]
        (try
          (handle ds req)
          (catch Exception e
            (binding [*out* *err*]
              (println "unhandled error:" (.getMessage e)))
            (error 500 "internal server error"))))
      wrap-params))
