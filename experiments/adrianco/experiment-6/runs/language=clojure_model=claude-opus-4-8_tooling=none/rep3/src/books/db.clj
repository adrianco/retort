(ns books.db
  "SQLite persistence layer for the book collection."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(defn datasource
  "Build a next.jdbc datasource for the given SQLite path (use \":memory:\" for tests)."
  [db-path]
  (jdbc/get-datasource {:dbtype "sqlite" :dbname db-path}))

(defn init-db!
  "Create the books table if it does not already exist."
  [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        title  TEXT NOT NULL,
        author TEXT NOT NULL,
        year   INTEGER,
        isbn   TEXT
      )"]))

;; Return maps with unqualified, lower-case keys (e.g. :id, :title).
(def ^:private opts {:builder-fn rs/as-unqualified-lower-maps})

(defn list-books
  "Return all books, optionally filtered by author."
  [ds author]
  (if (some? author)
    (jdbc/execute! ds ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
    (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts)))

(defn get-book
  "Return a single book by id, or nil."
  [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

(defn create-book!
  "Insert a book and return the persisted row."
  [ds {:keys [title author year isbn]}]
  (let [result (jdbc/execute-one! ds
                 ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
                  title author year isbn]
                 {:return-keys true :builder-fn rs/as-unqualified-lower-maps})
        ;; SQLite returns the generated key under a driver-specific column name
        ;; (e.g. "last_insert_rowid()"), so fall back to the single returned value.
        id     (or (:id result) (val (first result)))]
    (get-book ds id)))

(defn update-book!
  "Update an existing book; returns the updated row, or nil if it does not exist."
  [ds id {:keys [title author year isbn]}]
  (let [{:keys [next.jdbc/update-count]}
        (jdbc/execute-one! ds
          ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
           title author year isbn id])]
    (when (pos? (or update-count 0))
      (get-book ds id))))

(defn delete-book!
  "Delete a book by id; returns true if a row was removed."
  [ds id]
  (let [{:keys [next.jdbc/update-count]}
        (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id])]
    (pos? (or update-count 0))))
