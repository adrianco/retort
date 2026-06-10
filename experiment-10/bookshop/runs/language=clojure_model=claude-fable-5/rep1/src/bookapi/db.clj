(ns bookapi.db
  "SQLite persistence layer for books."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(def ^:private query-opts
  {:builder-fn rs/as-unqualified-lower-maps})

(defn make-datasource
  "Create a datasource backed by the SQLite file at db-path."
  [db-path]
  (jdbc/get-datasource {:dbtype "sqlite" :dbname db-path}))

(defn init!
  "Create the books table if it does not exist."
  [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        title  TEXT NOT NULL,
        author TEXT NOT NULL,
        year   INTEGER,
        isbn   TEXT)"]))

(defn get-book [ds id]
  (jdbc/execute-one! ds
    ["SELECT id, title, author, year, isbn FROM books WHERE id = ?" id]
    query-opts))

(defn list-books
  "List all books, optionally filtered by exact author match."
  [ds {:keys [author]}]
  (if author
    (jdbc/execute! ds
      ["SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id" author]
      query-opts)
    (jdbc/execute! ds
      ["SELECT id, title, author, year, isbn FROM books ORDER BY id"]
      query-opts)))

(defn create-book! [ds {:keys [title author year isbn]}]
  (let [result (jdbc/execute-one! ds
                 ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
                  title author year isbn]
                 {:return-keys true})
        id (first (vals result))]
    (get-book ds id)))

(defn update-book!
  "Update the book with the given id. Returns the updated book or nil if not found."
  [ds id {:keys [title author year isbn]}]
  (let [{:keys [next.jdbc/update-count]}
        (jdbc/execute-one! ds
          ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
           title author year isbn id])]
    (when (pos? update-count)
      (get-book ds id))))

(defn delete-book!
  "Delete the book with the given id. Returns true if a row was deleted."
  [ds id]
  (let [{:keys [next.jdbc/update-count]}
        (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id])]
    (pos? update-count)))
