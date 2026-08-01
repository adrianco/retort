(ns book-service.core-test
  (:require [book-service.core :as core]
            [cheshire.core :as json]
            [clojure.string :as string]
            [clojure.test :refer [deftest is testing]])
  (:import [java.io ByteArrayInputStream]
           [java.nio.charset StandardCharsets]
           [java.nio.file Files]))

(defn temporary-app []
  (let [file (Files/createTempFile "books-test-" ".sqlite" (make-array java.nio.file.attribute.FileAttribute 0))]
    [(core/app (str "jdbc:sqlite:" file)) file]))

(defn request [app method uri & [body]]
  (let [[path query-string] (string/split uri #"\?" 2)]
    (app {:request-method method :uri path :query-string query-string
        :headers {"content-type" "application/json"}
        :body (when body (ByteArrayInputStream. (.getBytes (json/generate-string body) StandardCharsets/UTF_8)))})))

(defn response-json [response] (json/parse-string (:body response) true))

(deftest health-endpoint-test
  (let [[app _] (temporary-app)]
    (is (= {:status "ok"} (response-json (request app :get "/health"))))))

(deftest create-list-and-filter-books-test
  (let [[app _] (temporary-app)]
    (is (= 201 (:status (request app :post "/books" {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441172719"}))))
    (request app :post "/books" {:title "Beloved" :author "Toni Morrison"})
    (is (= 2 (count (response-json (request app :get "/books")))))
    (is (= ["Dune"] (mapv :title (response-json (request app :get "/books?author=Frank+Herbert")))))))

(deftest update-delete-and-validation-test
  (let [[app _] (temporary-app)
        create (request app :post "/books" {:title "Old" :author "Author"})
        id (:id (response-json create))]
    (is (= 400 (:status (request app :post "/books" {:title "Missing author"}))))
    (is (= "New" (:title (response-json (request app :put (str "/books/" id) {:title "New" :author "Author" :year 2020})))))
    (is (= 204 (:status (request app :delete (str "/books/" id)))))
    (is (= 404 (:status (request app :get (str "/books/" id)))))))
