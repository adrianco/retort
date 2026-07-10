(ns book-api.handler
  (:require [compojure.core :refer [defroutes GET POST PUT DELETE routing]]
            [ring.middleware.json :refer [wrap-json-body wrap-json-response]]
            [ring.middleware.params :refer [wrap-params]]
            [clojure.string :as string]
            [book-api.db :as db]))

(defn- book->response [book]
  (reduce (fn [m [k v]]
            (if (keyword? k)
              (assoc m (name k) v)
              (assoc m (str k) v)))
          {} book))

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
    :nil)

(defn- handle-errors [e]
  (let [msg (str (.getMessage e))]
    (if (and msg (.startsWith msg "Book with id ")
             (.endsWith msg "not found"))
      {:status 404 :body {:status 404 :error "Book not found"}}
      {:status 500 :body {:status 500 :error "Internal server error"}})))

(defn- handle-not-found-error []
  {:status 404
   :body {:status 404
          :error "Book not found"}})

(defn cors-response [response]
  (assoc-in response [:headers "Access-Control-Allow-Origin"] "*"))

(defn cors-wrap [handler]
  (fn [req]
    (if (= (:request-method req) :options)
      (let [response {:status 200
                      :headers {"Access-Control-Allow-Origin" "*"
                                "Access-Control-Allow-Methods" "GET,POST,PUT,DELETE,OPTIONS"
                                "Access-Control-Allow-Headers" "Content-Type,Accept"}}]
        response)
      (let [response (handler req)]
        (if response
          (cors-response response)
          {:status 404
           :body {:status 404 :error "Not found"}})))))

(defroutes book-routes
  (GET "/health" []
    {:status 200
     :body {:status "healthy"
            :timestamp (System/currentTimeMillis)}})

  (POST "/books" {body :body}
    (if-let [validation-error (validate-book body)]
      validation-error
      (try
        (let [[book] (db/add-book! body)]
          {:status 201
           :body {:status 201
                  :book (book->response book)}})
        (catch Exception e
          (handle-errors e)))))

  (GET "/books" [{:keys [params]}]
    (let [author (when (and params (:author params))
                   (:author params))]
      (try
        (let [books (db/list-books {:author author})]
          {:status 200
           :body {:status 200
                  :books (mapv book->response books)}})
        (catch Exception e
          (handle-errors e)))))

  (GET "/books/:id" [{:keys [route-params]}]
    (try
      (let [id (Long/parseLong (:id route-params))
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
      (catch Exception e
        (handle-errors e))))

  (PUT "/books/:id" [{:keys [route-params body]}]
    (try
      (let [id (Long/parseLong (:id route-params))
            result (db/update-book! id body)]
        {:status 200
         :body {:status 200
                :book (book->response result)}})
      (catch NumberFormatException _
        {:status 400
         :body {:status 400
                :error "Invalid book ID"}})
      (catch RuntimeException e
        (let [msg (str (.getMessage e))]
          (if (.contains msg "not found")
            (handle-not-found-error)
            {:status 500
             :body {:status 500
                    :error "Internal server error"}})))
      (catch Exception e
        (handle-errors e))))

  (DELETE "/books/:id" [{:keys [route-params]}]
    (try
      (let [id (Long/parseLong (:id route-params))
            book (db/delete-book! id)]
        {:status 200
         :body {:status 200
                :book (book->response book)}})
      (catch NumberFormatException _
        {:status 400
         :body {:status 400
                :error "Invalid book ID"}})
      (catch RuntimeException e
        (let [msg (str (.getMessage e))]
          (if (.contains msg "not found")
            (handle-not-found-error)
            {:status 500
             :body {:status 500
                    :error "Internal server error"}})))
      (catch Exception e
        (handle-errors e)))))

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
      wrap-json-body {:keywords? true}
      wrap-json-response
      catch-all
      cors-wrap))
