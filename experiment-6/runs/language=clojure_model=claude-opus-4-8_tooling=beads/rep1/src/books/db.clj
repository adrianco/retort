(ns books.db
  "SQLite persistence layer for the book collection."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs])
  (:import [java.sql Connection]))

(def default-db-spec
  "Default SQLite database file used by the running service."
  {:dbtype "sqlite" :dbname "books.db"})

(defn datasource
  "Build a next.jdbc datasource from a db spec."
  [db-spec]
  (jdbc/get-datasource db-spec))

(defn init-schema!
  "Create the books table if it does not already exist."
  [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        title   TEXT    NOT NULL,
        author  TEXT    NOT NULL,
        year    INTEGER,
        isbn    TEXT
      )"]))

(def ^:private opts
  {:builder-fn rs/as-unqualified-lower-maps})

(defn- create-on-conn
  "Insert a book on a single connection and return the created row.
   The INSERT and the last_insert_rowid() lookup must share a connection."
  [^Connection conn {:keys [title author year isbn]}]
  (jdbc/execute-one! conn
    ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
     title author year isbn])
  (jdbc/execute-one! conn
    ["SELECT * FROM books WHERE id = last_insert_rowid()"]
    opts))

(defn create-book!
  "Insert a book and return the full created row."
  [ds book]
  (if (instance? Connection ds)
    (create-on-conn ds book)
    (with-open [conn (jdbc/get-connection ds)]
      (create-on-conn conn book))))

(defn list-books
  "Return all books, optionally filtered by author (case-insensitive)."
  [ds author]
  (if (some? author)
    (jdbc/execute! ds
      ["SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id" author]
      opts)
    (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts)))

(defn get-book
  "Return a single book by id, or nil if not found."
  [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

(defn update-book!
  "Update a book by id. Returns the updated row, or nil if it does not exist."
  [ds id {:keys [title author year isbn]}]
  (let [result (jdbc/execute-one! ds
                 ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
                  title author year isbn id])]
    (when (pos? (:next.jdbc/update-count result))
      (get-book ds id))))

(defn delete-book!
  "Delete a book by id. Returns true if a row was removed."
  [ds id]
  (let [result (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id])]
    (pos? (:next.jdbc/update-count result))))
