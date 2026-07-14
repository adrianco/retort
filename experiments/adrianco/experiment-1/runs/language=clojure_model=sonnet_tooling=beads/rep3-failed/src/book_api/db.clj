(ns book-api.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(def db-spec {:dbtype "sqlite" :dbname "books.db"})

(def datasource (jdbc/get-datasource db-spec))

(defn init-db! []
  (jdbc/execute! datasource
    ["CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT,
        created_at TEXT DEFAULT (datetime('now'))
      )"]))

(defn create-book! [title author year isbn]
  (jdbc/execute! datasource
    ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
     title author year isbn])
  (jdbc/execute-one! datasource
    ["SELECT * FROM books WHERE id = last_insert_rowid()"]
    {:builder-fn rs/as-unqualified-maps}))

(defn list-books
  ([] (list-books nil))
  ([author]
   (if (seq author)
     (jdbc/execute! datasource
       ["SELECT * FROM books WHERE author LIKE ?" (str "%" author "%")]
       {:builder-fn rs/as-unqualified-maps})
     (jdbc/execute! datasource
       ["SELECT * FROM books"]
       {:builder-fn rs/as-unqualified-maps}))))

(defn get-book [id]
  (jdbc/execute-one! datasource
    ["SELECT * FROM books WHERE id = ?" id]
    {:builder-fn rs/as-unqualified-maps}))

(defn update-book! [id title author year isbn]
  (let [fields [["title" title] ["author" author] ["year" year] ["isbn" isbn]]
        updates (keep (fn [[f v]] (when (some? v) (str f " = ?"))) fields)
        values (keep (fn [[_ v]] (when (some? v) v)) fields)]
    (when (seq updates)
      (jdbc/execute! datasource
        (into [(str "UPDATE books SET "
                    (clojure.string/join ", " updates)
                    " WHERE id = ?")]
              (conj (vec values) id))))
    (get-book id)))

(defn delete-book! [id]
  (jdbc/execute! datasource
    ["DELETE FROM books WHERE id = ?" id]))
