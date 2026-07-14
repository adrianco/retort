(ns books.api-test
  "Integration tests exercising the full Ring handler against an in-memory DB."
  (:require [books.core :as core]
            [books.db :as db]
            [clojure.test :refer [deftest is testing use-fixtures]]
            [muuntaja.core :as m]
            [next.jdbc :as jdbc]))

(def ^:dynamic *app* nil)

(defn fresh-app-fixture
  "Provide each test with a handler backed by a private in-memory SQLite DB.
   A single connection is held open for the duration so the in-memory
   database (which is per-connection in SQLite) survives across requests."
  [f]
  (with-open [conn (jdbc/get-connection {:dbtype "sqlite" :dbname ":memory:"})]
    (db/init-schema! conn)
    (binding [*app* (core/app conn)]
      (f))))

(use-fixtures :each fresh-app-fixture)

(defn- json-body
  "Encode a map to a JSON byte array suitable for a request body stream."
  [m]
  (.getBytes ^String (slurp (m/encode "application/json" m)) "UTF-8"))

(defn- decode [response]
  (when-let [body (:body response)]
    (let [s (if (instance? java.io.InputStream body) (slurp body) (str body))]
      (when (seq s)
        (m/decode "application/json" (.getBytes ^String s))))))

(defn- request
  "Issue a request through the app, encoding the optional body as JSON.
   A query string in the uri (after '?') is split out into :query-string."
  ([method uri] (request method uri nil))
  ([method uri body]
   (let [[path query] (clojure.string/split uri #"\?" 2)]
     (*app*
       (cond-> {:request-method method
                :uri            path
                :query-string   query
                :headers        {"accept" "application/json"}}
         (some? body) (assoc :headers {"content-type" "application/json"
                                       "accept"       "application/json"}
                             :body (java.io.ByteArrayInputStream. (json-body body))))))))

(deftest health-check
  (testing "health endpoint reports ok"
    (let [resp (request :get "/health")]
      (is (= 200 (:status resp)))
      (is (= "ok" (:status (decode resp)))))))

(deftest create-and-fetch-book
  (testing "POST creates a book and returns it with an id"
    (let [resp (request :post "/books"
                        {:title "Dune" :author "Herbert" :year 1965 :isbn "123"})
          book (decode resp)]
      (is (= 201 (:status resp)))
      (is (pos? (:id book)))
      (is (= "Dune" (:title book)))
      (testing "and GET by id returns the same book"
        (let [got (request :get (str "/books/" (:id book)))]
          (is (= 200 (:status got)))
          (is (= "Dune" (:title (decode got)))))))))

(deftest validation-rejects-missing-fields
  (testing "missing title and author yields 400 with error message"
    (let [resp  (request :post "/books" {:year 2000})
          error (:error (decode resp))]
      (is (= 400 (:status resp)))
      (is (re-find #"title is required" error))
      (is (re-find #"author is required" error)))))

(deftest list-and-filter-by-author
  (testing "GET /books lists all and filters by author"
    (request :post "/books" {:title "A" :author "Asimov"})
    (request :post "/books" {:title "B" :author "Herbert"})
    (request :post "/books" {:title "C" :author "Asimov"})
    (let [all (decode (request :get "/books"))]
      (is (= 3 (count all))))
    (let [filtered (decode (request :get "/books?author=Asimov"))]
      (is (= 2 (count filtered)))
      (is (every? #(= "Asimov" (:author %)) filtered)))))

(deftest update-book
  (testing "PUT updates an existing book"
    (let [created (decode (request :post "/books" {:title "Old" :author "X"}))
          id      (:id created)
          resp    (request :put (str "/books/" id)
                           {:title "New" :author "Y" :year 2020 :isbn "999"})
          updated (decode resp)]
      (is (= 200 (:status resp)))
      (is (= "New" (:title updated)))
      (is (= 2020 (:year updated)))))
  (testing "PUT on a missing book yields 404"
    (let [resp (request :put "/books/99999" {:title "x" :author "y"})]
      (is (= 404 (:status resp))))))

(deftest delete-book
  (testing "DELETE removes a book"
    (let [created (decode (request :post "/books" {:title "Temp" :author "Z"}))
          id      (:id created)]
      (is (= 204 (:status (request :delete (str "/books/" id)))))
      (is (= 404 (:status (request :get (str "/books/" id)))))))
  (testing "DELETE on a missing book yields 404"
    (is (= 404 (:status (request :delete "/books/99999"))))))
