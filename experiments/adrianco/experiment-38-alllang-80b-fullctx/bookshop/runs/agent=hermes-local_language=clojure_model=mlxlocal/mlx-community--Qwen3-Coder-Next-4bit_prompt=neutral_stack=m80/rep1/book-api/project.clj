(defproject book-api "0.1.0-SNAPSHOT"
  :description "REST API service for managing a book collection"
  :url "http://example.com/book-api"
  :license {:name "MIT"
            :url "https://opensource.org/licenses/MIT"}
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [org.clojure/java.jdbc "0.7.12"]
                 [compojure "1.7.1"]
                 [ring/ring-core "1.13.0"]
                 [ring/ring-jetty-adapter "1.13.0"]
                 [ring/ring-json "0.5.1"]
                 [org.xerial/sqlite-jdbc "3.45.1.0"]
                 [cheshire "5.13.0"]
                 [metosin/ring-http-response "0.9.2"]
                 [prismatic/schema "1.1.12"]]
  :main book-api.core
  :target-path "target"
  :profiles {:uberjar {:aot :all
                       :jvm-opts ["-Dserver.port=3000" "-Dclojure.wall=:warn"]}
             :dev {:source-paths ["env/dev" "src" "test"]}})
