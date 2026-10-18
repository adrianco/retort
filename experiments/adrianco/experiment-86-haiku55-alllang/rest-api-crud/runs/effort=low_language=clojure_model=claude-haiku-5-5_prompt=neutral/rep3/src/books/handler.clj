(ns books.handler
  (:require [books.db :as db]
            [clojure.string :as str]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [ring.middleware.params :refer [wrap-params]]))

(defn- blank? [s]
  (or (nil? s) (and (string? s) (str/blank? s))))

(defn validate
  "Returns a map of field -> error message for an invalid book payload, or nil if valid."
  [{:keys [title author year isbn] :as book}]
  (let [errors (cond-> {}
                 (not (string? title)) (assoc :title "title is required")
                 (and (string? title) (blank? title)) (assoc :title "title must not be blank")
                 (not (string? author)) (assoc :author "author is required")
                 (and (string? author) (blank? author)) (assoc :author "author must not be blank")
                 (and (some? year) (not (integer? year))) (assoc :year "year must be an integer")
                 (and (some? isbn) (not (string? isbn))) (assoc :isbn "isbn must be a string"))]
    (when (seq errors) errors)))

(defn- ok [body] {:status 200 :body body})
(defn- created [body] {:status 201 :body body})
(defn- bad-request [errors] {:status 400 :body {:error "validation failed" :details errors}})
(defn- not-found [] {:status 404 :body {:error "not found"}})

(defn- book-body
  "Keeps only the book fields the API exposes from a request body."
  [body]
  (select-keys body [:title :author :year :isbn]))

(defn- parse-id [s]
  (when (and s (re-matches #"\d+" s))
    (parse-long s)))

(defn- create [ds req]
  (let [book (book-body (:body req))]
    (if-let [errors (validate book)]
      (bad-request errors)
      (created (db/create-book! ds book)))))

(defn- list-all [ds req]
  (ok (db/list-books ds (get-in req [:query-params "author"]))))

(defn- get-one [ds id]
  (if-let [book (db/get-book ds id)]
    (ok book)
    (not-found)))

(defn- update-one [ds id req]
  (let [book (book-body (:body req))]
    (if-let [errors (validate book)]
      (bad-request errors)
      (if-let [updated (db/update-book! ds id book)]
        (ok updated)
        (not-found)))))

(defn- delete-one [ds id]
  (if (db/delete-book! ds id)
    {:status 204 :body nil}
    (not-found)))

(defn routes
  "Builds the raw Ring handler (no JSON/param middleware) over the datasource."
  [ds]
  (fn [{:keys [request-method uri] :as req}]
    (let [[_ id-str] (re-matches #"/books/([^/]+)" uri)
          id (parse-id id-str)]
      (cond
        (and (= uri "/health") (= request-method :get))
        (ok {:status "ok"})

        (= uri "/books")
        (case request-method
          :get (list-all ds req)
          :post (create ds req)
          (not-found))

        (and id-str (nil? id)) (not-found)

        id
        (case request-method
          :get (get-one ds id)
          :put (update-one ds id req)
          :delete (delete-one ds id)
          (not-found))

        :else (not-found)))))

(defn app
  "Full application handler: JSON request/response handling and query-param parsing."
  [ds]
  (-> (routes ds)
      (wrap-json-body {:keywords? true :malformed-response {:status 400 :body {:error "malformed JSON body"}}})
      wrap-json-response
      wrap-params))
