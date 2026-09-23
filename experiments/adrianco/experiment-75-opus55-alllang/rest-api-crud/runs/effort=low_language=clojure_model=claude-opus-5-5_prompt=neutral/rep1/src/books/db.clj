(ns books.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]
            [next.jdbc.sql :as sql]))

(def opts {:builder-fn rs/as-unqualified-lower-maps})

(defn make-ds [path]
  (let [ds (jdbc/get-datasource {:dbtype "sqlite" :dbname path})]
    (jdbc/execute! ds ["CREATE TABLE IF NOT EXISTS books (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         title TEXT NOT NULL, author TEXT NOT NULL,
                         year INTEGER, isbn TEXT)"])
    ds))

(defn list-books [ds author]
  (if author
    (sql/query ds ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
    (sql/query ds ["SELECT * FROM books ORDER BY id"] opts)))

(defn get-book [ds id]
  (sql/get-by-id ds :books id opts))

(defn create-book! [ds book]
  (let [r (sql/insert! ds :books book opts)
        id (or (:id r) (val (first r)))]
    (get-book ds id)))

(defn update-book! [ds id book]
  (when (pos? (::jdbc/update-count (sql/update! ds :books book {:id id})))
    (get-book ds id)))

(defn delete-book! [ds id]
  (pos? (::jdbc/update-count (sql/delete! ds :books {:id id}))))
