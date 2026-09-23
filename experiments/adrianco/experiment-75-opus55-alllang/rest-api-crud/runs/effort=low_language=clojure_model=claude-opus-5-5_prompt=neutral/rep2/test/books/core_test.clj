(ns books.core-test
  (:require [books.core :as core]
            [cheshire.core :as json]
            [clojure.test :refer [deftest is testing]]
            [ring.mock.request :as mock]))

(defn- fresh-app []
  (let [f (java.io.File/createTempFile "books" ".db")]
    (.deleteOnExit f)
    (core/app (core/make-db (.getPath f)))))

(defn- call [app method path & [body]]
  (let [req (cond-> (mock/request method path)
              body (-> (mock/body (json/generate-string body))
                       (mock/content-type "application/json")))
        r (app req)]
    (assoc r :json (when (seq (:body r)) (json/parse-string (:body r) true)))))

(deftest health-check
  (let [r (call (fresh-app) :get "/health")]
    (is (= 200 (:status r)))
    (is (= "ok" (get-in r [:json :status])))))

(deftest crud-lifecycle
  (let [app (fresh-app)
        c (call app :post "/books" {:title "Dune" :author "Herbert" :year 1965 :isbn "123"})
        id (get-in c [:json :id])]
    (is (= 201 (:status c)))
    (is (= "Dune" (get-in c [:json :title])))
    (is (= 200 (:status (call app :get (str "/books/" id)))))
    (let [u (call app :put (str "/books/" id) {:title "Dune Messiah" :author "Herbert" :year 1969})]
      (is (= 200 (:status u)))
      (is (= 1969 (get-in u [:json :year]))))
    (is (= 204 (:status (call app :delete (str "/books/" id)))))
    (is (= 404 (:status (call app :get (str "/books/" id)))))
    (is (= 404 (:status (call app :delete (str "/books/" id)))))))

(deftest author-filter
  (let [app (fresh-app)]
    (call app :post "/books" {:title "A" :author "X"})
    (call app :post "/books" {:title "B" :author "Y"})
    (call app :post "/books" {:title "C" :author "X"})
    (is (= 3 (count (:json (call app :get "/books")))))
    (is (= ["A" "C"] (map :title (:json (call app :get "/books?author=X")))))))

(deftest validation
  (let [app (fresh-app)]
    (testing "missing title and author"
      (let [r (call app :post "/books" {:year 2000})]
        (is (= 400 (:status r)))
        (is (= 2 (count (get-in r [:json :errors]))))))
    (testing "bad year"
      (is (= 400 (:status (call app :post "/books" {:title "T" :author "A" :year "x"})))))
    (testing "put validates"
      (let [id (get-in (call app :post "/books" {:title "T" :author "A"}) [:json :id])]
        (is (= 400 (:status (call app :put (str "/books/" id) {:title ""}))))))
    (testing "unknown id"
      (is (= 404 (:status (call app :put "/books/999" {:title "T" :author "A"}))))
      (is (= 404 (:status (call app :get "/books/abc")))))))
