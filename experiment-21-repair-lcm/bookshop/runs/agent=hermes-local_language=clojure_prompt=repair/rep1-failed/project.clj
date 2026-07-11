(defproject book-api "0.1.0-SNAPSHOT"
  :description "REST API service for managing a book collection"
  :test-paths ["test"]
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [com.github.seancorfield/next.jdbc "1.3.1118"]
                 [org.xerial/sqlite-jdbc "3.41.2.2"]
                 [compojure "1.7.1"]
                 [ring/ring-jetty-adapter "1.9.6"]
                 [ring/ring-json "0.5.1"]
                 [org.clojure/data.json "2.5.0"]
                 [midje "1.10.0"]])
