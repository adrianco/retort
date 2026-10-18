(ns book-api.db
  (:require [clojure.string :as str])
  (:import [java.sql DriverManager]))

(defonce ^:private connection (atom nil))

(defn- db-url []
  (str "jdbc:sqlite:" (or (System/getenv "BOOKS_DB") "books.db")))

(defn get-connection []
  (or @connection
      (locking connection
        (or @connection
            (let [conn (DriverManager/getConnection (db-url))]
              (with-open [stmt (.createStatement conn)]
                (.execute stmt "PRAGMA foreign_keys = ON")
                (.execute stmt "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)"))
              (reset! connection conn))))))

(defn reset-db! []
  (when-let [conn @connection]
    (with-open [stmt (.createStatement conn)]
      (.execute stmt "DROP TABLE IF EXISTS books"))
    (reset! connection nil))
  (get-connection))

(defn- read-book [rs]
  {:id (.getLong rs "id")
   :title (.getString rs "title")
   :author (.getString rs "author")
   :year (let [y (.getInt rs "year")] (when-not (.wasNull rs) y))
   :isbn (.getString rs "isbn")})

(defn all-books ([] (all-books nil))
  ([author]
   (let [conn (get-connection)
         sql (if (str/blank? author) "SELECT * FROM books ORDER BY id" "SELECT * FROM books WHERE author = ? ORDER BY id")]
     (with-open [stmt (if (str/blank? author)
                        (.prepareStatement conn sql)
                        (doto (.prepareStatement conn sql) (.setString 1 author)))
                 rs (.executeQuery stmt)]
       (loop [books []]
         (if (.next rs) (recur (conj books (read-book rs))) books))))))

(defn find-book [id]
  (with-open [stmt (.prepareStatement (get-connection) "SELECT * FROM books WHERE id = ?")]
    (.setLong stmt 1 (long id))
    (with-open [rs (.executeQuery stmt)]
      (when (.next rs) (read-book rs)))))

(defn- set-fields! [stmt book offset]
  (.setString stmt offset (:title book))
  (.setString stmt (inc offset) (:author book))
  (if (some? (:year book)) (.setInt stmt (+ offset 2) (int (:year book))) (.setNull stmt (+ offset 2) java.sql.Types/INTEGER))
  (if (some? (:isbn book)) (.setString stmt (+ offset 3) (:isbn book)) (.setNull stmt (+ offset 3) java.sql.Types/VARCHAR)))

(defn create-book [book]
  (with-open [stmt (.prepareStatement (get-connection) "INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)" java.sql.Statement/RETURN_GENERATED_KEYS)]
    (set-fields! stmt book 1)
    (.executeUpdate stmt)
    (with-open [keys (.getGeneratedKeys stmt)]
      (assoc book :id (if (.next keys) (.getLong keys 1) 0)))))

(defn update-book [id book]
  (with-open [stmt (.prepareStatement (get-connection) "UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?")]
    (set-fields! stmt book 1)
    (.setLong stmt 5 (long id))
    (when (pos? (.executeUpdate stmt)) (find-book id))))

(defn delete-book [id]
  (with-open [stmt (.prepareStatement (get-connection) "DELETE FROM books WHERE id=?")]
    (.setLong stmt 1 (long id))
    (pos? (.executeUpdate stmt))))
