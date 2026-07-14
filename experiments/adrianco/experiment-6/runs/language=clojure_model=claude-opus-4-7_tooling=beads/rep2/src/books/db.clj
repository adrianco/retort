(ns books.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.sql :as sql]
            [next.jdbc.result-set :as rs]))

(def default-db-spec
  {:dbtype "sqlite" :dbname "books.db"})

(defonce ^:dynamic *db* (atom nil))

(defn datasource
  [db-spec]
  (jdbc/get-datasource db-spec))

(defn init!
  "Initialize the database connection and create the schema."
  ([] (init! default-db-spec))
  ([db-spec]
   (let [ds (datasource db-spec)]
     (reset! *db* ds)
     (jdbc/execute!
      ds
      ["CREATE TABLE IF NOT EXISTS books (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          author TEXT NOT NULL,
          year INTEGER,
          isbn TEXT
        )"])
     ds)))

(defn clear!
  "Remove all rows. Used for tests."
  [ds]
  (jdbc/execute! ds ["DELETE FROM books"]))

(def ^:private opts
  {:builder-fn rs/as-unqualified-lower-maps})

(defn create-book
  [ds {:keys [title author year isbn]}]
  (let [result (sql/insert! ds :books
                            {:title title
                             :author author
                             :year year
                             :isbn isbn}
                            opts)]
    (sql/get-by-id ds :books (or (:id result) (get result (keyword "last_insert_rowid()"))) opts)))

(defn list-books
  ([ds] (list-books ds nil))
  ([ds author]
   (if (and author (not (clojure.string/blank? author)))
     (sql/query ds ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
     (sql/query ds ["SELECT * FROM books ORDER BY id"] opts))))

(defn get-book
  [ds id]
  (sql/get-by-id ds :books id opts))

(defn update-book
  [ds id {:keys [title author year isbn]}]
  (let [existing (get-book ds id)]
    (when existing
      (sql/update! ds :books
                   {:title title
                    :author author
                    :year year
                    :isbn isbn}
                   {:id id})
      (get-book ds id))))

(defn delete-book
  [ds id]
  (let [result (sql/delete! ds :books {:id id})]
    (pos? (or (:next.jdbc/update-count result) 0))))
