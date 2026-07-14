(ns bookapi.db
  (:require [next.jdbc :as jdbc]
            [next.jdbc.result-set :as rs]
            [next.jdbc.sql :as sql]))

(def ^:private opts {:builder-fn rs/as-unqualified-lower-maps})

(defn make-datasource [db-path]
  (jdbc/get-datasource {:dbtype "sqlite" :dbname db-path}))

(defn init! [ds]
  (jdbc/execute! ds ["CREATE TABLE IF NOT EXISTS books (
                        id     INTEGER PRIMARY KEY AUTOINCREMENT,
                        title  TEXT NOT NULL,
                        author TEXT NOT NULL,
                        year   INTEGER,
                        isbn   TEXT)"]))

(defn get-book [ds id]
  (sql/get-by-id ds :books id opts))

(defn create-book! [ds {:keys [title author year isbn]}]
  (let [res (sql/insert! ds :books
                         {:title title :author author :year year :isbn isbn}
                         opts)
        id  (-> res vals first)]
    (get-book ds id)))

(defn list-books [ds author]
  (if author
    (sql/find-by-keys ds :books {:author author} (assoc opts :order-by [:id]))
    (sql/query ds ["SELECT * FROM books ORDER BY id"] opts)))

(defn update-book! [ds id {:keys [title author year isbn]}]
  (let [res (sql/update! ds :books
                         {:title title :author author :year year :isbn isbn}
                         {:id id})]
    (when (pos? (:next.jdbc/update-count res))
      (get-book ds id))))

(defn delete-book! [ds id]
  (pos? (:next.jdbc/update-count (sql/delete! ds :books {:id id}))))
