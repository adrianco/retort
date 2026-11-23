(ns book-api.core-test
  (:require [book-api.core :as api]
            [cheshire.core :as json]
            [clojure.test :refer [deftest is use-fixtures]])
  (:import [java.io ByteArrayInputStream File]
           [java.nio.charset StandardCharsets]))

(def ^:dynamic *db-url*)
(def ^:dynamic *app*)

(use-fixtures :each
  (fn [test]
    (let [file (File/createTempFile "book-api-test-" ".sqlite")
          url (str "jdbc:sqlite:" (.getPath file))]
      (try
        (binding [*db-url* url
                  *app* (api/make-app url)]
          (test))
        (finally (.delete file))))))

(defn- request
  ([method uri] (request method uri nil nil))
  ([method uri body] (request method uri body nil))
  ([method uri body query-string]
   (let [{:keys [body] :as response}
         (*app* {:request-method method
                 :uri uri
                 :query-string query-string
                 :headers {"content-type" "application/json"}
                 :body (when body
                         (ByteArrayInputStream.
                          (.getBytes ^String body StandardCharsets/UTF_8)))})]
     (assoc response :body (some-> body (json/parse-string true))))))

(def sample-book
  {:title "Kindred" :author "Octavia E. Butler" :year 1979 :isbn "9780807083697"})

(deftest book-lifecycle
  (let [{:keys [status headers body]} (request :post "/books" (json/generate-string sample-book))
        path (get headers "Location")
        id (:id body)]
    (is (= 201 status))
    (is (= (str "/books/" id) path))
    (is (= (assoc sample-book :id id) body))
    (is (= body (:body (request :get path))))
    (let [replacement {:title "Parable of the Sower" :author "Octavia E. Butler" :year 1993}
          updated (request :put path (json/generate-string replacement))]
      (is (= 200 (:status updated)))
      (is (= (assoc replacement :id id :isbn nil) (:body updated)))
      (is (= (:body updated) (:body (request :get path)))))
    (is (= {:status 204 :headers {} :body nil} (request :delete path)))
    (is (= 404 (:status (request :get path))))
    (is (= 404 (:status (request :delete path))))
    (is (= 404 (:status (request :put path (json/generate-string sample-book)))))))

(deftest listing-and-author-filter
  (is (= [] (:body (request :get "/books"))))
  (let [first-book (:body (request :post "/books" (json/generate-string sample-book)))
        second-book (:body (request :post "/books" "{\"title\":\"Dune\",\"author\":\"Frank Herbert\"}"))]
    (is (= [first-book second-book] (:body (request :get "/books"))))
    (is (= [first-book] (:body (request :get "/books" nil "author=Octavia+E.+Butler"))))
    (is (= [] (:body (request :get "/books" nil "author=Unknown"))))))

(deftest validates-create-and-update
  (let [created (request :post "/books" (json/generate-string sample-book))
        path (get-in created [:headers "Location"])]
    (doseq [body ["{" "[]" "{}"
                  "{\"title\":\" \",\"author\":\"Author\"}"
                  "{\"title\":\"Title\",\"author\":12}"
                  "{\"title\":\"Title\",\"author\":\"Author\",\"year\":\"2020\"}"
                  "{\"title\":\"Title\",\"author\":\"Author\",\"isbn\":12}"]]
      (is (= 400 (:status (request :post "/books" body))) body)
      (is (= 400 (:status (request :put path body))) body))
    (is (= [(:body created)] (:body (request :get "/books"))))))

(deftest database-persists-across-app-instances
  (let [created (request :post "/books" (json/generate-string sample-book))]
    (binding [*app* (api/make-app *db-url*)]
      (is (= [(:body created)] (:body (request :get "/books")))))))

(deftest health-and-routing
  (let [{:keys [status headers body]} (request :get "/health")]
    (is (= 200 status))
    (is (= "application/json; charset=utf-8" (get headers "Content-Type")))
    (is (= {:status "ok"} body)))
  (is (= 404 (:status (request :get "/books/999999999999999999999"))))
  (is (= 404 (:status (request :get "/unknown"))))
  (let [{:keys [status headers]} (request :delete "/books")]
    (is (= 405 status))
    (is (= "GET, POST" (get headers "Allow")))))
