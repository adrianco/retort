(ns books.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(def ^:private schema
  "CREATE TABLE IF NOT EXISTS books (
     id     INTEGER PRIMARY KEY AUTOINCREMENT,
     title  TEXT NOT NULL,
     author TEXT NOT NULL,
     year   INTEGER,
     isbn   TEXT)")

(def ^:private opts {:builder-fn rs/as-unqualified-kebab-maps})

(defn datasource
  "Opens (and creates if needed) the SQLite database at db-path."
  [db-path]
  (let [ds (jdbc/get-datasource {:dbtype "sqlite" :dbname db-path})]
    (jdbc/execute! ds [schema])
    ds))

(defn create-book!
  "Inserts a book and returns it with its generated id."
  [ds {:keys [title author year isbn]}]
  ;; last_insert_rowid() is per-connection, so insert and read it in one transaction.
  (jdbc/with-transaction [tx ds]
    (jdbc/execute-one! tx ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
                           title author year isbn])
    (jdbc/execute-one! tx ["SELECT * FROM books WHERE id = last_insert_rowid()"] opts)))

(defn get-book
  "Returns the book with the given id, or nil."
  [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

(defn list-books
  "Returns all books, optionally filtered by author (case-insensitive exact match)."
  ([ds]
   (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts))
  ([ds author]
   (jdbc/execute! ds ["SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id" author] opts)))

(defn update-book!
  "Replaces the fields of an existing book. Returns the updated book, or nil if no such id."
  [ds id {:keys [title author year isbn]}]
  (let [result (jdbc/execute-one! ds ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
                                      title author year isbn id])]
    (when (pos? (:next.jdbc/update-count result 0))
      (get-book ds id))))

(defn delete-book!
  "Deletes the book with the given id. Returns true if a row was removed."
  [ds id]
  (pos? (:next.jdbc/update-count (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id]))))
