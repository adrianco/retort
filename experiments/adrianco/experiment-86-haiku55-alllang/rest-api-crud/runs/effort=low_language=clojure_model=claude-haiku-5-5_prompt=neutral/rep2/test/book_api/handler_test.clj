(ns book-api.handler-test
  "Integration tests: drive the Ring handler against a real SQLite file."
  (:require [book-api.db :as db]
            [book-api.handler :as handler]
            [cheshire.core :as json]
            [clojure.test :refer [deftest is testing use-fixtures]]))

(def ^:dynamic *app* nil)

(defn- temp-db-fixture [f]
  (let [file (java.io.File/createTempFile "books-test" ".db")]
    (try
      (binding [*app* (handler/make-handler (db/make-datasource (.getAbsolutePath file)))]
        (f))
      (finally (.delete file)))))

(use-fixtures :each temp-db-fixture)

(defn- request
  ([method uri] (request method uri nil))
  ([method uri body]
   (cond-> {:request-method method :uri uri :headers {}}
     body (assoc :body (java.io.ByteArrayInputStream. (.getBytes (json/generate-string body) "UTF-8"))
                 :headers {"content-type" "application/json"}))))

(defn- raw-request [method uri raw-body]
  {:request-method method :uri uri :headers {}
   :body (java.io.ByteArrayInputStream. (.getBytes raw-body "UTF-8"))})

(defn- call
  ([method uri] (*app* (request method uri)))
  ([method uri body] (*app* (request method uri body))))

(defn- parse [resp] (json/parse-string (:body resp) true))

(def dune {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441013593"})

(defn- create! [book]
  (let [resp (call :post "/books" book)]
    (assert (= 201 (:status resp)) (:body resp))
    (parse resp)))

(deftest health-check
  (let [resp (call :get "/health")]
    (is (= 200 (:status resp)))
    (is (= {:status "ok"} (parse resp)))))

(deftest create-and-get-book
  (testing "POST returns 201 with the stored book including an id"
    (let [created (create! dune)]
      (is (pos-int? (:id created)))
      (is (= "Dune" (:title created)))
      (is (= "Frank Herbert" (:author created)))
      (is (= 1965 (:year created)))
      (is (= "9780441013593" (:isbn created)))
      (testing "GET /books/{id} returns the same book"
        (let [resp (call :get (str "/books/" (:id created)))]
          (is (= 200 (:status resp)))
          (is (= created (parse resp))))))))

(deftest list-and-filter-books
  (create! dune)
  (create! {:title "Emma" :author "Jane Austen" :year 1815})
  (create! {:title "Persuasion" :author "Jane Austen"})
  (testing "GET /books lists everything"
    (is (= 3 (count (parse (call :get "/books"))))))
  (testing "GET /books?author= filters by author, case-insensitively"
    (let [books (*app* (assoc (request :get "/books") :query-string "author=jane%20austen"))
          titles (map :title (json/parse-string (:body books) true))]
      (is (= 200 (:status books)))
      (is (= ["Emma" "Persuasion"] titles)))))

(deftest update-book
  (let [{:keys [id]} (create! dune)
        resp (call :put (str "/books/" id) {:title "Dune Messiah" :author "Frank Herbert" :year 1969})]
    (is (= 200 (:status resp)))
    (is (= "Dune Messiah" (:title (parse resp))))
    (is (= "Dune Messiah" (:title (parse (call :get (str "/books/" id))))))))

(deftest delete-book
  (let [{:keys [id]} (create! dune)]
    (is (= 204 (:status (call :delete (str "/books/" id)))))
    (is (= 404 (:status (call :get (str "/books/" id)))))
    (is (= 404 (:status (call :delete (str "/books/" id)))))))

(deftest not-found-cases
  (is (= 404 (:status (call :get "/books/9999"))))
  (is (= 404 (:status (call :put "/books/9999" dune))))
  (is (= 404 (:status (call :get "/books/abc"))))
  (is (= 404 (:status (call :get "/nope")))))

(deftest validation-rejects-missing-title-and-author
  (testing "missing title and author are reported"
    (let [resp (call :post "/books" {:year 2000})]
      (is (= 422 (:status resp)))
      (is (= #{:title :author} (set (keys (:fields (parse resp))))))))
  (testing "blank strings are rejected"
    (is (= 422 (:status (call :post "/books" {:title "  " :author "x"})))))
  (testing "non-integer year is rejected"
    (is (= 422 (:status (call :post "/books" {:title "t" :author "a" :year "1999"})))))
  (testing "PUT is validated too"
    (let [{:keys [id]} (create! dune)]
      (is (= 422 (:status (call :put (str "/books/" id) {:author "a"})))))))

(deftest malformed-body-is-bad-request
  (let [resp (*app* (raw-request :post "/books" "{not json"))]
    (is (= 400 (:status resp)))))

(deftest method-not-allowed
  (is (= 405 (:status (call :patch "/books/1")))))
