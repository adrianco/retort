(ns book-api.core-test
  (:require [clojure.test :refer :all]
            [book-api.core :as core]
            [book-api.db :as db]))

(defn with-db [f]
  (let [file (java.io.File/createTempFile "books-test" ".db")]
    (try
      (binding [db/*database-path* (.getAbsolutePath file)]
        (db/initialize!)
        (f))
      (finally
        (.delete file)))))

(use-fixtures :each with-db)

(deftest health-check
  (is (= 200 (:status (core/app {:request-method :get :uri "/health"}))))
  (is (= {:status "ok"} (:body (core/app {:request-method :get :uri "/health"})))))

(deftest create-validate-and-read-book
  (let [bad (core/app {:request-method :post :uri "/books" :body {:title "" :author "A"}})
        created (core/app {:request-method :post :uri "/books"
                           :body {:title "Dune" :author "Frank Herbert" :year 1965 :isbn "9780441172719"}})
        id (get-in created [:body :id])
        fetched (core/app {:request-method :get :uri (str "/books/" id)})]
    (is (= 400 (:status bad)))
    (is (= 201 (:status created)))
    (is (= "Dune" (get-in fetched [:body :title])))))

(deftest list-filter-update-and-delete
  (let [a (db/create-book! {:title "Dune" :author "Frank Herbert" :year 1965})
        _ (db/create-book! {:title "Foundation" :author "Isaac Asimov"})
        filtered (core/app {:request-method :get :uri "/books" :query-params {"author" "Herbert"}})
        id (:id a)
        updated (core/app {:request-method :put :uri (str "/books/" id)
                           :body {:title "Dune Messiah" :author "Frank Herbert"}})
        deleted (core/app {:request-method :delete :uri (str "/books/" id)})
        missing (core/app {:request-method :get :uri (str "/books/" id)})]
    (is (= 1 (count (:body filtered))))
    (is (= "Dune Messiah" (get-in updated [:body :title])))
    (is (= 204 (:status deleted)))
    (is (= 404 (:status missing)))))
