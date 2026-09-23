(ns books.core
  (:require [books.db :as db]
            [cheshire.core :as json]
            [clojure.string :as str]
            [compojure.core :refer [routes GET POST PUT DELETE]]
            [compojure.route :as route]
            [ring.adapter.jetty :refer [run-jetty]]
            [ring.middleware.params :refer [wrap-params]])
  (:gen-class))

(defn json-resp [status body]
  {:status status
   :headers {"Content-Type" "application/json"}
   :body (json/generate-string body)})

(defn parse-body [req]
  (try (let [b (some-> (:body req) slurp)]
         (if (str/blank? b) {} (json/parse-string b true)))
       (catch Exception _ ::invalid)))

(defn validate [b]
  (cond
    (not (map? b)) ["Request body must be a JSON object"]
    :else
    (cond-> []
      (not (and (string? (:title b)) (not (str/blank? (:title b))))) (conj "title is required")
      (not (and (string? (:author b)) (not (str/blank? (:author b))))) (conj "author is required")
      (and (some? (:year b)) (not (integer? (:year b)))) (conj "year must be an integer")
      (and (some? (:isbn b)) (not (string? (:isbn b)))) (conj "isbn must be a string"))))

(defn parse-id [s] (try (Long/parseLong s) (catch Exception _ nil)))

(defn with-book-input [req f]
  (let [b (parse-body req)
        errs (validate b)]
    (if (seq errs)
      (json-resp 400 {:errors errs})
      (f (select-keys b [:title :author :year :isbn])))))

(defn with-id [id f]
  (if-let [id (parse-id id)] (f id) (json-resp 404 {:error "Book not found"})))

(defn app [ds]
  (wrap-params
   (routes
    (GET "/health" [] (json-resp 200 {:status "ok"}))
    (GET "/books" req
      (let [a (get-in req [:query-params "author"])]
        (json-resp 200 (db/list-books ds (when-not (str/blank? a) a)))))
    (POST "/books" req
      (with-book-input req #(json-resp 201 (db/create-book! ds %))))
    (GET "/books/:id" [id]
      (with-id id #(if-let [b (db/get-book ds %)]
                     (json-resp 200 b)
                     (json-resp 404 {:error "Book not found"}))))
    (PUT "/books/:id" [id :as req]
      (with-id id (fn [id]
                    (with-book-input req
                      #(if-let [b (db/update-book! ds id (merge {:year nil :isbn nil} %))]
                         (json-resp 200 b)
                         (json-resp 404 {:error "Book not found"}))))))
    (DELETE "/books/:id" [id]
      (with-id id #(if (db/delete-book! ds %)
                     {:status 204 :headers {} :body ""}
                     (json-resp 404 {:error "Book not found"}))))
    (route/not-found (json-resp 404 {:error "Not found"})))))

(defn -main [& _]
  (let [port (Integer/parseInt (or (System/getenv "PORT") "3000"))
        ds (db/make-ds (or (System/getenv "DB_PATH") "books.db"))]
    (println "Listening on port" port)
    (run-jetty (app ds) {:port port :join? true})))
