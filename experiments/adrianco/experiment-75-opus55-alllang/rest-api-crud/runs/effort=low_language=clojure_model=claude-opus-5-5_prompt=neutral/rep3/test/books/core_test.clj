(ns books.core-test
  (:require [books.core :as c]
            [cheshire.core :as json]
            [clojure.test :refer [deftest is testing]]
            [ring.mock.request :as mock]))

(defn- fresh-app []
  (let [f (java.io.File/createTempFile "books" ".db")]
    (.deleteOnExit f)
    (c/app (c/make-db (.getPath f)))))

(defn- call [app method uri & [body]]
  (let [r (app (cond-> (mock/request method uri)
                 body (mock/json-body body)))]
    (assoc r :json (when (seq (:body r)) (json/parse-string (:body r) true)))))

(deftest health
  (let [r (call (fresh-app) :get "/health")]
    (is (= 200 (:status r)))
    (is (= "ok" (-> r :json :status)))))

(deftest crud-lifecycle
  (let [app (fresh-app)
        created (call app :post "/books" {:title "Dune" :author "Herbert" :year 1965 :isbn "123"})
        id (-> created :json :id)]
    (is (= 201 (:status created)))
    (is (= "Dune" (-> created :json :title)))
    (is (= 200 (:status (call app :get (str "/books/" id)))))
    (let [u (call app :put (str "/books/" id) {:title "Dune Messiah" :author "Herbert" :year 1969})]
      (is (= 200 (:status u)))
      (is (= "Dune Messiah" (-> u :json :title))))
    (is (= 204 (:status (call app :delete (str "/books/" id)))))
    (is (= 404 (:status (call app :get (str "/books/" id)))))
    (is (= 404 (:status (call app :delete (str "/books/" id)))))
    (is (= 404 (:status (call app :put "/books/999" {:title "x" :author "y"}))))))

(deftest validation
  (let [app (fresh-app)]
    (testing "missing title and author"
      (let [r (call app :post "/books" {:year 2000})]
        (is (= 400 (:status r)))
        (is (= ["title is required" "author is required"] (-> r :json :errors)))))
    (is (= 400 (:status (call app :post "/books" {:title "T" :author "A" :year "abc"}))))
    (is (= 400 (:status (app (-> (mock/request :post "/books") (mock/body "{bad"))))))
    (is (= 404 (:status (call app :get "/books/abc"))))))

(deftest list-with-author-filter
  (let [app (fresh-app)]
    (call app :post "/books" {:title "A1" :author "Ann Lee"})
    (call app :post "/books" {:title "B1" :author "Bob"})
    (call app :post "/books" {:title "A2" :author "Ann Lee"})
    (is (= 3 (count (:json (call app :get "/books")))))
    (is (= ["A1" "A2"] (map :title (:json (call app :get "/books?author=Ann%20Lee")))))))
