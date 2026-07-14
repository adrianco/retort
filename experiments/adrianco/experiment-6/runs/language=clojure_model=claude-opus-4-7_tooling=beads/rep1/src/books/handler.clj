(ns books.handler
  (:require [books.db :as db]
            [compojure.core :refer [GET POST PUT DELETE routes]]
            [compojure.route :as route]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [ring.middleware.params :refer [wrap-params]]
            [ring.util.response :as resp]))

(defn- json-response [status body]
  (-> (resp/response body)
      (resp/status status)
      (resp/content-type "application/json")))

(defn- non-blank? [s]
  (and (string? s) (seq (.trim ^String s))))

(defn- validate-book
  "Returns a vector of error strings (empty when valid)."
  [body]
  (let [{:strs [title author year isbn]} (when (map? body) body)]
    (cond-> []
      (not (map? body))               (conj "request body must be a JSON object")
      (and (map? body)
           (not (non-blank? title)))  (conj "title is required")
      (and (map? body)
           (not (non-blank? author))) (conj "author is required")
      (and (some? year)
           (not (integer? year)))     (conj "year must be an integer")
      (and (some? isbn)
           (not (string? isbn)))      (conj "isbn must be a string"))))

(defn- parse-id [s]
  (try (Long/parseLong s) (catch Exception _ nil)))

(defn- coerce-book [body]
  {:title  (get body "title")
   :author (get body "author")
   :year   (get body "year")
   :isbn   (get body "isbn")})

(defn- health [_]
  (json-response 200 {:status "ok"}))

(defn- list-handler [ds req]
  (let [author (get-in req [:params "author"])
        books  (if (non-blank? author)
                 (db/list-books ds author)
                 (db/list-books ds))]
    (json-response 200 books)))

(defn- get-handler [ds id-str]
  (if-let [id (parse-id id-str)]
    (if-let [book (db/get-book ds id)]
      (json-response 200 book)
      (json-response 404 {:error "book not found"}))
    (json-response 400 {:error "invalid id"})))

(defn- create-handler [ds {body :body}]
  (let [errors (validate-book body)]
    (if (seq errors)
      (json-response 400 {:errors errors})
      (let [created (db/insert-book! ds (coerce-book body))]
        (json-response 201 created)))))

(defn- update-handler [ds id-str {body :body}]
  (if-let [id (parse-id id-str)]
    (let [errors (validate-book body)]
      (cond
        (seq errors)
        (json-response 400 {:errors errors})

        (nil? (db/get-book ds id))
        (json-response 404 {:error "book not found"})

        :else
        (json-response 200 (db/update-book! ds id (coerce-book body)))))
    (json-response 400 {:error "invalid id"})))

(defn- delete-handler [ds id-str]
  (if-let [id (parse-id id-str)]
    (if (db/delete-book! ds id)
      {:status 204 :headers {} :body ""}
      (json-response 404 {:error "book not found"}))
    (json-response 400 {:error "invalid id"})))

(defn- wrap-json-error [handler]
  (fn [req]
    (try
      (handler req)
      (catch com.fasterxml.jackson.core.JsonParseException _
        (json-response 400 {:error "invalid JSON body"})))))

(defn app-routes [ds]
  (-> (routes
        (GET    "/health"      []  health)
        (GET    "/books"       req (list-handler ds req))
        (POST   "/books"       req (create-handler ds req))
        (GET    "/books/:id"   [id]       (fn [_] (get-handler ds id)))
        (PUT    "/books/:id"   [id :as r] (update-handler ds id r))
        (DELETE "/books/:id"   [id]       (fn [_] (delete-handler ds id)))
        (route/not-found (json-response 404 {:error "not found"})))
      (wrap-json-error)
      (wrap-json-body)
      (wrap-json-response)
      (wrap-params)))
