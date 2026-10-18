(ns book-api.db
  (:require [clojure.java.io :as io])
  (:import [java.sql DriverManager ResultSet]))

(def ^:dynamic *database-path* nil)

(defn database-url []
  (let [path (or *database-path* (System/getenv "BOOKS_DB") "books.db")]
    (str "jdbc:sqlite:" path)))

(defn connection []
  (Class/forName "org.sqlite.JDBC")
  (let [conn (DriverManager/getConnection (database-url))]
    (with-open [stmt (.createStatement conn)]
      (.execute stmt "PRAGMA foreign_keys = ON"))
    conn))

(defn initialize! []
  (with-open [conn (connection)
              stmt (.createStatement conn)]
    (.execute stmt "CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                    )")))

(defn- row->book [^ResultSet rs]
  (let [year (.getInt rs "year")
        year (when-not (.wasNull rs) year)]
    {:id (.getLong rs "id")
     :title (.getString rs "title")
     :author (.getString rs "author")
     :year year
     :isbn (.getString rs "isbn")}))

(defn- query-books [sql values]
  (with-open [conn (connection)
              stmt (.prepareStatement conn sql)]
    (doseq [[index value] (map-indexed vector values)]
      (.setObject stmt (inc index) value))
    (with-open [rs (.executeQuery stmt)]
      (loop [books []]
        (if (.next rs)
          (recur (conj books (row->book rs)))
          books)))))

(defn list-books [author]
  (if (and author (not-empty author))
    (query-books "SELECT * FROM books WHERE author LIKE ? ORDER BY id" [(str "%" author "%")])
    (query-books "SELECT * FROM books ORDER BY id" [])))

(defn get-book [id]
  (first (query-books "SELECT * FROM books WHERE id = ?" [id])))

(defn create-book! [{:keys [title author year isbn]}]
  (with-open [conn (connection)
              stmt (.prepareStatement conn
                                     "INSERT INTO books(title, author, year, isbn) VALUES (?, ?, ?, ?)")]
    (.setString stmt 1 title)
    (.setString stmt 2 author)
    (if (some? year) (.setInt stmt 3 (int year)) (.setNull stmt 3 java.sql.Types/INTEGER))
    (if (some? isbn) (.setString stmt 4 isbn) (.setNull stmt 4 java.sql.Types/VARCHAR))
    (.executeUpdate stmt)
    (let [id (with-open [s (.createStatement conn)
                         rs (.executeQuery s "SELECT last_insert_rowid()")]
               (.next rs)
               (.getLong rs 1))]
      (get-book id))))

(defn update-book! [id {:keys [title author year isbn]}]
  (with-open [conn (connection)
              stmt (.prepareStatement conn
                                     "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")]
    (.setString stmt 1 title)
    (.setString stmt 2 author)
    (if (some? year) (.setInt stmt 3 (int year)) (.setNull stmt 3 java.sql.Types/INTEGER))
    (if (some? isbn) (.setString stmt 4 isbn) (.setNull stmt 4 java.sql.Types/VARCHAR))
    (.setLong stmt 5 (long id))
    (when (pos? (.executeUpdate stmt)) (get-book id))))

(defn delete-book! [id]
  (with-open [conn (connection)
              stmt (.prepareStatement conn "DELETE FROM books WHERE id = ?")]
    (.setLong stmt 1 (long id))
    (pos? (.executeUpdate stmt))))
