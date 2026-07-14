(ns books.core
  (:require [compojure.core :refer [defroutes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [ring.middleware.params :refer [wrap-params]]
            [ring.util.response :as resp]
            [books.db :as db])
  (:gen-class))

(defonce ^:private state (atom {}))

(defn- ds [] (:ds @state))

(defn- parse-id [s]
  (try (Long/parseLong s) (catch Exception _ nil)))

(defn- bad-request [msg]
  {:status 400 :body {:error msg}})

(defn- not-found [msg]
  {:status 404 :body {:error msg}})

(defn- validate-create [body]
  (let [title (some-> (:title body) str clojure.string/trim)
        author (some-> (:author body) str clojure.string/trim)]
    (cond
      (or (nil? body) (not (map? body)))
      "request body must be a JSON object"
      (or (nil? (:title body)) (empty? title))
      "title is required"
      (or (nil? (:author body)) (empty? author))
      "author is required"
      (and (some? (:year body)) (not (integer? (:year body))))
      "year must be an integer"
      :else nil)))

(defn health-handler [_]
  {:status 200 :body {:status "ok"}})

(defn create-book-handler [{:keys [body]}]
  (if-let [err (validate-create body)]
    (bad-request err)
    (let [book (db/create-book! (ds) body)]
      {:status 201 :body book})))

(defn list-books-handler [{:keys [params]}]
  {:status 200
   :body (db/list-books (ds) {:author (get params "author")})})

(defn get-book-handler [{:keys [route-params]}]
  (if-let [id (parse-id (:id route-params))]
    (if-let [book (db/get-book (ds) id)]
      {:status 200 :body book}
      (not-found "book not found"))
    (bad-request "invalid id")))

(defn update-book-handler [{:keys [route-params body]}]
  (if-let [id (parse-id (:id route-params))]
    (cond
      (or (nil? body) (not (map? body)))
      (bad-request "request body must be a JSON object")
      (and (contains? body :title)
           (or (nil? (:title body))
               (empty? (clojure.string/trim (str (:title body))))))
      (bad-request "title cannot be empty")
      (and (contains? body :author)
           (or (nil? (:author body))
               (empty? (clojure.string/trim (str (:author body))))))
      (bad-request "author cannot be empty")
      (and (contains? body :year)
           (some? (:year body))
           (not (integer? (:year body))))
      (bad-request "year must be an integer")
      :else
      (if-let [book (db/update-book! (ds) id body)]
        {:status 200 :body book}
        (not-found "book not found")))
    (bad-request "invalid id")))

(defn delete-book-handler [{:keys [route-params]}]
  (if-let [id (parse-id (:id route-params))]
    (if (db/delete-book! (ds) id)
      {:status 204 :body nil}
      (not-found "book not found"))
    (bad-request "invalid id")))

(defroutes app-routes
  (GET    "/health"     [] health-handler)
  (POST   "/books"      [] create-book-handler)
  (GET    "/books"      [] list-books-handler)
  (GET    "/books/:id"  [] get-book-handler)
  (PUT    "/books/:id"  [] update-book-handler)
  (DELETE "/books/:id"  [] delete-book-handler)
  (route/not-found {:status 404 :body {:error "not found"}}))

(def app
  (-> app-routes
      (wrap-json-body {:keywords? true})
      wrap-json-response
      wrap-params))

(defn set-datasource! [datasource]
  (swap! state assoc :ds datasource)
  datasource)

(defn start!
  ([] (start! {}))
  ([{:keys [port db-path join?]
     :or {port 3000 db-path "books.db" join? false}}]
   (let [datasource (db/make-datasource db-path)]
     (db/init-schema! datasource)
     (set-datasource! datasource)
     (jetty/run-jetty app {:port port :join? join?}))))

(defn -main [& args]
  (let [port (or (some-> (System/getenv "PORT") Long/parseLong) 3000)
        db-path (or (System/getenv "DB_PATH") "books.db")]
    (println (str "Starting books API on http://localhost:" port " (db=" db-path ")"))
    (start! {:port port :db-path db-path :join? true})))
