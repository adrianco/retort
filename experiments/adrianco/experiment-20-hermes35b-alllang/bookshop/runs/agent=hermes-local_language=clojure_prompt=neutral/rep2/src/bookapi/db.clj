(ns bookapi.db
  (:require [org.clojure.java.jdbc :as jdbc]))

(def db-spec {:dbtype "sqlite"
              :dbname "books.db"})

(defn init-db! []
  (jdbc/db-do-commands db-spec
    ["CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT UNIQUE
    )"]))

(defn insert-book [book]
  (jdbc/insert! db-spec :books book))

(defn get-all-books []
  (jdbc/query db-spec ["SELECT * FROM books"]))

(defn get-book-by-author [author]
  (jdbc/query db-spec ["SELECT * FROM books WHERE author = ?" author]))

(defn get-book-by-id [id]
  (first (jdbc/query db-spec ["SELECT * FROM books WHERE id = ?" id])))

(defn update-book [id book]
  (jdbc/update! db-spec :books book ["id = ?" id]))

(defn delete-book [id]
  (jdbc/delete! db-spec :books ["id = ?" id]))

(defn db-connected? []
  (try
    (jdbc/db-test! db-spec)
    true
    (catch Exception _
      false)))
