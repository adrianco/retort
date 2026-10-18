(ns book-api.db
  "SQLite persistence for books. All functions take a next.jdbc datasource."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(def ^:private schema
  "CREATE TABLE IF NOT EXISTS books (
     id     INTEGER PRIMARY KEY AUTOINCREMENT,
     title  TEXT NOT NULL,
     author TEXT NOT NULL,
     year   INTEGER,
     isbn   TEXT
   )")

(def ^:private opts
  {:builder-fn rs/as-unqualified-lower-maps})

(defn make-datasource
  "Creates a datasource for the SQLite database file at `path` and ensures the schema exists."
  [path]
  (let [ds (jdbc/get-datasource {:dbtype "sqlite" :dbname path})]
    (jdbc/execute! ds [schema])
    ds))

(defn create-book!
  "Inserts a book and returns the stored row."
  [ds {:keys [title author year isbn]}]
  (jdbc/execute-one! ds
                     ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING *"
                      title author year isbn]
                     opts))

(defn find-book
  "Returns the book with the given id, or nil."
  [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

(defn list-books
  "Returns all books ordered by id. When `author` is non-nil, only books whose
  author matches case-insensitively are returned."
  [ds author]
  (if author
    (jdbc/execute! ds ["SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id" author] opts)
    (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts)))

(defn update-book!
  "Replaces the fields of the book with the given id. Returns the updated row, or nil if not found."
  [ds id {:keys [title author year isbn]}]
  (jdbc/execute-one! ds
                     ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING *"
                      title author year isbn id]
                     opts))

(defn delete-book!
  "Deletes the book with the given id. Returns true if a row was deleted."
  [ds id]
  (some? (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ? RETURNING id" id] opts)))
