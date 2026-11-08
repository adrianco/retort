(ns books.core-test
  (:require [books.core :as core]
            [clojure.data.json :as json]
            [clojure.test :refer [deftest is testing]])
  (:import [java.io ByteArrayInputStream]
           [java.nio.file Files]))

(defn with-app [f]
  (let [path (.toFile (Files/createTempFile "books-test" ".db" (make-array java.nio.file.attribute.FileAttribute 0)))]
    (try
      (core/init-db! (.getPath path))
      (f (core/handler (.getPath path)))
      (finally (.delete path)))))

(defn request
  ([app method uri] (request app method uri nil))
  ([app method uri body]
   (let [[path query] (clojure.string/split uri #"\?" 2)
         result (app {:request-method method :uri path :query-string query
                      :body (when body (ByteArrayInputStream. (.getBytes body "UTF-8")))})]
     (update result :body #(json/read-str % :key-fn keyword)))))

(deftest health-and-empty-list
  (with-app (fn [app]
              (is (= {:status "ok"} (:body (request app :get "/health"))))
              (is (= [] (:body (request app :get "/books")))))))

(deftest create-read-filter-and-delete
  (with-app
    (fn [app]
      (let [created (request app :post "/books" "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"abc\"}")
            id (get-in created [:body :id])
            url (str "/books/" id)]
        (is (= 201 (:status created)))
        (is (= url (get-in created [:headers "Location"])))
        (is (= (:body created) (:body (request app :get url))))
        (request app :post "/books" "{\"title\":\"Other\",\"author\":\"Someone\"}")
        (is (= [(:body created)] (:body (request app :get "/books?author=Frank+Herbert"))))
        (is (= 200 (:status (request app :delete url))))
        (is (= 404 (:status (request app :get url))))
        (is (= 404 (:status (request app :delete url))))))))

(deftest validation-and-update
  (with-app
    (fn [app]
      (doseq [body ["{" "{}" "[]" "{\"title\":\" \",\"author\":\"A\"}" "{\"title\":\"T\",\"author\":\"A\",\"year\":\"bad\"}"]]
        (is (= 400 (:status (request app :post "/books" body)))))
      (let [created (request app :post "/books" "{\"title\":\"T\",\"author\":\"A\",\"year\":2000}")
            url (str "/books/" (get-in created [:body :id]))
            updated (request app :put url "{\"title\":\"New\",\"author\":\"B\"}")]
        (is (= 200 (:status updated)))
        (is (= "New" (get-in updated [:body :title])))
        (is (nil? (get-in updated [:body :year])))
        (is (= (:body updated) (:body (request app :get url))))
        (is (= 400 (:status (request app :put url "{}"))))
        (is (= 404 (:status (request app :put "/books/9999" "{\"title\":\"T\",\"author\":\"A\"}"))))))))
