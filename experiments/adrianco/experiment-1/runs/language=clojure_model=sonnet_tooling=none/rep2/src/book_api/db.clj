(ns book-api.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(def db-spec {:dbtype "sqlite" :dbname "books.db"})

(defonce ds (atom nil))

(defn get-ds []
  (when-not @ds
    (reset! ds (jdbc/get-datasource db-spec)))
  @ds)

(defn init-db! []
  (jdbc/execute! (get-ds)
    ["CREATE TABLE IF NOT EXISTS books (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        title      TEXT    NOT NULL,
        author     TEXT    NOT NULL,
        year       INTEGER,
        isbn       TEXT
      )"]))

(defn create-book! [book]
  (jdbc/with-transaction [tx (get-ds)]
    (jdbc/execute! tx
      ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
       (:title book) (:author book) (:year book) (:isbn book)])
    (jdbc/execute-one! tx
      ["SELECT * FROM books WHERE id = last_insert_rowid()"]
      {:builder-fn rs/as-unqualified-lower-maps})))

(defn get-books
  ([] (get-books nil))
  ([author-filter]
   (if (seq author-filter)
     (jdbc/execute! (get-ds)
       ["SELECT * FROM books WHERE author LIKE ?" (str "%" author-filter "%")]
       {:builder-fn rs/as-unqualified-lower-maps})
     (jdbc/execute! (get-ds)
       ["SELECT * FROM books"]
       {:builder-fn rs/as-unqualified-lower-maps}))))

(defn get-book [id]
  (jdbc/execute-one! (get-ds)
    ["SELECT * FROM books WHERE id = ?" id]
    {:builder-fn rs/as-unqualified-lower-maps}))

(defn update-book! [id book]
  (let [rows-affected (first (jdbc/execute! (get-ds)
                               ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
                                (:title book) (:author book) (:year book) (:isbn book) id]
                               {:return-keys false}))]
    (when (pos? (get rows-affected :next.jdbc/update-count 0))
      (get-book id))))

(defn delete-book! [id]
  (first (jdbc/execute! (get-ds)
           ["DELETE FROM books WHERE id = ?" id])))
