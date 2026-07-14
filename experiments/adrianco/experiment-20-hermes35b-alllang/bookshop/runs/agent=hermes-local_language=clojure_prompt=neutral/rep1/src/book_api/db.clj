(ns book-api.db
  (:require [next.jdbc :as jdbc]
            [clojure.string :as string]))

(def db-spec {:dbtype "sqlite"
              :dbname "books.db"})

(defn- get-conn []
  (jdbc/get-datasource db-spec))

(defn init-db! []
  (jdbc/execute! (get-conn)
                 ["CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                  )"]))

(defn add-book! [{:keys [title author year isbn]}]
  (jdbc/execute! (get-conn)
                 ["INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
                  title author year isbn]
                 {:return-keys true}))

(defn list-books [{:keys [author]}]
  (if author
    (jdbc/execute! (get-conn)
                   ["SELECT * FROM books WHERE author = ?" author])
    (jdbc/execute! (get-conn)
                   ["SELECT * FROM books"])))

(defn get-book! [id]
  (first (jdbc/execute! (get-conn)
                        ["SELECT * FROM books WHERE id = ?" id])))

(defn update-book! [id data]
  (let [book (get-book! id)]
    (when-not book
      (throw (RuntimeException. (str "Book with id " id " not found"))))
    (let [fields (dissoc data :id)]
      (when (seq fields)
        (let [set-clause (string/join ", " (map (fn [[k _v]]
                                                  (str (name k) " = ?"))
                                               fields))
              params (into [(str "WHERE id = " id)]
                           (vals fields))]
          (jdbc/execute! (get-conn)
                         (into ["UPDATE books SET" set-clause] params)))))
    (get-book! id)))

(defn delete-book! [id]
  (let [book (get-book! id)]
    (when-not book
      (throw (RuntimeException. (str "Book with id " id " not found"))))
    (jdbc/execute! (get-conn)
                   ["DELETE FROM books WHERE id = ?" id])
    book))

(defn clear-db! []
  (jdbc/execute! (get-conn)
                 ["DELETE FROM books"]))

(defn reset-db! []
  (jdbc/execute! (get-conn)
                 ["DROP TABLE IF EXISTS books"])
  (init-db!))
