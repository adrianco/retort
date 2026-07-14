(ns books.handler-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [books.db :as db]
            [books.handler :as handler]
            [cheshire.core :as json]))

(def ^:dynamic *app* nil)

(defn fresh-app
  "Build an app backed by a fresh in-memory SQLite database."
  []
  (let [ds (db/make-datasource ":memory:")]
    (db/init-schema! ds)
    (handler/make-app ds)))

(use-fixtures :each
  (fn [f]
    (binding [*app* (fresh-app)]
      (f))))

(defn req
  "Issue a request to the app under test. `body` is JSON-encoded if given."
  ([method uri] (req method uri nil))
  ([method uri body]
   (let [resp (*app* (cond-> {:request-method method :uri uri}
                       body (assoc :body (java.io.ByteArrayInputStream.
                                          (.getBytes (json/generate-string body))))))]
     (update resp :body #(when (and % (seq (str %)))
                           (json/parse-string % true))))))

(deftest health-check
  (testing "health endpoint reports ok"
    (let [resp (req :get "/health")]
      (is (= 200 (:status resp)))
      (is (= "ok" (get-in resp [:body :status]))))))

(deftest create-and-fetch
  (testing "POST creates a book and returns 201 with an id"
    (let [resp (req :post "/books"
                    {:title "Clojure" :author "Rich" :year 2007 :isbn "123"})]
      (is (= 201 (:status resp)))
      (is (some? (get-in resp [:body :id])))
      (is (= "Clojure" (get-in resp [:body :title])))
      (testing "and the book can then be fetched by id"
        (let [id  (get-in resp [:body :id])
              got (req :get (str "/books/" id))]
          (is (= 200 (:status got)))
          (is (= "Rich" (get-in got [:body :author]))))))))

(deftest validation-rejects-missing-fields
  (testing "POST without title/author returns 400 with errors"
    (let [resp (req :post "/books" {:year 2020})]
      (is (= 400 (:status resp)))
      (is (= 2 (count (get-in resp [:body :errors])))))))

(deftest list-and-filter
  (testing "GET /books lists all books and supports ?author= filter"
    (req :post "/books" {:title "A" :author "Alice"})
    (req :post "/books" {:title "B" :author "Bob"})
    (req :post "/books" {:title "C" :author "Alice"})
    (let [all (req :get "/books")]
      (is (= 200 (:status all)))
      (is (= 3 (count (:body all)))))
    (let [filtered (*app* {:request-method :get :uri "/books"
                           :query-string "author=Alice"})
          books    (json/parse-string (:body filtered) true)]
      (is (= 200 (:status filtered)))
      (is (= 2 (count books)))
      (is (every? #(= "Alice" (:author %)) books)))))

(deftest update-and-delete
  (testing "PUT updates a book and DELETE removes it"
    (let [created (req :post "/books" {:title "Old" :author "X"})
          id      (get-in created [:body :id])
          updated (req :put (str "/books/" id) {:title "New" :author "X" :year 2021})]
      (is (= 200 (:status updated)))
      (is (= "New" (get-in updated [:body :title])))
      (let [del (req :delete (str "/books/" id))]
        (is (= 204 (:status del))))
      (let [gone (req :get (str "/books/" id))]
        (is (= 404 (:status gone)))))))

(deftest missing-book-returns-404
  (testing "GET/PUT/DELETE on unknown id return 404"
    (is (= 404 (:status (req :get "/books/9999"))))
    (is (= 404 (:status (req :put "/books/9999" {:title "T" :author "A"}))))
    (is (= 404 (:status (req :delete "/books/9999"))))))
