(ns books.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]
            [next.jdbc.sql :as sql]))

(defn ds
  "Build a JDBC datasource for a SQLite file."
  [db-file]
  (jdbc/get-datasource {:dbtype "sqlite" :dbname db-file}))

(defn init-schema!
  "Create the books table if it doesn't exist."
  [datasource]
  (jdbc/execute!
   datasource
   ["CREATE TABLE IF NOT EXISTS books (
       id     INTEGER PRIMARY KEY AUTOINCREMENT,
       title  TEXT NOT NULL,
       author TEXT NOT NULL,
       year   INTEGER,
       isbn   TEXT
     )"]))

(def ^:private opts
  {:builder-fn rs/as-unqualified-lower-maps})

(defn list-books
  ([datasource]
   (sql/query datasource
              ["SELECT id, title, author, year, isbn FROM books ORDER BY id"]
              opts))
  ([datasource author]
   (sql/query datasource
              ["SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id" author]
              opts)))

(defn get-book [datasource id]
  (first (sql/query datasource
                    ["SELECT id, title, author, year, isbn FROM books WHERE id = ?" id]
                    opts)))

(defn- generated-id [insert-result]
  (or (:id insert-result)
      (get insert-result (keyword "last_insert_rowid()"))
      (some (fn [[k v]]
              (when (re-find #"(?i)rowid|generated" (name k)) v))
            insert-result)))

(defn insert-book! [datasource {:keys [title author year isbn]}]
  (let [result (sql/insert! datasource :books
                            {:title title :author author :year year :isbn isbn})
        id     (generated-id result)]
    (when id (get-book datasource id))))

(defn update-book! [datasource id {:keys [title author year isbn]}]
  (let [result (sql/update! datasource :books
                            {:title title :author author :year year :isbn isbn}
                            {:id id})
        n      (:next.jdbc/update-count result)]
    (when (and n (pos? n))
      (get-book datasource id))))

(defn delete-book! [datasource id]
  (let [result (sql/delete! datasource :books {:id id})
        n      (:next.jdbc/update-count result)]
    (boolean (and n (pos? n)))))

(defn reset!
  "Drop and recreate the table (used by tests)."
  [datasource]
  (jdbc/execute! datasource ["DROP TABLE IF EXISTS books"])
  (init-schema! datasource))
