(defproject book-api "0.1.0-SNAPSHOT"
  :description "REST API for managing a book collection"
  :url "http://example.com/book-api"
  :license {:name "EPL-2.0-or-later"
            :url "http://www.eclipse.org/legal/epl-2.0"}
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [org.clojure/java.jdbc "0.7.12"]
                 [ring/ring-core "1.12.1"]
                 [ring/ring-jetty-adapter "1.12.1"]
                 [cheshire "5.11.0"]
                 [org.xerial/sqlite-jdbc "3.45.1.0"]]
  :main book-api.core
  :aot [book-api.core])
