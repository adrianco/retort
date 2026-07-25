(ns book-api.db
  (:require [clojure.java.jdbc :as jdbc])
  (:import [java.sql SQLException]))

(def db-spec
  {:classname "org.sqlite.JDBC"
   :subprotocol "sqlite"
   :subname "books.db"})

(defn init-db []
  "Initialize the database with the books table"
  (jdbc/db-do-commands
    db-spec
    "CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT UNIQUE
    )"))

(defn get-all-books []
  "Get all books from the database"
  (jdbc/query db-spec ["SELECT * FROM books"]))

(defn get-book-by-id [id]
  "Get a single book by ID"
  (jdbc/query db-spec ["SELECT * FROM books WHERE id = ?" id]
              :row-fn (fn [row] row)))

(defn create-book [book]
  "Create a new book"
  (try
    (jdbc/insert! db-spec :books
                  {:title (:title book)
                   :author (:author book)
                   :year (:year book)
                   :isbn (:isbn book)})
    {:success true}
    (catch SQLException e
      {:success false :error (.getMessage e)})))

(defn update-book [id book]
  "Update an existing book"
  (try
    (jdbc/update! db-spec :books
                  {:title (:title book)
                   :author (:author book)
                   :year (:year book)
                   :isbn (:isbn book)}
                  ["id = ?" id])
    {:success true}
    (catch SQLException e
      {:success false :error (.getMessage e)})))

(defn delete-book [id]
  "Delete a book by ID"
  (jdbc/delete! db-spec :books ["id = ?" id]))

(defn get-books-by-author [author]
  "Get all books by a specific author"
  (jdbc/query db-spec ["SELECT * FROM books WHERE author = ?" author]))
