(ns books.core
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.params :refer [wrap-params]])
  (:import [java.sql DriverManager Connection PreparedStatement ResultSet]))

(defn connect [db-path]
  (DriverManager/getConnection (str "jdbc:sqlite:" db-path)))

(defn init-db! [db-path]
  (with-open [conn (connect db-path)
              stmt (.createStatement conn)]
    (.execute stmt "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)")))

(defn- bind! [^PreparedStatement stmt values]
  (doseq [[index value] (map-indexed vector values)]
    (.setObject stmt (inc index) value))
  stmt)

(defn- row [^ResultSet rs]
  {:id (.getLong rs "id") :title (.getString rs "title")
   :author (.getString rs "author") :year (.getObject rs "year")
   :isbn (.getString rs "isbn")})

(defn- query [^Connection conn sql values]
  (with-open [stmt (bind! (.prepareStatement conn sql) values)
              rs (.executeQuery stmt)]
    (loop [rows []]
      (if (.next rs) (recur (conj rows (row rs))) rows))))

(defn- execute! [^Connection conn sql values]
  (with-open [stmt (bind! (.prepareStatement conn sql) values)]
    (.executeUpdate stmt)))

(defn- response [status body]
  {:status status :headers {"Content-Type" "application/json; charset=utf-8"}
   :body (json/write-str body)})

(defn- error [status message] (response status {:error message}))

(defn- valid-book? [book]
  (and (map? book)
       (every? #(and (string? %) (not (str/blank? %))) [(:title book) (:author book)])
       (or (nil? (:year book)) (and (integer? (:year book)) (<= -2147483648 (:year book) 2147483647)))
       (or (nil? (:isbn book)) (string? (:isbn book)))))

(defn- parse-body [request]
  (try
    (when-let [body (:body request)]
      (json/read-str (slurp body) :key-fn keyword))
    (catch Exception _ ::invalid)))

(defn- find-book [conn id]
  (first (query conn "SELECT id, title, author, year, isbn FROM books WHERE id = ?" [id])))

(defn- book-values [book]
  [(:title book) (:author book) (:year book) (:isbn book)])

(defn- book-id [uri]
  (when-let [[_ s] (re-matches #"/books/([0-9]+)" uri)]
    (try (Long/parseLong s) (catch NumberFormatException _ nil))))

(defn handler [db-path]
  (wrap-params
   (fn [{:keys [request-method uri params] :as request}]
     (let [id (book-id uri)]
       (cond
         (and (= request-method :get) (= uri "/health"))
         (response 200 {:status "ok"})

         (and (= request-method :get) (= uri "/books"))
         (with-open [conn (connect db-path)]
           (response 200 (if (contains? params "author")
                           (query conn "SELECT * FROM books WHERE author = ? ORDER BY id" [(get params "author")])
                           (query conn "SELECT * FROM books ORDER BY id" []))))

         (and (= request-method :post) (= uri "/books"))
         (let [book (parse-body request)]
           (if-not (valid-book? book)
             (error 400 "Expected a JSON object with non-empty title and author, an optional integer year and an optional string isbn")
             (with-open [conn (connect db-path)]
               (execute! conn "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)" (book-values book))
               (let [id (with-open [stmt (.createStatement conn) rs (.executeQuery stmt "SELECT last_insert_rowid()")]
                          (.next rs) (.getLong rs 1))]
                 (assoc-in (response 201 (find-book conn id)) [:headers "Location"] (str "/books/" id))))))

         (and id (= request-method :get))
         (with-open [conn (connect db-path)]
           (if-let [book (find-book conn id)] (response 200 book) (error 404 "Book not found")))

         (and id (= request-method :put))
         (let [book (parse-body request)]
           (if-not (valid-book? book)
             (error 400 "Expected a JSON object with non-empty title and author, an optional integer year and an optional string isbn")
             (with-open [conn (connect db-path)]
               (if (pos? (execute! conn "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?" (conj (book-values book) id)))
                 (response 200 (find-book conn id))
                 (error 404 "Book not found")))))

         (and id (= request-method :delete))
         (with-open [conn (connect db-path)]
           (if (pos? (execute! conn "DELETE FROM books WHERE id = ?" [id]))
             (response 200 {:deleted true})
             (error 404 "Book not found")))

         :else (error 404 "Not found"))))))

(defn -main [& _]
  (let [db-path (or (System/getenv "BOOKS_DB") "books.db")
        port (Integer/parseInt (or (System/getenv "PORT") "3000"))]
    (init-db! db-path)
    (jetty/run-jetty (handler db-path) {:port port :join? true})))
