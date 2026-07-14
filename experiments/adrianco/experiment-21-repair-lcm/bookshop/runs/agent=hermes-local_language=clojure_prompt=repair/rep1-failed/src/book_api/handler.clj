(ns book-api.handler
  (:require [compojure.core :refer [defroutes GET POST PUT DELETE]]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [ring.middleware.params :refer [wrap-params]]
            [clojure.string :as string]
            [book-api.db :as db]))

(defn- book->response [book]
  (into {} (map (fn [[k v]]
                  [(name k) v])
                book)))

(defn- validate-book [data]
  (cond
    (or (nil? (:title data))
        (string/blank? (str (:title data))))
    {:status 400
     :body {:status 400
            :error "Validation failed"
            :fields {:title ["Title is required"]}}}
    (or (nil? (:author data))
        (string/blank? (str (:author data))))
    {:status 400
     :body {:status 400
            :error "Validation failed"
            :fields {:author ["Author is required"]}}}
    :else
    nil))

(defn- handle-not-found-error []
  {:status 404
   :body {:status 404
          :error "Book not found"}})

(defn cors-wrap [handler]
  (fn [req]
    (if (= (:request-method req) :options)
      {:status 200
       :headers {"Access-Control-Allow-Origin" "*"
                 "Access-Control-Allow-Methods" "GET,POST,PUT,DELETE,OPTIONS"
                 "Access-Control-Allow-Headers" "Content-Type,Accept"}}
      (let [response (handler req)]
        (if response
          (assoc-in response [:headers "Access-Control-Allow-Origin"] "*")
          {:status 404
           :body {:status 404 :error "Not found"}})))))

(defroutes book-routes
  (GET "/health" []
    {:status 200
     :body {:status "healthy"
            :timestamp (System/currentTimeMillis)}})

  (POST "/books" [request]
    (let [body (:body request)]
      (if-let [validation-error (validate-book body)]
        validation-error
        (try
          (let [[book] (db/add-book! body)]
            {:status 201
             :body {:status 201
                    :book (book->response book)}})
          (catch RuntimeException e
            (if (.contains (.getMessage e) "not found")
              (handle-not-found-error)
              {:status 500
               :body {:status 500
                      :error "Internal server error"}}))))))

  (GET "/books" [request]
    (let [params (:params request)
          author (:author params)]
      (try
        (let [books (db/list-books {:author author})]
          {:status 200
           :body {:status 200
                  :books (mapv book->response books)}})
        (catch Exception e
          {:status 500
           :body {:status 500
                  :error "Internal server error"}}))))

  (GET "/books/:id" [request]
    (try
      (let [id (Long/parseLong (str (:id request)))
            book (db/get-book! id)]
        (if book
          {:status 200
           :body {:status 200
                  :book (book->response book)}}
          (handle-not-found-error)))
      (catch NumberFormatException _
        {:status 400
         :body {:status 400
                :error "Invalid book ID"}})
      (catch RuntimeException e
        (if (.contains (.getMessage e) "not found")
          (handle-not-found-error)
          {:status 500
           :body {:status 500
                  :error "Internal server error"}}))))

  (PUT "/books/:id" [request]
    (try
      (let [id (Long/parseLong (str (:id request)))
            body (:body request)
            result (db/update-book! id body)]
        {:status 200
         :body {:status 200
                :book (book->response result)}})
      (catch NumberFormatException _
        {:status 400
         :body {:status 400
                :error "Invalid book ID"}})
      (catch RuntimeException e
        (if (.contains (.getMessage e) "not found")
          (handle-not-found-error)
          {:status 500
           :body {:status 500
                  :error "Internal server error"}}))))

  (DELETE "/books/:id" [request]
    (try
      (let [id (Long/parseLong (str (:id request)))
            book (db/delete-book! id)]
        {:status 200
         :body {:status 200
                :book (book->response book)}})
      (catch NumberFormatException _
        {:status 400
         :body {:status 400
                :error "Invalid book ID"}})
      (catch RuntimeException e
        (if (.contains (.getMessage e) "not found")
          (handle-not-found-error)
          {:status 500
           :body {:status 500
                  :error "Internal server error"}})))))

(defn- not-found-handler [_]
  {:status 404
   :body {:status 404
          :error "Not found"}})

(defn- catch-all [handler]
  (fn [req]
    (let [response (handler req)]
      (if (= 404 (:status response))
        (not-found-handler req)
        response))))

(def app
  (-> book-routes
      wrap-params
      (wrap-json-body {:keywords? true})
      wrap-json-response
      catch-all
      cors-wrap))
