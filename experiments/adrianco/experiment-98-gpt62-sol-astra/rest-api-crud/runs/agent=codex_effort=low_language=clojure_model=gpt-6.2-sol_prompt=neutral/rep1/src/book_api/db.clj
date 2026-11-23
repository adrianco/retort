(ns book-api.db
  (:import [java.sql Connection DriverManager PreparedStatement ResultSet Types]))

(defn- statement ^PreparedStatement [^Connection connection ^String sql params]
  (let [^PreparedStatement stmt (.prepareStatement connection sql)]
    (try
      (doseq [[index value] (map-indexed vector params)]
        (let [position (inc index)]
          (cond
            (nil? value) (.setNull stmt position Types/NULL)
            (string? value) (.setString stmt position value)
            :else (.setLong stmt position (long value)))))
      stmt
      (catch Exception e
        (.close stmt)
        (throw e)))))

(defn- read-book [^ResultSet row]
  {:id (.getLong row "id")
   :title (.getString row "title")
   :author (.getString row "author")
   :year (.getObject row "year")
   :isbn (.getString row "isbn")})

(defn- query [url sql & params]
  (with-open [connection (DriverManager/getConnection url)
              stmt (statement connection sql params)
              rows (.executeQuery stmt)]
    (loop [books []]
      (if (.next rows)
        (recur (conj books (read-book rows)))
        books))))

(defn init! [url]
  (with-open [connection (DriverManager/getConnection url)
              stmt (.createStatement connection)]
    (.execute stmt "CREATE TABLE IF NOT EXISTS books (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     title TEXT NOT NULL,
                     author TEXT NOT NULL,
                     year INTEGER,
                     isbn TEXT
                    )")))

(defn create! [url {:keys [title author year isbn]}]
  (first (query url "INSERT INTO books (title, author, year, isbn)
                     VALUES (?, ?, ?, ?) RETURNING *"
                title author year isbn)))

(defn list-books [url author]
  (if (some? author)
    (query url "SELECT * FROM books WHERE author = ? ORDER BY id" author)
    (query url "SELECT * FROM books ORDER BY id")))

(defn get-book [url id]
  (first (query url "SELECT * FROM books WHERE id = ?" id)))

(defn update! [url id {:keys [title author year isbn]}]
  (first (query url "UPDATE books SET title = ?, author = ?, year = ?, isbn = ?
                     WHERE id = ? RETURNING *"
                title author year isbn id)))

(defn delete! [url id]
  (with-open [connection (DriverManager/getConnection url)
              stmt (statement connection "DELETE FROM books WHERE id = ?" [id])]
    (pos? (.executeUpdate stmt))))
