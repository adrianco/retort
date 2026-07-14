(ns books.handler-test
  "Integration tests driving the Ring handler against an in-memory SQLite DB."
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [clojure.data.json :as json]
            [next.jdbc :as jdbc]
            [books.db :as db]
            [books.handler :as handler]))

(def ^:dynamic *app* nil)

(defn each-fixture
  "Fresh in-memory database + handler for every test. A single open
  connection is held open so the in-memory database survives across requests."
  [f]
  (with-open [conn (jdbc/get-connection (db/make-datasource ":memory:"))]
    (db/init-schema! conn)
    (binding [*app* (handler/app conn)]
      (f))))

(use-fixtures :each each-fixture)

(defn- request
  "Issue a request through the handler, encoding/decoding JSON bodies."
  ([method uri] (request method uri nil))
  ([method uri body]
   (let [[path query] (clojure.string/split uri #"\?" 2)
         req (cond-> {:request-method method
                      :uri path
                      :query-string query
                      :headers {"content-type" "application/json"}}
               body (assoc :body (java.io.ByteArrayInputStream.
                                   (.getBytes (json/write-str body)))))
         resp (*app* req)]
     (cond-> resp
       (and (:body resp) (string? (:body resp)) (seq (:body resp)))
       (assoc :json (json/read-str (:body resp) :key-fn keyword))))))

(deftest health-check
  (testing "health endpoint reports ok"
    (let [resp (request :get "/health")]
      (is (= 200 (:status resp)))
      (is (= "ok" (get-in resp [:json :status]))))))

(deftest create-and-fetch-book
  (testing "POST creates a book and returns 201 with an id"
    (let [resp (request :post "/books"
                        {:title "Clojure" :author "Hickey" :year 2010 :isbn "123"})]
      (is (= 201 (:status resp)))
      (is (some? (get-in resp [:json :id])))
      (is (= "Clojure" (get-in resp [:json :title])))
      (testing "and GET /books/:id returns it"
        (let [id (get-in resp [:json :id])
              got (request :get (str "/books/" id))]
          (is (= 200 (:status got)))
          (is (= "Hickey" (get-in got [:json :author]))))))))

(deftest validation-rejects-missing-fields
  (testing "POST without title/author returns 400"
    (let [resp (request :post "/books" {:year 2020})]
      (is (= 400 (:status resp)))
      (is (some #{"title is required"} (get-in resp [:json :errors])))
      (is (some #{"author is required"} (get-in resp [:json :errors]))))))

(deftest list-and-filter-by-author
  (testing "GET /books lists all and filters by author"
    (request :post "/books" {:title "A" :author "Smith"})
    (request :post "/books" {:title "B" :author "Jones"})
    (request :post "/books" {:title "C" :author "Smith"})
    (let [all (request :get "/books")]
      (is (= 200 (:status all)))
      (is (= 3 (count (:json all)))))
    (let [filtered (request :get "/books?author=Smith")]
      (is (= 2 (count (:json filtered))))
      (is (every? #(= "Smith" (:author %)) (:json filtered))))))

(deftest update-book
  (testing "PUT updates an existing book"
    (let [created (request :post "/books" {:title "Old" :author "Auth"})
          id (get-in created [:json :id])
          updated (request :put (str "/books/" id)
                           {:title "New" :author "Auth" :year 2021})]
      (is (= 200 (:status updated)))
      (is (= "New" (get-in updated [:json :title])))
      (is (= 2021 (get-in updated [:json :year]))))))

(deftest delete-book
  (testing "DELETE removes a book and subsequent GET is 404"
    (let [created (request :post "/books" {:title "Doomed" :author "Auth"})
          id (get-in created [:json :id])
          deleted (request :delete (str "/books/" id))]
      (is (= 204 (:status deleted)))
      (is (= 404 (:status (request :get (str "/books/" id))))))))

(deftest missing-book-returns-404
  (testing "GET unknown id returns 404"
    (is (= 404 (:status (request :get "/books/9999"))))))
