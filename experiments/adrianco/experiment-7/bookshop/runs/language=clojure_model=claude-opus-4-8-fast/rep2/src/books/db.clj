(ns books.db
  "SQLite-backed persistence for the book collection."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.connection :as connection]
            [next.jdbc.result-set :as rs])
  (:import [com.zaxxer.hikari HikariDataSource]))

(defn datasource
  "Build a pooled next.jdbc datasource for the given SQLite database path.

  A connection pool is used so that, for in-memory databases, at least one
  connection stays open and the shared in-memory database survives between
  calls. Pass \":memory:\" for a private in-memory database (handy in tests);
  each call gets its own isolated in-memory database."
  [db-path]
  (let [dbname (if (= db-path ":memory:")
                 ;; A uniquely-named, shared-cache in-memory DB kept alive by the pool.
                 (str "file:mem_" (System/nanoTime) "?mode=memory&cache=shared")
                 db-path)]
    (connection/->pool HikariDataSource
      {:dbtype "sqlite" :dbname dbname})))

(defn init!
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
  "Return unqualified, lower-cased column names as plain maps."
  {:builder-fn rs/as-unqualified-lower-maps})

(defn create-book!
  "Insert a book and return the newly created row."
  [ds {:keys [title author year isbn]}]
  (jdbc/execute-one! ds
    ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
     title author year isbn]
    {:return-keys true})
  ;; SQLite's generated-keys support varies; fetch the most recent row reliably.
  (jdbc/execute-one! ds
    ["SELECT * FROM books WHERE id = last_insert_rowid()"]
    opts))

(defn list-books
  "Return all books, optionally filtered by author (case-insensitive)."
  [ds author]
  (if (and author (seq author))
    (jdbc/execute! ds
      ["SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id" author]
      opts)
    (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts)))

(defn get-book
  "Return a single book by id, or nil if not found."
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
  (let [result (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id])]
    (pos? (:next.jdbc/update-count result))))
