(ns book-api.api-test
  "Integration tests driving the Ring handler end to end against SQLite."
  (:require [book-api.test-support :as ts :refer [create! json-body request]]
            [clojure.test :refer [deftest is testing use-fixtures]]))

(use-fixtures :each ts/with-test-db)

(def dune {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441013593"})
(def emma {:title "Emma" :author "Jane Austen" :year 1815 :isbn "9780141439587"})

;; ---------------------------------------------------------------------------

(deftest health-check
  (let [response (request :get "/health")]
    (is (= 200 (:status response)))
    (is (= {:status "ok" :database "up"} (json-body response)))))

(deftest create-book
  (testing "a valid payload is stored and echoed back with an id"
    (let [response (request :post "/books" dune)
          body     (json-body response)]
      (is (= 201 (:status response)))
      (is (pos-int? (:id body)))
      (is (= "Dune" (:title body)))
      (is (= "Frank Herbert" (:author body)))
      (is (= 1965 (:year body)))
      (is (= "9780441013593" (:isbn body)))
      (is (= (str "/books/" (:id body)) (get-in response [:headers "Location"])))))

  (testing "year and isbn are optional"
    (let [response (request :post "/books" {:title "Untitled" :author "Anon"})
          body     (json-body response)]
      (is (= 201 (:status response)))
      (is (nil? (:year body)))
      (is (nil? (:isbn body)))))

  (testing "whitespace around text fields is trimmed"
    (let [body (create! {:title "  Neuromancer " :author " William Gibson  "})]
      (is (= "Neuromancer" (:title body)))
      (is (= "William Gibson" (:author body))))))

(deftest create-book-validation
  (testing "title and author are required"
    (doseq [[label payload expected-fields]
            [["missing both"   {}                                    #{"title" "author"}]
             ["missing title"  {:author "Anon"}                      #{"title"}]
             ["missing author" {:title "Untitled"}                   #{"author"}]
             ["blank title"    {:title "   " :author "Anon"}         #{"title"}]
             ["blank author"   {:title "Untitled" :author ""}        #{"author"}]
             ["non-string"     {:title 42 :author "Anon"}            #{"title"}]]]
      (testing label
        (let [response (request :post "/books" payload)
              body     (json-body response)]
          (is (= 400 (:status response)))
          (is (= "Validation failed" (:error body)))
          (is (= expected-fields (set (map :field (:details body)))))))))

  (testing "year must be a plausible integer"
    (doseq [year ["not-a-year" 0 9999 3.5]]
      (let [response (request :post "/books" (assoc dune :year year :isbn nil))]
        (is (= 400 (:status response)) (str "year " (pr-str year))))))

  (testing "no book is persisted when validation fails"
    (request :post "/books" {:author "Anon"})
    (is (= [] (json-body (request :get "/books")))))

  (testing "a malformed JSON body is rejected"
    (let [response (ts/raw-request :post "/books" "{not json")]
      (is (= 400 (:status response)))
      (is (= "Malformed JSON in request body" (:error (json-body response))))))

  (testing "a duplicate isbn is a conflict"
    (create! dune)
    (is (= 409 (:status (request :post "/books" (assoc dune :title "Dune reprint")))))))

(deftest list-books
  (testing "an empty collection is an empty array"
    (is (= [] (json-body (request :get "/books")))))

  (testing "all books are returned in insertion order"
    (create! dune)
    (create! emma)
    (let [response (request :get "/books")
          body     (json-body response)]
      (is (= 200 (:status response)))
      (is (= ["Dune" "Emma"] (map :title body)))))

  (testing "?author= filters, case-insensitively"
    (create! (assoc dune :title "Dune Messiah" :isbn "9780575074903"))
    (is (= ["Dune" "Dune Messiah"]
           (map :title (json-body (request :get "/books?author=Frank%20Herbert")))))
    (is (= ["Dune" "Dune Messiah"]
           (map :title (json-body (request :get "/books?author=frank+herbert")))))
    (is (= ["Emma"]
           (map :title (json-body (request :get "/books?author=Jane%20Austen")))))
    (is (= [] (json-body (request :get "/books?author=Nobody"))))))

(deftest get-book-by-id
  (let [created (create! dune)]
    (testing "an existing book is returned"
      (let [response (request :get (str "/books/" (:id created)))]
        (is (= 200 (:status response)))
        (is (= created (json-body response)))))

    (testing "an unknown id is a 404"
      (let [response (request :get "/books/9999")]
        (is (= 404 (:status response)))
        (is (= "Book not found" (:error (json-body response))))))

    (testing "a non-numeric id is a 404, not a 500"
      (is (= 404 (:status (request :get "/books/abc")))))))

(deftest update-book
  (let [created (create! dune)
        id      (:id created)]
    (testing "a valid update replaces the stored fields"
      (let [response (request :put (str "/books/" id)
                              {:title "Dune (Deluxe Edition)"
                               :author "Frank Herbert"
                               :year 2019
                               :isbn "9780441013593"})
            body     (json-body response)]
        (is (= 200 (:status response)))
        (is (= id (:id body)))
        (is (= "Dune (Deluxe Edition)" (:title body)))
        (is (= 2019 (:year body))))
      (is (= "Dune (Deluxe Edition)"
             (:title (json-body (request :get (str "/books/" id)))))))

    (testing "optional fields can be cleared"
      (let [body (json-body (request :put (str "/books/" id)
                                     {:title "Dune" :author "Frank Herbert"}))]
        (is (nil? (:year body)))
        (is (nil? (:isbn body)))))

    (testing "validation applies to updates too"
      (let [response (request :put (str "/books/" id) {:title "" :author "Frank Herbert"})]
        (is (= 400 (:status response)))
        (is (= ["title"] (map :field (:details (json-body response)))))))

    (testing "updating an unknown id is a 404"
      (is (= 404 (:status (request :put "/books/9999" dune)))))

    (testing "keeping your own isbn is fine, stealing another book's is a conflict"
      (create! emma)
      (is (= 200 (:status (request :put (str "/books/" id) dune))))
      (is (= 409 (:status (request :put (str "/books/" id) (assoc emma :title "Clash"))))))))

(deftest delete-book
  (let [id (:id (create! dune))]
    (testing "deleting returns 204 with no body"
      (let [response (request :delete (str "/books/" id))]
        (is (= 204 (:status response)))
        (is (nil? (:body response)))))

    (testing "the book is really gone"
      (is (= 404 (:status (request :get (str "/books/" id)))))
      (is (= [] (json-body (request :get "/books")))))

    (testing "deleting twice is a 404"
      (is (= 404 (:status (request :delete (str "/books/" id))))))))

(deftest unknown-route
  (let [response (request :get "/nope")]
    (is (= 404 (:status response)))
    (is (= "Not found" (:error (json-body response))))))

(deftest responses-are-json
  (doseq [uri ["/health" "/books"]]
    (is (= "application/json; charset=utf-8"
           (get-in (request :get uri) [:headers "Content-Type"]))
        uri)))

(deftest errors-become-500-not-exceptions
  (testing "an unexpected failure is reported as JSON rather than escaping"
    (with-redefs [book-api.db/list-books (fn [& _] (throw (ex-info "boom" {})))]
      (let [response (request :get "/books")]
        (is (= 500 (:status response)))
        (is (= "Internal server error" (:error (json-body response))))))))
