(ns book-api.db
  (:require [clojure.java.jdbc :as jdbc]
            [clojure.string :as str]))

(defn db-spec [path]
  {:connection-uri (str "jdbc:sqlite:" path)})

(defn initialize! [db]
  (jdbc/db-do-commands db
    "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)"))

(defn list-books [db author]
  (if (and author (not-empty author))
    (jdbc/query db ["SELECT * FROM books WHERE LOWER(author) = LOWER(?) ORDER BY id" author])
    (jdbc/query db ["SELECT * FROM books ORDER BY id"])))

(defn find-book [db id]
  (first (jdbc/query db ["SELECT * FROM books WHERE id = ?" id])))

(defn create-book! [db book]
  (let [values (select-keys book [:title :author :year :isbn])
        columns (map name (keys values))
        sql (str "INSERT INTO books (" (str/join ", " columns) ") VALUES ("
                 (str/join ", " (repeat (count columns) "?")) ")")]
    (jdbc/with-db-connection [conn db]
      (let [id (jdbc/with-db-transaction [tx conn]
                 (jdbc/execute! tx (into [sql] (mapv values (keys values))))
                 (jdbc/query tx ["SELECT last_insert_rowid() AS id"] {:result-set-fn (comp :id first)}))]
        (find-book conn id)))))

(defn update-book! [db id book]
  (let [fields (select-keys book [:title :author :year :isbn])]
    (when (seq fields)
      (let [columns (map name (keys fields))
            assignments (str/join ", " (map #(str % " = ?") columns))]
        (jdbc/execute! db (into [(str "UPDATE books SET " assignments " WHERE id = ?")]
                                (conj (mapv fields (keys fields)) id)))))
    (find-book db id)))

(defn delete-book! [db id]
  (pos? (first (jdbc/execute! db ["DELETE FROM books WHERE id = ?" id]))))
