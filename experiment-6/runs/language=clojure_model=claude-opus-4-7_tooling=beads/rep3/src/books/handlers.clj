(ns books.handlers
  (:require [books.db :as db]
            [cheshire.core :as json]))

(defn- json-response
  ([status body] (json-response status body {}))
  ([status body extra-headers]
   {:status status
    :headers (merge {"Content-Type" "application/json"} extra-headers)
    :body (json/generate-string body)}))

(defn- parse-json-body
  "Parse a request body to a Clojure map keyed with keywords. Returns nil on
   failure or empty body."
  [body]
  (cond
    (nil? body) nil
    (string? body) (when-not (empty? body)
                     (try (json/parse-string body true)
                          (catch Exception _ ::invalid)))
    :else (try (json/parse-string (slurp body) true)
               (catch Exception _ ::invalid))))

(defn- blank? [s]
  (or (nil? s)
      (and (string? s) (clojure.string/blank? s))))

(defn- validate-book [body]
  (cond
    (or (nil? body) (= ::invalid body))
    {:error "Invalid JSON body"}

    (not (map? body))
    {:error "Request body must be a JSON object"}

    (blank? (:title body))
    {:error "Field 'title' is required"}

    (blank? (:author body))
    {:error "Field 'author' is required"}

    (and (some? (:year body)) (not (integer? (:year body))))
    {:error "Field 'year' must be an integer"}

    :else nil))

(defn- parse-id [s]
  (try (Long/parseLong s)
       (catch Exception _ nil)))

(defn health-handler [_req]
  (json-response 200 {:status "ok"}))

(defn create-book-handler [{:keys [body] :as _req} ds]
  (let [parsed (parse-json-body body)]
    (if-let [err (validate-book parsed)]
      (json-response 400 err)
      (let [created (db/create-book! ds parsed)]
        (json-response 201 created)))))

(defn list-books-handler [{:keys [query-params] :as _req} ds]
  (let [author (get query-params "author")
        rows (db/list-books ds author)]
    (json-response 200 rows)))

(defn get-book-handler [req ds]
  (let [id (parse-id (get-in req [:path-params :id]))]
    (if-let [book (and id (db/get-book ds id))]
      (json-response 200 book)
      (json-response 404 {:error "Book not found"}))))

(defn update-book-handler [{:keys [body] :as req} ds]
  (let [id (parse-id (get-in req [:path-params :id]))
        parsed (parse-json-body body)]
    (cond
      (nil? id)
      (json-response 404 {:error "Book not found"})

      :else
      (if-let [err (validate-book parsed)]
        (json-response 400 err)
        (if-let [updated (db/update-book! ds id parsed)]
          (json-response 200 updated)
          (json-response 404 {:error "Book not found"}))))))

(defn delete-book-handler [req ds]
  (let [id (parse-id (get-in req [:path-params :id]))]
    (if (and id (db/delete-book! ds id))
      {:status 204 :headers {} :body ""}
      (json-response 404 {:error "Book not found"}))))
