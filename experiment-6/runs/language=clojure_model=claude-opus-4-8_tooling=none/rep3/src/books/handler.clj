(ns books.handler
  "HTTP routing and request handling for the book collection API."
  (:require [books.db :as db]
            [clojure.string :as str]
            [cheshire.core :as json]
            [compojure.core :refer [defroutes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.middleware.params :refer [wrap-params]]))

(defn- json-response
  "Build a Ring response with a JSON-encoded body."
  [status body]
  {:status  status
   :headers {"Content-Type" "application/json"}
   :body    (json/generate-string body)})

(defn- parse-body
  "Parse a JSON request body into a Clojure map with keyword keys; nil if absent/invalid."
  [request]
  (when-let [body (:body request)]
    (try
      (json/parse-string (slurp body) true)
      (catch Exception _ nil))))

(defn- blank? [s]
  (or (nil? s) (and (string? s) (str/blank? s))))

(defn- validate
  "Return a vector of validation error messages for the given book payload."
  [{:keys [title author]}]
  (cond-> []
    (blank? title)  (conj "title is required")
    (blank? author) (conj "author is required")))

(defn- parse-id [id]
  (try (Long/parseLong id) (catch Exception _ nil)))

(defn create-book [ds request]
  (let [payload (parse-body request)
        errors  (validate payload)]
    (cond
      (nil? payload) (json-response 400 {:error "request body must be valid JSON"})
      (seq errors)   (json-response 400 {:errors errors})
      :else          (json-response 201 (db/create-book! ds payload)))))

(defn list-books [ds request]
  (let [author (get-in request [:query-params "author"])]
    (json-response 200 (db/list-books ds author))))

(defn get-book [ds id]
  (if-let [id (parse-id id)]
    (if-let [book (db/get-book ds id)]
      (json-response 200 book)
      (json-response 404 {:error "book not found"}))
    (json-response 400 {:error "invalid id"})))

(defn update-book [ds id request]
  (let [id      (parse-id id)
        payload (parse-body request)
        errors  (and payload (validate payload))]
    (cond
      (nil? id)      (json-response 400 {:error "invalid id"})
      (nil? payload) (json-response 400 {:error "request body must be valid JSON"})
      (seq errors)   (json-response 400 {:errors errors})
      :else          (if-let [book (db/update-book! ds id payload)]
                       (json-response 200 book)
                       (json-response 404 {:error "book not found"})))))

(defn delete-book [ds id]
  (if-let [id (parse-id id)]
    (if (db/delete-book! ds id)
      {:status 204 :headers {} :body nil}
      (json-response 404 {:error "book not found"}))
    (json-response 400 {:error "invalid id"})))

(defn make-routes
  "Build the route handler bound to the given datasource."
  [ds]
  (defroutes routes
    (GET    "/health"      []           (json-response 200 {:status "ok"}))
    (POST   "/books"       request      (create-book ds request))
    (GET    "/books"       request      (list-books ds request))
    (GET    "/books/:id"   [id]         (get-book ds id))
    (PUT    "/books/:id"   [id :as req] (update-book ds id req))
    (DELETE "/books/:id"   [id]         (delete-book ds id))
    (route/not-found (json-response 404 {:error "not found"}))))

(defn app
  "Build the full Ring application (routes + middleware) for the given datasource."
  [ds]
  (-> (make-routes ds)
      wrap-params))
