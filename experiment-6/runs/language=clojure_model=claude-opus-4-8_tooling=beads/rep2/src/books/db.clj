(ns books.db
  "SQLite persistence layer for the book collection."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(defn make-datasource
  "Create a datasource for the given SQLite database file (or \":memory:\")."
  [db-path]
  (jdbc/get-datasource {:dbtype "sqlite" :dbname db-path}))

(def ^:private opts
  {:builder-fn rs/as-unqualified-maps})

(defn init-schema!
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

(defn list-books
  "Return all books, optionally filtered by author."
  ([ds] (list-books ds nil))
  ([ds author]
   (if (seq author)
     (jdbc/execute! ds
       ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
     (jdbc/execute! ds
       ["SELECT * FROM books ORDER BY id"] opts))))

(defn get-book
  "Return the book with the given id, or nil if absent."
  [ds id]
  (jdbc/execute-one! ds
    ["SELECT * FROM books WHERE id = ?" id] opts))

(defn create-book!
  "Insert a book and return the created row."
  [ds {:keys [title author year isbn]}]
  (let [row (jdbc/execute-one! ds
              ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
               title author year isbn]
              {:return-keys true :builder-fn rs/as-unqualified-maps})]
    (get-book ds (or (:id row) (val (first row))))))

(defn update-book!
  "Update the book with the given id. Returns the updated row, or nil if absent."
  [ds id {:keys [title author year isbn]}]
  (when (get-book ds id)
    (jdbc/execute-one! ds
      ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
       title author year isbn id])
    (get-book ds id)))

(defn delete-book!
  "Delete the book with the given id. Returns true if a row was removed."
  [ds id]
  (let [result (jdbc/execute-one! ds
                 ["DELETE FROM books WHERE id = ?" id])]
    (pos? (or (:next.jdbc/update-count result) 0))))
