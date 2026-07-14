(ns books.handler
  "HTTP routing, request validation and JSON serialization."
  (:require [books.db :as db]
            [cheshire.core :as json]
            [compojure.core :refer [defroutes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.middleware.params :refer [wrap-params]]))

(defn- json-response
  "Build a Ring response with a JSON-encoded body."
  [status body]
  {:status status
   :headers {"Content-Type" "application/json"}
   :body (json/generate-string body)})

(defn- parse-body
  "Parse a JSON request body into a keyword-keyed map, or nil on failure."
  [request]
  (when-let [body (:body request)]
    (try
      (json/parse-string (slurp body) true)
      (catch Exception _ nil))))

(defn- parse-id
  "Parse a path id string into a long, or nil if not numeric."
  [id]
  (try (Long/parseLong id) (catch Exception _ nil)))

(defn- validate
  "Return a vector of validation error messages for a book payload."
  [{:keys [title author]}]
  (cond-> []
    (not (and (string? title) (seq (.trim ^String (or title "")))))
    (conj "title is required")
    (not (and (string? author) (seq (.trim ^String (or author "")))))
    (conj "author is required")))

(defn create-book [ds request]
  (let [data (parse-body request)]
    (cond
      (nil? data) (json-response 400 {:error "invalid JSON body"})
      (seq (validate data)) (json-response 400 {:errors (validate data)})
      :else (json-response 201 (db/create-book! ds data)))))

(defn list-books [ds request]
  (let [author (get-in request [:query-params "author"])]
    (json-response 200 (db/list-books ds author))))

(defn get-book [ds id]
  (if-let [book (some->> (parse-id id) (db/get-book ds))]
    (json-response 200 book)
    (json-response 404 {:error "book not found"})))

(defn update-book [ds id request]
  (let [pid (parse-id id)
        data (parse-body request)]
    (cond
      (nil? pid) (json-response 404 {:error "book not found"})
      (nil? data) (json-response 400 {:error "invalid JSON body"})
      (seq (validate data)) (json-response 400 {:errors (validate data)})
      :else (if-let [updated (db/update-book! ds pid data)]
              (json-response 200 updated)
              (json-response 404 {:error "book not found"})))))

(defn delete-book [ds id]
  (let [pid (parse-id id)]
    (if (and pid (db/delete-book! ds pid))
      (json-response 200 {:deleted pid})
      (json-response 404 {:error "book not found"}))))

(defn make-routes
  "Build the Compojure route handler bound to a datasource `ds`."
  [ds]
  (defroutes routes
    (GET "/health" [] (json-response 200 {:status "ok"}))
    (POST "/books" request (create-book ds request))
    (GET "/books" request (list-books ds request))
    (GET "/books/:id" [id] (get-book ds id))
    (PUT "/books/:id" [id :as request] (update-book ds id request))
    (DELETE "/books/:id" [id] (delete-book ds id))
    (route/not-found (json-response 404 {:error "not found"}))))

(defn app
  "Wrap the routes with parameter parsing middleware."
  [ds]
  (-> (make-routes ds)
      wrap-params))
