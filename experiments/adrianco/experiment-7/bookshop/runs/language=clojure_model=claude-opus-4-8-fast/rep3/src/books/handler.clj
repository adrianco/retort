(ns books.handler
  "HTTP routing and request handling for the book collection API."
  (:require [books.db :as db]
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
  "Parse a JSON request body into a keyword-keyed map. Returns nil on failure."
  [req]
  (when-let [body (:body req)]
    (try
      (json/parse-string (slurp body) true)
      (catch Exception _ nil))))

(defn- parse-id
  "Parse a path id into a long, or nil if not a valid integer."
  [s]
  (try (Long/parseLong s) (catch Exception _ nil)))

(defn- validate
  "Return a vector of validation error strings for a book payload."
  [{:keys [title author]}]
  (cond-> []
    (not (and (string? title) (seq (.trim ^String title))))
    (conj "title is required")
    (not (and (string? author) (seq (.trim ^String author))))
    (conj "author is required")))

(defn create-book [ds req]
  (let [body (parse-body req)]
    (cond
      (nil? body)
      (json-response 400 {:error "invalid JSON body"})

      (seq (validate body))
      (json-response 400 {:errors (validate body)})

      :else
      (json-response 201 (db/insert-book! ds body)))))

(defn list-books [ds req]
  (let [author (get-in req [:query-params "author"])]
    (json-response 200 (db/list-books ds author))))

(defn get-book [ds id-str]
  (if-let [id (parse-id id-str)]
    (if-let [book (db/get-book ds id)]
      (json-response 200 book)
      (json-response 404 {:error "book not found"}))
    (json-response 400 {:error "invalid id"})))

(defn update-book [ds id-str req]
  (let [id   (parse-id id-str)
        body (parse-body req)]
    (cond
      (nil? id)            (json-response 400 {:error "invalid id"})
      (nil? body)          (json-response 400 {:error "invalid JSON body"})
      (seq (validate body)) (json-response 400 {:errors (validate body)})
      :else
      (if-let [updated (db/update-book! ds id body)]
        (json-response 200 updated)
        (json-response 404 {:error "book not found"})))))

(defn delete-book [ds id-str]
  (if-let [id (parse-id id-str)]
    (if (db/delete-book! ds id)
      {:status 204 :headers {} :body ""}
      (json-response 404 {:error "book not found"}))
    (json-response 400 {:error "invalid id"})))

(defn make-routes
  "Build the Compojure route handler bound to a datasource."
  [ds]
  (defroutes app-routes
    (GET    "/health"      []        (json-response 200 {:status "ok"}))
    (POST   "/books"       req       (create-book ds req))
    (GET    "/books"       req       (list-books ds req))
    (GET    "/books/:id"   [id]      (get-book ds id))
    (PUT    "/books/:id"   [id :as req] (update-book ds id req))
    (DELETE "/books/:id"   [id]      (delete-book ds id))
    (route/not-found (json-response 404 {:error "not found"})))
  app-routes)

(defn make-handler
  "Construct the full Ring handler (routes + middleware) for a datasource."
  [ds]
  (-> (make-routes ds)
      wrap-params))
