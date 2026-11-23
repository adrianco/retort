(ns books
  (:require [clojure.data.json :as json]
            [clojure.java.jdbc :as jdbc]
            [clojure.string :as str]
            [ring.adapter.jetty :as jetty]
            [ring.util.codec :as codec]))

(defn open-db [path]
  (let [db {:classname "org.sqlite.JDBC" :subprotocol "sqlite" :subname path}]
    (jdbc/execute! db ["CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
      author TEXT NOT NULL, year INTEGER, isbn TEXT)"])
    db))

(defn response [status value]
  {:status status :headers {"Content-Type" "application/json; charset=utf-8"}
   :body (json/write-str value)})

(def missing (response 404 {:error "Not found"}))

(defn method-error [allowed]
  (assoc-in (response 405 {:error "Method not allowed"}) [:headers "Allow"] allowed))

(defn invalid [message]
  (throw (ex-info message {:status 400})))

(defn book-values [body]
  (let [data (try (json/read-str (slurp body :encoding "UTF-8") :extra-data-fn json/on-extra-throw)
                  (catch Exception _ (invalid "Expected a JSON object")))
        [title author year isbn] (map #(get data %) ["title" "author" "year" "isbn"])]
    (when-not (every? #(and (string? %) (not (str/blank? %))) [title author])
      (invalid "Title and author must be nonblank strings"))
    (when-not (or (nil? year) (and (integer? year) (<= Long/MIN_VALUE year Long/MAX_VALUE)))
      (invalid "Year must be an integer"))
    (when-not (or (nil? isbn) (string? isbn))
      (invalid "ISBN must be a string"))
    [title author year isbn]))

(defn collection-route [db method body query-string]
  (case method
    :get (let [author (get (codec/form-decode (or query-string "")) "author")]
           (response 200 (jdbc/query db (if author
                                         ["SELECT * FROM books WHERE author = ? ORDER BY id" author]
                                         ["SELECT * FROM books ORDER BY id"]))))
    :post (let [values (book-values body)
                book (first (jdbc/query db (into ["INSERT INTO books (title,author,year,isbn)
                                                  VALUES (?,?,?,?) RETURNING *"] values)))]
            (assoc-in (response 201 book) [:headers "Location"] (str "/books/" (:id book))))
    (method-error "GET, POST")))

(defn item-route [db method body id]
  (case method
    :delete (if (pos? (first (jdbc/execute! db ["DELETE FROM books WHERE id=?" id])))
              (response 200 {:id id}) missing)
    (:get :put)
    (let [sql (if (= :get method)
                ["SELECT * FROM books WHERE id=?" id]
                (into ["UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=? RETURNING *"]
                      (conj (book-values body) id)))]
      (if-let [book (first (jdbc/query db sql))] (response 200 book) missing))
    (method-error "GET, PUT, DELETE")))

(defn handler [db]
  (fn [{:keys [request-method uri body query-string]}]
    (try
      (case uri
        "/health" (if (= request-method :get) (response 200 {:status "ok"}) (method-error "GET"))
        "/books" (collection-route db request-method body query-string)
        (if-let [id (some-> (re-matches #"/books/([0-9]+)" uri) second parse-long)]
          (item-route db request-method body id)
          missing))
      (catch clojure.lang.ExceptionInfo e
        (response (:status (ex-data e)) {:error (.getMessage e)}))
      (catch Exception e
        (.printStackTrace e)
        (response 500 {:error "Internal server error"})))))

(defn -main [& _]
  (jetty/run-jetty (handler (open-db (or (System/getenv "BOOKS_DB") "books.sqlite")))
                   {:port (Integer/parseInt (or (System/getenv "PORT") "8080"))}))
