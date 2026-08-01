(ns book-service.db
  (:import [java.sql DriverManager PreparedStatement ResultSet]))

(defn connection [database-url]
  (Class/forName "org.sqlite.JDBC")
  (DriverManager/getConnection database-url))

(defn- execute! [database-url sql params]
  (with-open [conn (connection database-url)
              statement (.prepareStatement conn sql)]
    (doseq [[index value] (map-indexed vector params)]
      (.setObject statement (inc index) value))
    (.executeUpdate statement)))

(defn- query! [database-url sql params]
  (with-open [conn (connection database-url)
              statement (.prepareStatement conn sql)]
    (doseq [[index value] (map-indexed vector params)]
      (.setObject statement (inc index) value))
    (with-open [result (.executeQuery statement)]
      (loop [rows []]
        (if (.next result)
          (recur (conj rows {:id (.getLong result "id")
                             :title (.getString result "title")
                             :author (.getString result "author")
                             :year (let [value (.getObject result "year")]
                                     (when-not (.wasNull result) value))
                             :isbn (.getString result "isbn")}))
          rows)))))

(defn initialize! [database-url]
  (execute! database-url
            "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)"
            []))

(defn create-book! [database-url {:keys [title author year isbn]}]
  (with-open [conn (connection database-url)
              statement (.prepareStatement conn
                                           "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
                                           PreparedStatement/RETURN_GENERATED_KEYS)]
    (doseq [[index value] (map-indexed vector [title author year isbn])]
      (.setObject statement (inc index) value))
    (.executeUpdate statement)
    (with-open [keys (.getGeneratedKeys statement)]
      (.next keys)
      (first (query! database-url "SELECT id, title, author, year, isbn FROM books WHERE id = ?" [(.getLong keys 1)])))))

(defn list-books [database-url author]
  (query! database-url
          (if author
            "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id"
            "SELECT id, title, author, year, isbn FROM books ORDER BY id")
          (if author [author] [])))

(defn get-book [database-url id]
  (first (query! database-url "SELECT id, title, author, year, isbn FROM books WHERE id = ?" [id])))

(defn update-book! [database-url id {:keys [title author year isbn]}]
  (if (zero? (execute! database-url "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
                       [title author year isbn id]))
    nil
    (get-book database-url id)))

(defn delete-book! [database-url id]
  (pos? (execute! database-url "DELETE FROM books WHERE id = ?" [id])))
