(ns book-api.db
  (:require [clojure.java.jdbc :as jdbc]))

(def db-spec
  {:classname "org.sqlite.JDBC"
   :subprotocol "sqlite"
   :subname "books.db"})

(defn init-db []
  (jdbc/execute!
   (jdbc/get-connection db-spec)
   ["CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )"]))

(defn create-book [{:keys [title author year isbn]}]
  (jdbc/insert!
   (jdbc/get-connection db-spec)
   :books
   {:title title :author author :year year :isbn isbn}))

(defn get-all-books []
  (jdbc/query
   (jdbc/get-connection db-spec)
   ["SELECT * FROM books"]))

(defn get-book-by-id [id]
  (let [result (jdbc/query
                (jdbc/get-connection db-spec)
                ["SELECT * FROM books WHERE id = ?" id]
                {:row-fn (fn [r] r)
                 :result-set-fn (fn [rs] (first rs))})]
    (if (seq result)
      result
      nil)))

(defn update-book [id {:keys [title author year isbn]}]
  (jdbc/update!
   (jdbc/get-connection db-spec)
   :books
   {:title title :author author :year year :isbn isbn}
   ["id = ?" id]))

(defn delete-book [id]
  (jdbc/delete!
   (jdbc/get-connection db-spec)
   :books
   ["id = ?" id]))

(defn get-books-by-author [author]
  (jdbc/query
   (jdbc/get-connection db-spec)
   ["SELECT * FROM books WHERE author = ?" author]))
