(ns books.db
  "SQLite-backed persistence for the book collection."
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(defn make-datasource
  "Create a connectable for the given SQLite file (or \":memory:\").

   A `:memory:` database lives only as long as its connection, so we hold a
   single connection open for it (handy for tests). File-backed databases use
   a plain datasource that opens a connection per operation."
  [db-file]
  (let [ds (jdbc/get-datasource {:dbtype "sqlite" :dbname db-file})]
    (if (= db-file ":memory:")
      (jdbc/get-connection ds)
      ds)))

(defn init-schema!
  "Create the books table if it does not already exist."
  [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        title   TEXT NOT NULL,
        author  TEXT NOT NULL,
        year    INTEGER,
        isbn    TEXT)"]))

(def ^:private opts
  ;; Return unqualified, kebab-cased keys so JSON output is clean.
  {:builder-fn rs/as-unqualified-lower-maps})

(defn create-book!
  "Insert a book and return the full inserted row."
  [ds {:keys [title author year isbn]}]
  (let [result (jdbc/execute-one! ds
                 ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
                  title author year isbn]
                 {:return-keys true})
        id (or (:last_insert_rowid result)
               (val (first result)))]
    (jdbc/execute-one! ds
      ["SELECT * FROM books WHERE id = ?" id]
      opts)))

(defn list-books
  "List all books, optionally filtered by exact author match."
  ([ds] (list-books ds nil))
  ([ds author]
   (if (some? author)
     (jdbc/execute! ds ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
     (jdbc/execute! ds ["SELECT * FROM books ORDER BY id"] opts))))

(defn get-book
  "Fetch a single book by id, or nil if not found."
  [ds id]
  (jdbc/execute-one! ds ["SELECT * FROM books WHERE id = ?" id] opts))

(defn update-book!
  "Update an existing book. Returns the updated row, or nil if it does not exist."
  [ds id {:keys [title author year isbn]}]
  (let [result (jdbc/execute-one! ds
                 ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
                  title author year isbn id])]
    (when (pos? (::jdbc/update-count result))
      (get-book ds id))))

(defn delete-book!
  "Delete a book by id. Returns true if a row was deleted."
  [ds id]
  (let [result (jdbc/execute-one! ds ["DELETE FROM books WHERE id = ?" id])]
    (pos? (::jdbc/update-count result))))
