(ns books.api-test
  (:require [clojure.test :refer [deftest is testing use-fixtures]]
            [books.db :as db]
            [books.handler :as h]
            [cheshire.core :as json]
            [clojure.java.io :as io]
            [clojure.string :as str]))

(def ^:dynamic *app* nil)

(defn- with-app [f]
  (let [file (java.io.File/createTempFile "books-test" ".db")]
    (.deleteOnExit file)
    (binding [*app* (h/app (db/open (.getPath file)))]
      (f))))

(use-fixtures :each with-app)

(defn- request
  "Calls the app with a JSON body (when given) and returns {:status :body} with parsed JSON."
  ([method uri] (request method uri nil))
  ([method uri body]
   (let [[path query] (str/split uri #"\?" 2)
         resp (*app* (cond-> {:request-method method
                              :uri path
                              :headers {"content-type" "application/json"}
                              :query-string query}
                       body (assoc :body (io/input-stream (.getBytes (json/generate-string body) "UTF-8")))))
         raw (:body resp)]
     {:status (:status resp)
      :body (when (string? raw) (json/parse-string raw true))})))

(defn- create! [book]
  (:body (request :post "/books" book)))

(def dune {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441172719"})

(deftest health-check
  (let [r (request :get "/health")]
    (is (= 200 (:status r)))
    (is (= {:status "ok"} (:body r)))))

(deftest create-and-get-book
  (let [created (request :post "/books" dune)]
    (is (= 201 (:status created)))
    (is (= "Dune" (get-in created [:body :title])))
    (let [id (get-in created [:body :id])
          fetched (request :get (str "/books/" id))]
      (is (= 200 (:status fetched)))
      (is (= dune (dissoc (:body fetched) :id))))))

(deftest create-validates-input
  (let [r (request :post "/books" {:year 1965})]
    (is (= 400 (:status r)))
    (is (= {:title "title is required" :author "author is required"}
           (get-in r [:body :details])))))

(deftest list-and-filter-by-author
  (create! dune)
  (create! {:title "Emma" :author "Jane Austen"})
  (testing "all books"
    (is (= 2 (count (:body (request :get "/books"))))))
  (testing "author filter"
    (let [books (:body (request :get "/books?author=Jane%20Austen"))]
      (is (= ["Emma"] (map :title books))))))

(deftest update-book
  (let [id (get-in (request :post "/books" dune) [:body :id])
        r (request :put (str "/books/" id) {:title "Dune Messiah" :author "Frank Herbert"})]
    (is (= 200 (:status r)))
    (is (= "Dune Messiah" (get-in r [:body :title])))
    (is (nil? (get-in r [:body :isbn])))
    (is (= 404 (:status (request :put "/books/9999" dune))))
    (is (= 400 (:status (request :put (str "/books/" id) {:author "x"}))))))

(deftest delete-book
  (let [id (get-in (request :post "/books" dune) [:body :id])]
    (is (= 204 (:status (request :delete (str "/books/" id)))))
    (is (= 404 (:status (request :get (str "/books/" id)))))
    (is (= 404 (:status (request :delete (str "/books/" id)))))))

(deftest not-found-and-bad-ids
  (is (= 404 (:status (request :get "/books/9999"))))
  (is (= 404 (:status (request :get "/books/abc"))))
  (is (= 404 (:status (request :get "/nope")))))
