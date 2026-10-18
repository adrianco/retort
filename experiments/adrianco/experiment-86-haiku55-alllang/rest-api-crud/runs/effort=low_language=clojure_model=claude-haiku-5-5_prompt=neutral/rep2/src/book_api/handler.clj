(ns book-api.handler
  "Ring handler exposing the book REST API."
  (:require [book-api.db :as db]
            [book-api.validation :as v]
            [cheshire.core :as json]
            [clojure.string :as str]
            [ring.middleware.params :refer [wrap-params]]))

(defn- json-response [status body]
  {:status status
   :headers {"Content-Type" "application/json"}
   :body (json/generate-string body)})

(defn- error-response [status message]
  (json-response status {:error message}))

(defn- validation-response [errors]
  (json-response 422 {:error "validation failed" :fields errors}))

(defn- parse-body
  "Parses the JSON request body into a keyword-keyed map. Returns nil when the
  body is missing, not JSON, or not a JSON object."
  [req]
  (when-let [body (some-> (:body req) slurp not-empty)]
    (try
      (let [parsed (json/parse-string body true)]
        (when (map? parsed) parsed))
      (catch Exception _ nil))))

(defn- parse-id [s]
  (when (and s (re-matches #"\d+" s))
    (Long/parseLong s)))

(defn- book-fields [body]
  (select-keys body [:title :author :year :isbn]))

(defn- handle-health []
  (json-response 200 {:status "ok"}))

(defn- handle-create [ds req]
  (let [body (parse-body req)
        errors (some-> body v/validate-book)]
    (cond
      (nil? body) (error-response 400 "request body must be a JSON object")
      errors (validation-response errors)
      :else (json-response 201 (db/create-book! ds (v/normalize-book (book-fields body)))))))

(defn- handle-list [ds req]
  (let [author (get-in req [:query-params "author"])]
    (json-response 200 (db/list-books ds (when-not (str/blank? author) author)))))

(defn- handle-get [ds id]
  (if-let [book (db/find-book ds id)]
    (json-response 200 book)
    (error-response 404 "book not found")))

(defn- handle-update [ds id req]
  (let [body (parse-body req)
        errors (some-> body v/validate-book)]
    (cond
      (nil? body) (error-response 400 "request body must be a JSON object")
      errors (validation-response errors)
      :else (if-let [book (db/update-book! ds id (v/normalize-book (book-fields body)))]
              (json-response 200 book)
              (error-response 404 "book not found")))))

(defn- handle-delete [ds id]
  (if (db/delete-book! ds id)
    {:status 204 :headers {} :body ""}
    (error-response 404 "book not found")))

(defn- route
  "Returns a [handler-fn args] pair for the request, or a keyword describing the failure."
  [req]
  (let [method (:request-method req)
        path (:uri req)
        segments (vec (remove str/blank? (str/split path #"/")))]
    (cond
      (= segments ["health"]) (if (= method :get) [:health] :method-not-allowed)
      (= segments ["books"]) (case method
                               :post [:create]
                               :get [:list]
                               :method-not-allowed)
      (and (= (count segments) 2) (= (first segments) "books"))
      (let [id (parse-id (second segments))]
        (cond
          (nil? id) :not-found
          :else (case method
                  :get [:get id]
                  :put [:update id]
                  :delete [:delete id]
                  :method-not-allowed)))
      :else :not-found)))

(defn- make-handler* [ds]
  (fn [req]
    (try
      (let [r (route req)]
        (cond
          (= r :not-found) (error-response 404 "not found")
          (= r :method-not-allowed) (error-response 405 "method not allowed")
          :else (let [[op id] r]
                  (case op
                    :health (handle-health)
                    :create (handle-create ds req)
                    :list (handle-list ds req)
                    :get (handle-get ds id)
                    :update (handle-update ds id req)
                    :delete (handle-delete ds id)))))
      (catch Exception e
        (binding [*out* *err*]
          (println "unhandled error:" (.getMessage e)))
        (error-response 500 "internal server error")))))

(defn make-handler
  "Returns a Ring handler backed by the datasource `ds`."
  [ds]
  (wrap-params (make-handler* ds)))
