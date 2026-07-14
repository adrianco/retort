(ns book-api.db
  (:require [clojure.java.jdbc :as jdbc]))

(def db-spec {:subprotocol "sqlite"
              :subname "books.db"})

(defn init-db!
  "Create the books table if it does not exist."
  []
  (jdbc/db-do-commands db-spec
    "CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT UNIQUE
    )"))

(defn get-books
  "Return all books, optionally filtered by author."
  ([]
   (get-books nil))
  ([author]
   (if author
     (jdbc/query db-spec
       ["SELECT * FROM books WHERE author = ?" author])
     (jdbc/query db-spec ["SELECT * FROM books"]))))

(defn get-book-by-id
  "Return a single book by ID, or nil."
  [id]
  (first (jdbc/query db-spec
    ["SELECT * FROM books WHERE id = ?" id])))

(defn insert-book
  "Insert a new book and return the created row with id."
  [title author year isbn]
  (let [year-int (when (and year (not= year "")) (Integer/parseInt (str year)))
        isbn-val (when (and isbn (not= isbn "")) isbn)
        result (jdbc/insert! db-spec :books
                  {:title title
                   :author author
                   :year year-int
                   :isbn isbn-val})]
    (let [book-id (if (map? result)
                    (or (:id result) (:last_insert_rowid result))
                    result)]
      (get-book-by-id book-id))))

(defn update-book!
  "Update an existing book by ID. Returns the updated row, or nil if not found."
  [id updates]
  (let [current (get-book-by-id id)]
    (when current
      (let [new-data (reduce
                       (fn [acc [k v]]
                         (if (or (nil? v) (= v ""))
                           acc
                           (assoc acc k (if (= k :year)
                                         (Integer/parseInt (str v))
                                         v)))
                       {})
                       updates)
            _ (jdbc/update! db-spec :books new-data ["id = ?" id])]
        (get-book-by-id id)))))

(defn delete-book!
  "Delete a book by ID. Returns true if a row was deleted."
  [id]
  (let [rows (jdbc/delete! db-spec ["id = ?" id])]
    (pos? rows)))
