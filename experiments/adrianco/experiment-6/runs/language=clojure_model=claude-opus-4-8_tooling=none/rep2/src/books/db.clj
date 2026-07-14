(ns books.db
  "SQLite-backed persistence for the book collection."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(defn make-datasource
  "Create a next.jdbc datasource backed by a SQLite file at `db-path`.

   Note: we use the {:dbtype \"sqlite\" :dbname ...} spec rather than a raw
   {:jdbcUrl ...} — with the xerial sqlite-jdbc driver the latter yields a
   per-connection in-memory database (data is never written to the file and is
   invisible to other connections/threads), which breaks under a threaded
   server."
  [db-path]
  (jdbc/get-datasource {:dbtype "sqlite" :dbname db-path}))

(defn init-schema!
  "Create the books table if it does not already exist."
  [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        title  TEXT NOT NULL,
        author TEXT NOT NULL,
        year   INTEGER,
        isbn   TEXT)"]))

(def ^:private opts
  "Return rows as plain maps with unqualified, lowercase keys."
  {:builder-fn rs/as-unqualified-lower-maps})

(defn create-book!
  "Insert a book and return the full created row (including generated id)."
  [ds {:keys [title author year isbn]}]
  (let [row (jdbc/execute-one! ds
              ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
               title author year isbn]
              {:return-keys true})
        id (or (:last_insert_rowid row)
               (val (first row)))]
    (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts)))

(defn list-books
  "List all books, optionally filtered by author (exact match)."
  [ds author]
  (if (seq author)
    (jdbc/execute! ds ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
    (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts)))

(defn get-book
  "Fetch a single book by id, or nil if not found."
  [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

(defn update-book!
  "Update a book by id. Returns the updated row, or nil if the id was not found."
  [ds id {:keys [title author year isbn]}]
  (when (get-book ds id)
    (jdbc/execute-one! ds
      ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
       title author year isbn id])
    (get-book ds id)))

(defn delete-book!
  "Delete a book by id. Returns true if a row was deleted, false otherwise."
  [ds id]
  (let [result (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id])]
    (pos? (or (:next.jdbc/update-count result) 0))))
