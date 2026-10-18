(ns books.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(def ^:private opts {:builder-fn rs/as-unqualified-maps})

(defn open
  "Opens (creating if needed) a SQLite database at `path` and ensures the schema exists."
  [path]
  (let [ds (jdbc/get-datasource {:jdbcUrl (str "jdbc:sqlite:" path)})]
    (jdbc/execute! ds ["CREATE TABLE IF NOT EXISTS books (
                          id     INTEGER PRIMARY KEY AUTOINCREMENT,
                          title  TEXT NOT NULL,
                          author TEXT NOT NULL,
                          year   INTEGER,
                          isbn   TEXT)"])
    ds))

(defn list-books
  "Returns all books, optionally restricted to an exact author match."
  [ds author]
  (if author
    (jdbc/execute! ds ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
    (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts)))

(defn get-book
  [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

(defn create-book!
  [ds {:keys [title author year isbn]}]
  (jdbc/with-transaction [tx ds]
    (jdbc/execute! tx ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
                       title author year isbn])
    (jdbc/execute-one! tx ["SELECT * FROM books WHERE id = last_insert_rowid()"] opts)))

(defn update-book!
  "Replaces the book's fields. Returns the updated book, or nil if no such id."
  [ds id {:keys [title author year isbn]}]
  (jdbc/with-transaction [tx ds]
    (let [n (:next.jdbc/update-count
             (jdbc/execute-one! tx ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
                                    title author year isbn id]))]
      (when (pos? n)
        (get-book tx id)))))

(defn delete-book!
  "Deletes the book. Returns true if a row was removed."
  [ds id]
  (pos? (:next.jdbc/update-count
         (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id]))))
