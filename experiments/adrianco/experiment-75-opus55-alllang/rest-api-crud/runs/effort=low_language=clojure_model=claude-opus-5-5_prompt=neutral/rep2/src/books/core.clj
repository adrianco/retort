(ns books.core
  (:require [cheshire.core :as json]
            [compojure.core :refer [routes GET POST PUT DELETE]]
            [compojure.route :as route]
            [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.params :refer [wrap-params]])
  (:gen-class))

(def opts {:builder-fn rs/as-unqualified-lower-maps})

(defn make-db [path]
  (let [ds (jdbc/get-datasource {:dbtype "sqlite" :dbname path})]
    (jdbc/execute! ds ["CREATE TABLE IF NOT EXISTS books (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         title TEXT NOT NULL, author TEXT NOT NULL,
                         year INTEGER, isbn TEXT)"])
    ds))

(defn- resp [status body]
  {:status status
   :headers {"Content-Type" "application/json"}
   :body (json/generate-string body)})

(defn- blank? [v] (or (not (string? v)) (clojure.string/blank? v)))

(defn validate [b]
  (cond-> []
    (blank? (:title b)) (conj "title is required")
    (blank? (:author b)) (conj "author is required")
    (and (some? (:year b)) (not (integer? (:year b)))) (conj "year must be an integer")
    (and (some? (:isbn b)) (not (string? (:isbn b)))) (conj "isbn must be a string")))

(defn- parse-body [req]
  (try (let [b (json/parse-string (slurp (:body req)) true)]
         (when (map? b) b))
       (catch Exception _ nil)))

(defn- parse-id [s] (try (Long/parseLong s) (catch Exception _ nil)))

(defn- find-book [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

(defn- with-valid-body [req f]
  (if-let [b (parse-body req)]
    (let [errs (validate b)]
      (if (seq errs) (resp 400 {:errors errs}) (f b)))
    (resp 400 {:errors ["invalid JSON body"]})))

(defn- handler [ds]
  (routes
   (GET "/health" [] (resp 200 {:status "ok"}))
   (GET "/books" [author]
     (resp 200 (if author
                 (jdbc/execute! ds ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
                 (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts))))
   (POST "/books" req
     (with-valid-body req
       (fn [{:keys [title author year isbn]}]
         (let [r (jdbc/execute-one! ds ["INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?) RETURNING *"
                                        title author year isbn] opts)]
           (resp 201 r)))))
   (GET "/books/:id" [id]
     (if-let [b (some->> (parse-id id) (find-book ds))]
       (resp 200 b) (resp 404 {:error "book not found"})))
   (PUT "/books/:id" [id :as req]
     (if-let [id (some-> (parse-id id) (#(when (find-book ds %) %)))]
       (with-valid-body req
         (fn [{:keys [title author year isbn]}]
           (jdbc/execute! ds ["UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?"
                              title author year isbn id])
           (resp 200 (find-book ds id))))
       (resp 404 {:error "book not found"})))
   (DELETE "/books/:id" [id]
     (let [n (some->> (parse-id id)
                      (vector "DELETE FROM books WHERE id = ?")
                      (jdbc/execute-one! ds)
                      :next.jdbc/update-count)]
       (if (and n (pos? n)) {:status 204 :body ""} (resp 404 {:error "book not found"}))))
   (route/not-found (resp 404 {:error "not found"}))))

(defn app [ds] (wrap-params (handler ds)))

(defn -main [& _]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))
        ds (make-db (or (System/getenv "DB_PATH") "books.db"))]
    (println "Listening on port" port)
    (jetty/run-jetty (app ds) {:port port :join? true})))
