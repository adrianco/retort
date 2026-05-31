(ns books.db
  "SQLite persistence layer for the book collection."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(defn make-datasource
  "Create a SQLite datasource. `db-name` is a file path, or \":memory:\"
  for an in-memory database (handy for tests).

  For in-memory databases we return a single long-lived connection: a
  plain datasource would open a fresh (empty) database on every call,
  losing the schema and any data between requests."
  [db-name]
  (let [spec {:dbtype "sqlite" :dbname db-name}]
    (if (= ":memory:" db-name)
      (jdbc/get-connection spec)
      (jdbc/get-datasource spec))))

(defn init-schema!
  "Create the books table if it does not already exist."
  [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        title  TEXT NOT NULL,
        author TEXT NOT NULL,
        year   INTEGER,
        isbn   TEXT)"]))

(def ^:private opts
  {:builder-fn rs/as-unqualified-lower-maps})

(defn create-book!
  "Insert a book and return the freshly created row."
  [ds {:keys [title author year isbn]}]
  (let [row (jdbc/execute-one! ds
              ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
               title author year isbn]
              {:return-keys true})
        id  (or (:books/id row) (get row (keyword "last_insert_rowid()"))
                (val (first row)))]
    (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts)))

(defn list-books
  "Return all books, optionally filtered by author (exact match)."
  [ds {:keys [author]}]
  (if author
    (jdbc/execute! ds ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
    (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts)))

(defn get-book
  "Return a single book by id, or nil."
  [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

(defn update-book!
  "Update the book with the given id. Returns the updated row, or nil if
  no such book exists."
  [ds id {:keys [title author year isbn]}]
  (let [res (jdbc/execute-one! ds
              ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
               title author year isbn id])]
    (when (pos? (or (:next.jdbc/update-count res) 0))
      (get-book ds id))))

(defn delete-book!
  "Delete the book with the given id. Returns true if a row was removed."
  [ds id]
  (let [res (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id])]
    (pos? (or (:next.jdbc/update-count res) 0))))
