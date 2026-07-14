(ns books.db
  "SQLite-backed persistence for the book collection."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(defn db-spec
  "Build a JDBC datasource spec for the given SQLite file path.
   Use \":memory:\" for an in-memory database."
  [path]
  {:jdbcType "sqlite"
   :dbtype   "sqlite"
   :dbname   path})

(defn make-datasource
  "Open a single long-lived JDBC connection to the SQLite database at `path`.

   A single connection is used (rather than a per-query datasource) so that an
   in-memory database (\":memory:\") survives across calls — it would otherwise
   be discarded as soon as its only connection closed."
  [path]
  (jdbc/get-connection (jdbc/get-datasource (db-spec path))))

(defn init-schema!
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

(def ^:private opts
  "Return column names unqualified (e.g. :title rather than :books/title)."
  {:builder-fn rs/as-unqualified-maps})

(defn insert-book!
  "Insert a book map and return the freshly created row."
  [ds {:keys [title author year isbn]}]
  (let [row (jdbc/execute-one! ds
              ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
               title author year isbn]
              {:return-keys true})
        id  (or (:books/id row) (val (first row)))]
    (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts)))

(defn list-books
  "Return all books, optionally filtered by author (exact match)."
  ([ds] (list-books ds nil))
  ([ds author]
   (if (seq author)
     (jdbc/execute! ds ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
     (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts))))

(defn get-book
  "Return the book with the given id, or nil if not found."
  [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

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
  (let [res (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id])]
    (pos? (or (:next.jdbc/update-count res) 0))))
