(ns books.handler
  "HTTP routing and request handling for the book collection API."
  (:require [books.db :as db]
            [cheshire.core :as json]
            [clojure.string :as str]
            [compojure.core :refer [defroutes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.middleware.params :refer [wrap-params]]))

(defn- json-response
  [status body]
  {:status  status
   :headers {"Content-Type" "application/json"}
   :body    (json/generate-string body)})

(defn- parse-body
  "Parse a JSON request body into a keywordized map. Returns nil on
  empty or malformed input."
  [req]
  (let [body (:body req)]
    (when body
      (let [s (slurp body)]
        (when-not (str/blank? s)
          (try (json/parse-string s true)
               (catch Exception _ ::invalid)))))))

(defn- validate
  "Return a vector of validation error messages (empty when valid)."
  [{:keys [title author]}]
  (cond-> []
    (str/blank? (str title))  (conj "title is required")
    (str/blank? (str author)) (conj "author is required")))

(defn- parse-id [id-str]
  (try (Long/parseLong id-str) (catch Exception _ nil)))

(defn create-book [ds req]
  (let [body (parse-body req)]
    (cond
      (or (nil? body) (= ::invalid body))
      (json-response 400 {:error "invalid or missing JSON body"})

      :else
      (let [errors (validate body)]
        (if (seq errors)
          (json-response 400 {:errors errors})
          (json-response 201 (db/create-book! ds body)))))))

(defn list-books [ds req]
  (let [author (get-in req [:params "author"])]
    (json-response 200 (db/list-books ds {:author author}))))

(defn get-book [ds id-str]
  (if-let [id (parse-id id-str)]
    (if-let [book (db/get-book ds id)]
      (json-response 200 book)
      (json-response 404 {:error "book not found"}))
    (json-response 400 {:error "invalid id"})))

(defn update-book [ds id-str req]
  (if-let [id (parse-id id-str)]
    (let [body (parse-body req)]
      (cond
        (or (nil? body) (= ::invalid body))
        (json-response 400 {:error "invalid or missing JSON body"})

        :else
        (let [errors (validate body)]
          (if (seq errors)
            (json-response 400 {:errors errors})
            (if-let [updated (db/update-book! ds id body)]
              (json-response 200 updated)
              (json-response 404 {:error "book not found"}))))))
    (json-response 400 {:error "invalid id"})))

(defn delete-book [ds id-str]
  (if-let [id (parse-id id-str)]
    (if (db/delete-book! ds id)
      (json-response 204 nil)
      (json-response 404 {:error "book not found"}))
    (json-response 400 {:error "invalid id"})))

(defn make-routes [ds]
  (defroutes routes
    (GET    "/health"      []         (json-response 200 {:status "ok"}))
    (POST   "/books"       req        (create-book ds req))
    (GET    "/books"       req        (list-books ds req))
    (GET    "/books/:id"   [id]       (get-book ds id))
    (PUT    "/books/:id"   [id :as r] (update-book ds id r))
    (DELETE "/books/:id"   [id]       (delete-book ds id))
    (route/not-found (json-response 404 {:error "not found"}))))

(defn make-app
  "Build the Ring handler backed by the given datasource."
  [ds]
  (wrap-params (make-routes ds)))
