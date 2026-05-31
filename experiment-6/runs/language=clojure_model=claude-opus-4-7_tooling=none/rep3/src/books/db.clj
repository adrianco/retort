(ns books.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.sql :as sql]
            [next.jdbc.result-set :as rs]))

(def default-spec
  {:dbtype "sqlite" :dbname "books.db"})

(defn make-datasource [spec]
  (jdbc/get-datasource spec))

(defn init-schema! [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        title  TEXT    NOT NULL,
        author TEXT    NOT NULL,
        year   INTEGER,
        isbn   TEXT)"]))

(def ^:private opts
  {:builder-fn rs/as-unqualified-lower-maps})

(defn list-books [ds {:keys [author]}]
  (if author
    (sql/query ds ["SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id" author] opts)
    (sql/query ds ["SELECT id, title, author, year, isbn FROM books ORDER BY id"] opts)))

(defn get-book [ds id]
  (first (sql/query ds ["SELECT id, title, author, year, isbn FROM books WHERE id = ?" id] opts)))

(defn create-book! [ds {:keys [title author year isbn]}]
  (let [result (sql/insert! ds :books
                            {:title title :author author :year year :isbn isbn}
                            opts)
        id (or (:id result)
               (get result (keyword "last_insert_rowid()"))
               (-> result vals first))]
    (get-book ds id)))

(defn update-book! [ds id {:keys [title author year isbn]}]
  (let [res (sql/update! ds :books
                         {:title title :author author :year year :isbn isbn}
                         {:id id})]
    (when (pos? (:next.jdbc/update-count res))
      (get-book ds id))))

(defn delete-book! [ds id]
  (let [res (sql/delete! ds :books {:id id})]
    (pos? (:next.jdbc/update-count res))))
