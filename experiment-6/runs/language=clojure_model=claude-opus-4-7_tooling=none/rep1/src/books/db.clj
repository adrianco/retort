(ns books.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]))

(defn create-datasource [db-spec]
  (jdbc/get-datasource db-spec))

(defn init-db! [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT)"]))

(def ^:private opts {:builder-fn rs/as-unqualified-lower-maps})

(defn list-books
  ([ds] (list-books ds nil))
  ([ds author]
   (if author
     (jdbc/execute! ds ["SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id" author] opts)
     (jdbc/execute! ds ["SELECT id, title, author, year, isbn FROM books ORDER BY id"] opts))))

(defn get-book [ds id]
  (jdbc/execute-one! ds
    ["SELECT id, title, author, year, isbn FROM books WHERE id = ?" id]
    opts))

(defn create-book! [ds {:keys [title author year isbn]}]
  (jdbc/with-transaction [tx ds]
    (jdbc/execute! tx
      ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
       title author year isbn])
    (let [{:keys [id]} (jdbc/execute-one! tx
                         ["SELECT last_insert_rowid() AS id"]
                         opts)]
      (get-book tx id))))

(defn update-book! [ds id {:keys [title author year isbn]}]
  (let [result (jdbc/execute-one! ds
                 ["UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
                  title author year isbn id])]
    (pos? (:next.jdbc/update-count result))))

(defn delete-book! [ds id]
  (let [result (jdbc/execute-one! ds
                 ["DELETE FROM books WHERE id = ?" id])]
    (pos? (:next.jdbc/update-count result))))
