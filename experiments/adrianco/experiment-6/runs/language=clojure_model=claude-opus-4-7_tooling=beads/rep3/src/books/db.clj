(ns books.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]
            [next.jdbc.sql :as sql]))

(defn make-datasource
  "Create a JDBC datasource for SQLite. Pass a file path or \":memory:\"."
  [db-path]
  (jdbc/get-datasource {:dbtype "sqlite" :dbname db-path}))

(defn init-schema!
  "Create the books table if it does not already exist."
  [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )"]))

(def ^:private opts
  {:builder-fn rs/as-unqualified-lower-maps})

(declare get-book)

(defn- last-insert-id [insert-result]
  (or (:id insert-result)
      (get insert-result (keyword "last_insert_rowid()"))
      (some (fn [[k v]]
              (when (and (keyword? k)
                         (.contains (name k) "rowid"))
                v))
            insert-result)))

(defn create-book!
  "Insert a book row. Returns the created row including the new id."
  [ds book]
  (let [row (select-keys book [:title :author :year :isbn])
        result (sql/insert! ds :books row opts)
        id (last-insert-id result)]
    (get-book ds id)))

(defn list-books
  "List all books, optionally filtered by author (case-insensitive equality)."
  ([ds]
   (sql/query ds ["SELECT id, title, author, year, isbn FROM books ORDER BY id"] opts))
  ([ds author]
   (if (some? author)
     (sql/query ds
                ["SELECT id, title, author, year, isbn FROM books
                  WHERE lower(author) = lower(?) ORDER BY id" author]
                opts)
     (list-books ds))))

(defn get-book
  "Fetch a single book by id, or nil if not found."
  [ds id]
  (first (sql/query ds
                    ["SELECT id, title, author, year, isbn FROM books WHERE id = ?" id]
                    opts)))

(defn update-book!
  "Update an existing book. Returns the updated row, or nil if id not found."
  [ds id book]
  (let [row (select-keys book [:title :author :year :isbn])
        result (sql/update! ds :books row {:id id})]
    (when (pos? (or (:next.jdbc/update-count result) 0))
      (get-book ds id))))

(defn delete-book!
  "Delete a book by id. Returns true if a row was deleted."
  [ds id]
  (let [result (sql/delete! ds :books {:id id})]
    (pos? (or (:next.jdbc/update-count result) 0))))
