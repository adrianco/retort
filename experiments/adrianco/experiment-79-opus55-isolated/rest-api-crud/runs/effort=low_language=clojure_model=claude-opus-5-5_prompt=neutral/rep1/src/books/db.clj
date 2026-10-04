(ns books.db
  "SQLite persistence for books."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(def ^:private opts {:builder-fn rs/as-unqualified-lower-maps})

(defn datasource
  "Returns a datasource for the SQLite database file at `path`."
  [path]
  (jdbc/get-datasource {:dbtype "sqlite" :dbname path}))

(defn init!
  "Creates the schema if it does not exist. Returns the datasource."
  [ds]
  (jdbc/execute! ds ["CREATE TABLE IF NOT EXISTS books (
                        id     INTEGER PRIMARY KEY AUTOINCREMENT,
                        title  TEXT NOT NULL,
                        author TEXT NOT NULL,
                        year   INTEGER,
                        isbn   TEXT)"])
  ds)

(defn create-book! [ds {:keys [title author year isbn]}]
  (jdbc/execute-one!
   ds
   ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING *"
    title author year isbn]
   opts))

(defn list-books
  "Lists all books, optionally restricted to an exact `author` match."
  [ds author]
  (jdbc/execute!
   ds
   (if author
     ["SELECT * FROM books WHERE author = ? ORDER BY id" author]
     ["SELECT * FROM books ORDER BY id"])
   opts))

(defn get-book [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

(defn update-book!
  "Replaces the book with `id`. Returns the updated book, or nil if absent."
  [ds id {:keys [title author year isbn]}]
  (jdbc/execute-one!
   ds
   ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING *"
    title author year isbn id]
   opts))

(defn delete-book!
  "Deletes the book with `id`. Returns true if a row was removed."
  [ds id]
  (pos? (:next.jdbc/update-count
         (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id]))))
