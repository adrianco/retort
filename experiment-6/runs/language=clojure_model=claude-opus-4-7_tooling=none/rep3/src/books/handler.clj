(ns books.handler
  (:require [compojure.core :refer [defroutes routes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [ring.middleware.params :refer [wrap-params]]
            [ring.middleware.keyword-params :refer [wrap-keyword-params]]
            [ring.util.response :refer [response status]]
            [books.db :as db]))

(defn- json-resp [body] (response body))

(defn- error [code msg]
  (-> (response {:error msg}) (status code)))

(defn- parse-id [s]
  (try (Long/parseLong (str s)) (catch Exception _ nil)))

(defn- coerce-year [y]
  (cond
    (nil? y) nil
    (integer? y) y
    (string? y) (try (Long/parseLong y) (catch Exception _ :invalid))
    :else :invalid))

(defn- validate-book [{:keys [title author year]}]
  (let [errs (cond-> []
               (or (nil? title) (and (string? title) (clojure.string/blank? title)))
               (conj "title is required")
               (or (nil? author) (and (string? author) (clojure.string/blank? author)))
               (conj "author is required")
               (= :invalid (coerce-year year))
               (conj "year must be an integer"))]
    (when (seq errs) errs)))

(defn- normalize [body]
  (-> body
      (update :year (fn [y]
                      (let [c (coerce-year y)] (if (= :invalid c) y c))))))

(defn list-handler [ds req]
  (let [author (get-in req [:params :author])
        author (or author (get-in req [:query-params "author"]))]
    (json-resp (db/list-books ds {:author author}))))

(defn get-handler [ds id]
  (if-let [pid (parse-id id)]
    (if-let [book (db/get-book ds pid)]
      (json-resp book)
      (error 404 "book not found"))
    (error 404 "book not found")))

(defn create-handler [ds req]
  (let [body (or (:body req) {})
        body (if (map? body) body {})
        errs (validate-book body)]
    (if errs
      (error 400 (clojure.string/join "; " errs))
      (let [created (db/create-book! ds (normalize body))]
        (-> (json-resp created) (status 201))))))

(defn update-handler [ds id req]
  (if-let [pid (parse-id id)]
    (let [body (or (:body req) {})
          body (if (map? body) body {})
          errs (validate-book body)]
      (if errs
        (error 400 (clojure.string/join "; " errs))
        (if-let [updated (db/update-book! ds pid (normalize body))]
          (json-resp updated)
          (error 404 "book not found"))))
    (error 404 "book not found")))

(defn delete-handler [ds id]
  (if-let [pid (parse-id id)]
    (if (db/delete-book! ds pid)
      {:status 204 :headers {} :body nil}
      (error 404 "book not found"))
    (error 404 "book not found")))

(defn make-routes [ds]
  (routes
    (GET "/health" [] (json-resp {:status "ok"}))
    (GET "/books" req (list-handler ds req))
    (POST "/books" req (create-handler ds req))
    (GET "/books/:id" [id] (get-handler ds id))
    (PUT "/books/:id" [id :as req] (update-handler ds id req))
    (DELETE "/books/:id" [id] (delete-handler ds id))
    (route/not-found {:error "not found"})))

(defn make-app [ds]
  (-> (make-routes ds)
      (wrap-keyword-params)
      (wrap-params)
      (wrap-json-body {:keywords? true})
      (wrap-json-response)))
