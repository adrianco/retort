(ns book-api.test-support
  "Per-test throwaway SQLite database plus a few request helpers."
  (:require [book-api.db :as db]
            [book-api.handler :as handler]
            [cheshire.core :as json]
            [clojure.java.io :as io]
            [ring.mock.request :as mock]))

(def ^:dynamic *ds* nil)
(def ^:dynamic *app* nil)

(defn with-test-db
  "clojure.test fixture: binds *ds* and *app* to a fresh temporary database.

  A real file (rather than :memory:) is used because next.jdbc opens a new
  connection per operation, and each connection to :memory: would get its own
  empty database."
  [f]
  (let [file (doto (java.io.File/createTempFile "book-api-test" ".db")
               (.delete))                        ; let SQLite create it
        ds   (db/migrate! (db/datasource (.getAbsolutePath file)))]
    (try
      (binding [*ds* ds, *app* (handler/app ds)]
        (f))
      (finally
        (io/delete-file file true)))))

(defn json-body
  "Parse a Ring response body as JSON with keyword keys."
  [response]
  (when-let [b (:body response)]
    (json/parse-string b true)))

(defn request
  "Issue a request against *app*. `body`, when given, is sent as JSON."
  ([method uri] (request method uri nil))
  ([method uri body]
   (*app* (cond-> (mock/request method uri)
            (some? body) (-> (mock/content-type "application/json")
                             (mock/body (json/generate-string body)))))))

(defn raw-request
  "Issue a request with a verbatim (possibly invalid) JSON body string."
  [method uri raw]
  (*app* (-> (mock/request method uri)
             (mock/content-type "application/json")
             (mock/body raw))))

(defn create!
  "Create a book and return the parsed response body."
  [book]
  (json-body (request :post "/books" book)))
