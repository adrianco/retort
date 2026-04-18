(ns book-api.core-test
  (:require [clojure.test :refer :all]
            [clojure.data.json :as json]
            [book-api.core :refer [app]]
            [book-api.db :as db]
            [ring.mock.request :as mock]
            [next.jdbc :as jdbc]))

(defn parse-body [response]
  (when-let [body (:body response)]
    (cond
      (map? body) body
      (vector? body) body
      (string? body) (when (seq body) (json/read-str body))
      (instance? java.io.InputStream body)
      (let [s (slurp body)]
        (when (seq s) (json/read-str s)))
      :else nil)))

(defn json-request [method url data]
  (-> (mock/request method url)
      (mock/content-type "application/json")
      (assoc-in [:headers "accept"] "application/json")
      (mock/body (json/write-str data))))

(use-fixtures :each
  (fn [f]
    (let [tmp-file (java.io.File/createTempFile "test-books" ".db")
          db-path (.getAbsolutePath tmp-file)
          ds (jdbc/get-datasource {:dbtype "sqlite" :dbname db-path})]
      (.deleteOnExit tmp-file)
      (with-redefs [db/datasource ds]
        (db/init-db!)
        (f))
      (.delete tmp-file))))

(deftest health-check-test
  (testing "GET /health returns 200"
    (let [response (app (mock/request :get "/health"))
          body (parse-body response)]
      (is (= 200 (:status response)))
      (is (or (= "ok" (get body "status"))
              (= "ok" (:status body)))))))

(deftest create-book-validation-test
  (testing "POST /books without title returns 422"
    (let [response (app (json-request :post "/books" {:author "Someone"}))
          body (parse-body response)]
      (is (= 422 (:status response)))
      (is (not (nil? body)))))

  (testing "POST /books without author returns 422"
    (let [response (app (json-request :post "/books" {:title "Some Book"}))
          body (parse-body response)]
      (is (= 422 (:status response)))
      (is (not (nil? body)))))

  (testing "POST /books with empty title returns 422"
    (let [response (app (json-request :post "/books" {:title "" :author "Author"}))]
      (is (= 422 (:status response))))))

(deftest create-and-get-book-test
  (testing "POST /books creates a book and returns 201"
    (let [create-resp (app (json-request :post "/books"
                                         {:title "Clojure for the Brave"
                                          :author "Daniel Higginbotham"
                                          :year 2015
                                          :isbn "978-1593275914"}))
          body (parse-body create-resp)]
      (is (= 201 (:status create-resp)))
      (is (not (nil? body)))))

  (testing "GET /books/:id retrieves a book"
    (let [create-resp (app (json-request :post "/books"
                                         {:title "The Joy of Clojure"
                                          :author "Michael Fogus"}))
          body (parse-body create-resp)
          id (or (get body "id") (:id body))]
      (is (= 201 (:status create-resp)))
      (when id
        (let [get-resp (app (mock/request :get (str "/books/" id)))
              get-body (parse-body get-resp)]
          (is (= 200 (:status get-resp)))
          (is (or (= "The Joy of Clojure" (get get-body "title"))
                  (= "The Joy of Clojure" (:title get-body)))))))))

(deftest list-books-test
  (testing "GET /books returns list"
    (app (json-request :post "/books" {:title "Book A" :author "Author X"}))
    (app (json-request :post "/books" {:title "Book B" :author "Author Y"}))
    (let [response (app (mock/request :get "/books"))
          body (parse-body response)]
      (is (= 200 (:status response)))
      (is (sequential? body))
      (is (>= (count body) 2)))))

(deftest filter-books-test
  (testing "GET /books?author= filters by author"
    (app (json-request :post "/books" {:title "Book A" :author "Common Author"}))
    (app (json-request :post "/books" {:title "Book B" :author "Other Author"}))
    (let [response (app (mock/request :get "/books?author=Common"))
          body (parse-body response)]
      (is (= 200 (:status response)))
      (is (sequential? body))
      (is (pos? (count body))))))

(deftest update-book-test
  (testing "PUT /books/:id updates a book"
    (let [create-resp (app (json-request :post "/books"
                                         {:title "Old Title" :author "Old Author"}))
          cre-body (parse-body create-resp)
          id (or (get cre-body "id") (:id cre-body))
          update-resp (app (json-request :put (str "/books/" id)
                                         {:title "New Title" :author "New Author"}))
          body (parse-body update-resp)]
      (is (= 201 (:status create-resp)))
      (is (= 200 (:status update-resp)))
      (is (or (= "New Title" (get body "title")) (= "New Title" (:title body))))))

  (testing "PUT /books/:id returns 404 for missing book"
    (let [response (app (json-request :put "/books/99999" {:title "X" :author "Y"}))]
      (is (= 404 (:status response))))))

(deftest delete-book-test
  (testing "DELETE /books/:id deletes a book"
    (let [create-resp (app (json-request :post "/books"
                                         {:title "To Delete" :author "Someone"}))
          cre-body (parse-body create-resp)
          id (or (get cre-body "id") (:id cre-body))
          del-resp (app (mock/request :delete (str "/books/" id)))
          get-resp (app (mock/request :get (str "/books/" id)))]
      (is (= 201 (:status create-resp)))
      (is (= 204 (:status del-resp)))
      (is (= 404 (:status get-resp)))))

  (testing "DELETE /books/:id returns 404 for missing book"
    (let [response (app (mock/request :delete "/books/99999"))]
      (is (= 404 (:status response))))))

(deftest get-nonexistent-book-test
  (testing "GET /books/:id returns 404 for nonexistent book"
    (let [response (app (mock/request :get "/books/99999"))]
      (is (= 404 (:status response))))))
