(ns books.db
  (:refer-clojure :exclude [reset!])
  (:require [next.jdbc :as jdbc]
            [next.jdbc.sql :as sql]
            [next.jdbc.result-set :as rs]))

(defn make-datasource
  "Build a SQLite datasource. Pass \":memory:\" for an in-memory DB."
  [db-path]
  (jdbc/get-datasource {:dbtype "sqlite" :dbname db-path}))

(def ^:private opts {:builder-fn rs/as-unqualified-lower-maps})

(defn init-schema! [ds]
  (jdbc/execute! ds
    ["CREATE TABLE IF NOT EXISTS books (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        title   TEXT NOT NULL,
        author  TEXT NOT NULL,
        year    INTEGER,
        isbn    TEXT
      )"]))

(defn reset! [ds]
  (jdbc/execute! ds ["DROP TABLE IF EXISTS books"])
  (init-schema! ds))

(defn create-book! [ds {:keys [title author year isbn]}]
  (let [result (sql/insert! ds :books
                            {:title title
                             :author author
                             :year year
                             :isbn isbn}
                            opts)
        id (or (:id result) (get result (keyword "last_insert_rowid()")))]
    (sql/get-by-id ds :books id :id opts)))

(defn list-books
  ([ds] (sql/query ds ["SELECT * FROM books ORDER BY id"] opts))
  ([ds {:keys [author]}]
   (if (and author (seq author))
     (sql/query ds ["SELECT * FROM books WHERE author = ? ORDER BY id" author] opts)
     (list-books ds))))

(defn get-book [ds id]
  (sql/get-by-id ds :books id :id opts))

(defn update-book! [ds id {:keys [title author year isbn]}]
  (let [existing (get-book ds id)]
    (when existing
      (sql/update! ds :books
                   (cond-> {}
                     (some? title)  (assoc :title title)
                     (some? author) (assoc :author author)
                     (some? year)   (assoc :year year)
                     (some? isbn)   (assoc :isbn isbn))
                   {:id id})
      (get-book ds id))))

(defn delete-book! [ds id]
  (let [result (sql/delete! ds :books {:id id})]
    (pos? (first (vals (first (if (sequential? result) result [result])))))))
