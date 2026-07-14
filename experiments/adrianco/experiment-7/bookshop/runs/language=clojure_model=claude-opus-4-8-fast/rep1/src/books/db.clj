(ns books.db
  "SQLite-backed persistence for the book collection."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(def default-db
  "Default datasource spec — a file-backed SQLite database."
  {:dbtype "sqlite" :dbname "books.db"})

(defn datasource
  "Build a next.jdbc datasource from a db spec (defaults to `default-db`)."
  ([] (datasource default-db))
  ([db-spec] (jdbc/get-datasource db-spec)))

(defn init-db!
  "Create the books table if it does not already exist."
  [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        title   TEXT NOT NULL,
        author  TEXT NOT NULL,
        year    INTEGER,
        isbn    TEXT
      )"]))

(def ^:private opts
  {:return-keys true :builder-fn rs/as-unqualified-maps})

(defn list-books
  "Return all books, optionally filtered by author."
  ([ds] (list-books ds nil))
  ([ds author]
   (if (seq author)
     (jdbc/execute! ds ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
     (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts))))

(defn get-book
  "Return a single book by id, or nil if not found."
  [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

(defn create-book!
  "Insert a new book and return the created row."
  [ds {:keys [title author year isbn]}]
  (let [result (jdbc/execute-one! ds
                 ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
                  title author year isbn]
                 {:return-keys true})
        id (or (:id result)
               (get result (keyword "last_insert_rowid()")))]
    (get-book ds id)))

(defn update-book!
  "Update an existing book by id. Returns the updated row, or nil if absent."
  [ds id {:keys [title author year isbn]}]
  (when (get-book ds id)
    (jdbc/execute-one! ds
      ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
       title author year isbn id])
    (get-book ds id)))

(defn delete-book!
  "Delete a book by id. Returns true if a row was removed."
  [ds id]
  (let [result (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id])]
    (pos? (or (:next.jdbc/update-count result) 0))))
