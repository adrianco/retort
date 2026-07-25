(ns book-api.middleware
  "JSON request/response plumbing and a catch-all error handler."
  (:require [cheshire.core :as json]
            [clojure.java.io :as io]
            [clojure.string :as str])
  (:import (java.io InputStream)))

(def ^:private json-content-type "application/json; charset=utf-8")

(defn- json-request? [request]
  (some-> (get-in request [:headers "content-type"])
          (str/starts-with? "application/json")))

(defn- read-body [request]
  (let [body (:body request)]
    (cond
      (nil? body)                 nil
      (instance? InputStream body) (slurp (io/reader body :encoding "UTF-8"))
      :else                       (str body))))

(defn wrap-json-body
  "Decode a JSON request body into `:json-body` (keywordised keys).

  A body that is present but unparseable short-circuits with 400 rather than
  reaching a handler."
  [handler]
  (fn [request]
    (if-not (json-request? request)
      (handler request)
      (let [raw (read-body request)]
        (if (str/blank? raw)
          (handler request)
          (let [parsed (try
                         {:ok (json/parse-string raw true)}
                         (catch Exception _ :malformed))]
            (if (= :malformed parsed)
              {:status  400
               :headers {"Content-Type" json-content-type}
               :body    (json/generate-string
                         {:error "Malformed JSON in request body"})}
              (handler (assoc request :json-body (:ok parsed))))))))))

(defn wrap-json-response
  "Encode any non-string response body as JSON."
  [handler]
  (fn [request]
    (let [response (handler request)]
      (if (or (nil? (:body response)) (string? (:body response)))
        response
        (-> response
            (assoc :body (json/generate-string (:body response)))
            (assoc-in [:headers "Content-Type"] json-content-type))))))

(defn wrap-errors
  "Turn any uncaught exception into a 500 JSON response."
  [handler]
  (fn [request]
    (try
      (handler request)
      (catch Exception e
        (binding [*out* *err*]
          (println "Unhandled error:" (.getMessage e)))
        {:status  500
         :headers {"Content-Type" json-content-type}
         :body    (json/generate-string {:error "Internal server error"})}))))
