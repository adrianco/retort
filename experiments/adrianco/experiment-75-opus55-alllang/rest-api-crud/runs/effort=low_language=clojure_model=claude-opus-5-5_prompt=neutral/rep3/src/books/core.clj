(ns books.core
  (:require [cheshire.core :as json]
            [clojure.string :as str]
            [compojure.core :refer [routes GET POST PUT DELETE]]
            [compojure.route :as route]
            [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]
            [ring.adapter.jetty :refer [run-jetty]])
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

(defn- blank? [v] (or (not (string? v)) (str/blank? v)))

(defn validate [b]
  (cond-> []
    (not (map? b)) (conj "body must be a JSON object")
    (and (map? b) (blank? (get b "title"))) (conj "title is required")
    (and (map? b) (blank? (get b "author"))) (conj "author is required")
    (and (map? b) (some? (get b "year")) (not (integer? (get b "year")))) (conj "year must be an integer")
    (and (map? b) (some? (get b "isbn")) (not (string? (get b "isbn")))) (conj "isbn must be a string")))

(defn- parse-body [req]
  (try (some-> (:body req) slurp not-empty (json/parse-string))
       (catch Exception _ ::invalid)))

(defn- parse-id [s] (try (Long/parseLong s) (catch Exception _ nil)))

(defn- find-book [db id]
  (jdbc/execute-one! db ["SELECT * FROM books WHERE id = ?" id] opts))

(defn- with-book-body [req f]
  (let [b (parse-body req)]
    (if (= b ::invalid)
      (resp 400 {:error "invalid JSON"})
      (let [errs (validate b)]
        (if (seq errs) (resp 400 {:errors errs}) (f b))))))

(defn app [db]
  (routes
   (GET "/health" [] (resp 200 {:status "ok"}))
   (GET "/books" {{:strs [author]} :query-params :as req}
     (let [author (or author (some->> (:query-string req)
                                      (re-find #"(?:^|&)author=([^&]*)")
                                      second
                                      (#(java.net.URLDecoder/decode % "UTF-8"))))]
       (resp 200 (if author
                   (jdbc/execute! db ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
                   (jdbc/execute! db ["SELECT * FROM books ORDER BY id"] opts)))))
   (POST "/books" req
     (with-book-body req
       (fn [b]
         (let [r (jdbc/execute-one! db ["INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?) RETURNING *"
                                        (b "title") (b "author") (b "year") (b "isbn")] opts)]
           (resp 201 r)))))
   (GET "/books/:id" [id]
     (if-let [b (some->> (parse-id id) (find-book db))]
       (resp 200 b) (resp 404 {:error "book not found"})))
   (PUT "/books/:id" [id :as req]
     (if-let [i (some->> (parse-id id) (find-book db) :id)]
       (with-book-body req
         (fn [b]
           (jdbc/execute! db ["UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?"
                              (b "title") (b "author") (b "year") (b "isbn") i])
           (resp 200 (find-book db i))))
       (resp 404 {:error "book not found"})))
   (DELETE "/books/:id" [id]
     (let [n (some->> (parse-id id)
                      (vector "DELETE FROM books WHERE id = ?")
                      (jdbc/execute-one! db) ::jdbc/update-count)]
       (if (and n (pos? n)) {:status 204 :headers {} :body ""} (resp 404 {:error "book not found"}))))
   (route/not-found (resp 404 {:error "not found"}))))

(defn -main [& _]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))
        db (make-db (or (System/getenv "DB_PATH") "books.db"))]
    (println "Listening on port" port)
    (run-jetty (app db) {:port port})))
