(ns books-test
  (:require [books :as books]
            [clojure.data.json :as json]
            [clojure.test :refer [deftest is use-fixtures run-tests]])
  (:import [java.io ByteArrayInputStream File]))

(def ^:dynamic *app*)
(def ^:dynamic *path*)

(use-fixtures :each
  (fn [test-fn]
    (let [file (File/createTempFile "books-test" ".sqlite")]
      (try
        (binding [*path* (.getPath file) *app* (books/handler (books/open-db (.getPath file)))]
          (test-fn))
        (finally (.delete file))))))

(defn request [method uri & [data query]]
  (let [raw (if (string? data) data (json/write-str data))
        result (*app* {:request-method method :uri uri :query-string query
                       :body (ByteArrayInputStream. (.getBytes raw "UTF-8"))})]
    (update result :body #(json/read-str % :key-fn keyword))))

(def book {:title "Kindred" :author "Octavia Butler" :year 1979 :isbn "001"})

(deftest lifecycle
  (let [{:keys [status headers body]} (request :post "/books" book)
        uri (get headers "Location")]
    (is (= 201 status))
    (is (= book (dissoc body :id)))
    (binding [*app* (books/handler (books/open-db *path*))]
      (is (= body (:body (request :get uri)))))
    (let [changed (assoc body :year 1980)]
      (is (= changed (:body (request :put uri changed))))
      (is (= changed (:body (request :get uri)))))
    (is (= 200 (:status (request :delete uri))))
    (doseq [method [:get :put :delete]]
      (is (= 404 (:status (request method uri book)))))))

(deftest listing
  (request :post "/books" book)
  (request :post "/books" (assoc book :author "Other"))
  (is (= 2 (count (:body (request :get "/books")))))
  (is (= [book] (map #(dissoc % :id)
                     (:body (request :get "/books" nil "author=Octavia+Butler")))))
  (is (= [] (:body (request :get "/books" nil "author=Nobody")))))

(deftest validation
  (doseq [bad ["{" "{} garbage" {} {:author "A"} {:title "T" :author " "}
               (assoc book :year "1979") (assoc book :isbn 123)]]
    (is (= 400 (:status (request :post "/books" bad)))))
  (is (= [] (:body (request :get "/books"))))
  (let [uri (get-in (request :post "/books" book) [:headers "Location"])]
    (is (= 400 (:status (request :put uri {}))))
    (is (= book (dissoc (:body (request :get uri)) :id)))))

(deftest health-and-routing
  (is (= {:status "ok"} (:body (request :get "/health"))))
  (is (= 405 (:status (request :delete "/books"))))
  (is (= 404 (:status (request :get "/other")))))

(defn -main [& _]
  (let [{:keys [fail error]} (run-tests 'books-test)]
    (System/exit (if (zero? (+ fail error)) 0 1))))
