(ns book-api.db
  (:require [clojure.java.jdbc :as jdbc]))

(def db-spec
  {:classname "org.sqlite.JDBC"
   :subprotocol "sqlite"
   :subname "books.db"
   :create-if-missing true})

(defn init-db []
  (jdbc/db-do-commands
    db-spec
    (jdbc/create-table-ddl :books
                           [:id "INTEGER PRIMARY KEY AUTOINCREMENT"
                            :title "TEXT NOT NULL"
                            :author "TEXT NOT NULL"
                            :year "INTEGER"
                            :isbn "TEXT UNIQUE"]))
  :db-initialized)

(defn create-book [book]
  (jdbc/insert! db-spec :books book {:returning [:id]}))

(defn get-book [id]
  (first (jdbc/query db-spec ["SELECT * FROM books WHERE id = ?" id] {:row-fn :book})))

(defn get-books [& {:keys [author] :as opts}]
  (if author
    (jdbc/query db-spec ["SELECT * FROM books WHERE author = ?" author])
    (jdbc/query db-spec ["SELECT * FROM books"])))

(defn update-book [id book]
  (jdbc/update! db-spec :books book [:id id]))

(defn delete-book [id]
  (jdbc/delete! db-spec :books [:id id]))

(defn book-exists? [id]
  (not (nil? (get-book id))))
