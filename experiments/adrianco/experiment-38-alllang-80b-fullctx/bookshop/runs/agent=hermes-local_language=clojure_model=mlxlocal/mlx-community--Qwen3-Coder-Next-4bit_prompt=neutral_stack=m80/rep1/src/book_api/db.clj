(ns book-api.db
  (:require [hugsql.core :as hugsql]
            [clojure.java.jdbc :as jdbc]))

(hugsql/def-db-fns "db.sql")

(defn db []
  {:classname "org.sqlite.JDBC"
   :subprotocol "sqlite"
   :subname "books.db"
   :create-if-missing true})

(defn init-db []
  (jdbc/db-create-table
    (db)
    :books
    [:id "INTEGER PRIMARY KEY AUTOINCREMENT"
     :title "TEXT NOT NULL"
     :author "TEXT NOT NULL"
     :year "INTEGER"
     :isbn "TEXT UNIQUE"])
  :db-initialized)

(defn create-book [book]
  (create-book! book))

(defn get-book [id]
  (get-book-by-id {:id id}))

(defn get-books [& {:keys [author] :as opts}]
  (get-books opts))

(defn update-book [id book]
  (update-book! (assoc book :id id)))

(defn delete-book [id]
  (delete-book! {:id id}))

(defn book-exists? [id]
  (book-exists? {:id id}))
