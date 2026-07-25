(ns book-api.db
  "SQLite persistence for the book collection.

  A `ds` is any next.jdbc-compatible datasource; every function here takes one
  explicitly so that tests can point at a throwaway database file."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]
            [next.jdbc.sql :as sql]))

(def ^:private opts
  {:builder-fn rs/as-unqualified-lower-maps})

(defn datasource
  "Build a datasource for the SQLite database at `path`.
  `path` may be a filename such as \"books.db\"."
  [path]
  (jdbc/get-datasource {:dbtype "sqlite" :dbname path}))

(defn migrate!
  "Create the books table if it is not already there. Safe to call repeatedly."
  [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        title  TEXT    NOT NULL,
        author TEXT    NOT NULL,
        year   INTEGER,
        isbn   TEXT    UNIQUE
      )"])
  ds)

(defn ping
  "Return true when the database answers a trivial query."
  [ds]
  (= 1 (:one (jdbc/execute-one! ds ["SELECT 1 AS one"] opts))))

(defn find-book
  "Return the book with `id`, or nil."
  [ds id]
  (sql/get-by-id ds :books id opts))

(defn insert-book!
  "Insert `book` (keys :title :author :year :isbn) and return the stored row.

  SQLite's JDBC driver only hands back the generated rowid, so the row is read
  back inside the same transaction."
  [ds book]
  (jdbc/with-transaction [tx ds]
    (sql/insert! tx :books (select-keys book [:title :author :year :isbn]) opts)
    (jdbc/execute-one! tx ["SELECT * FROM books WHERE id = last_insert_rowid()"] opts)))

(defn list-books
  "Return all books ordered by id. When `author` is given, only books whose
  author matches it (case-insensitively, exact match) are returned."
  [ds {:keys [author]}]
  (if author
    (sql/query ds ["SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id" author] opts)
    (sql/query ds ["SELECT * FROM books ORDER BY id"] opts)))

(defn update-book!
  "Replace the stored fields of book `id`. Returns the updated row, or nil when
  no such book exists."
  [ds id book]
  (let [n (::jdbc/update-count
           (sql/update! ds :books
                        (select-keys book [:title :author :year :isbn])
                        {:id id}
                        opts))]
    (when (pos? n)
      (find-book ds id))))

(defn delete-book!
  "Delete book `id`. Returns true when a row was removed."
  [ds id]
  (pos? (::jdbc/update-count (sql/delete! ds :books {:id id} opts))))

(defn isbn-owner
  "Return the id of the book already using `isbn`, or nil."
  [ds isbn]
  (when isbn
    (:id (jdbc/execute-one! ds ["SELECT id FROM books WHERE isbn = ?" isbn] opts))))
