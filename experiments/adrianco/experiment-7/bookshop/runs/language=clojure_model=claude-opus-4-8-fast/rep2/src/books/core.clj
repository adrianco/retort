(ns books.core
  "HTTP server, routing and middleware wiring for the book collection API."
  (:require [books.db :as db]
            [books.handlers :as h]
            [cheshire.core :as json]
            [reitit.ring :as ring]
            [ring.adapter.jetty :as jetty]
            [ring.middleware.params :as params])
  (:gen-class))

(defn- wrap-json
  "Parse JSON request bodies into :body-params (keyword keys) and encode
  every response body as JSON with a proper content type."
  [handler]
  (fn [request]
    (let [body-str (some-> (:body request) slurp)
          parsed   (when (seq body-str)
                     (try (json/parse-string body-str true)
                          (catch Exception _ ::invalid)))]
      (if (= parsed ::invalid)
        {:status 400
         :headers {"Content-Type" "application/json"}
         :body (json/generate-string {:errors ["invalid JSON body"]})}
        (let [response (handler (assoc request :body-params parsed))]
          (-> response
              (assoc-in [:headers "Content-Type"] "application/json")
              (update :body #(if (nil? %) "" (json/generate-string %)))))))))

(defn app
  "Build the Ring handler around the given datasource."
  [ds]
  (ring/ring-handler
    (ring/router
      [["/health" {:get h/health}]
       ["/books"  {:get  (h/list-books ds)
                   :post (h/create-book ds)}]
       ["/books/:id" {:get    (h/get-book ds)
                      :put    (h/update-book ds)
                      :delete (h/delete-book ds)}]]
      {:data {:middleware [params/wrap-params wrap-json]}})
    (ring/create-default-handler
      {:not-found (constantly
                    {:status 404
                     :headers {"Content-Type" "application/json"}
                     :body (json/generate-string {:error "not found"})})})))

(defn start-server
  "Initialise the database and start a Jetty server. Returns the server."
  [{:keys [port db-path join?] :or {port 3000 db-path "books.db" join? true}}]
  (let [ds (db/datasource db-path)]
    (db/init! ds)
    (println (str "Starting books API on port " port " (db: " db-path ")"))
    (jetty/run-jetty (app ds) {:port port :join? join?})))

(defn -main
  [& args]
  (let [port (if-let [p (first args)] (Long/parseLong p) 3000)]
    (start-server {:port port})))
