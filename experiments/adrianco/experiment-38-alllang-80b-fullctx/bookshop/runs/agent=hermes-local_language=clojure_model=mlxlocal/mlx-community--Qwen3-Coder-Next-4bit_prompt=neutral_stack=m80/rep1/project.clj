(defproject book-api "0.1.0-SNAPSHOT"
  :description "REST API service for managing a book collection"
  :url "http://example.com/book-api"
  :license {:name "MIT"
            :url "https://opensource.org/licenses/MIT"}
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [compojure "1.7.1"]
                 [ring/ring-core "1.13.0"]
                 [ring/ring-jetty-adapter "1.13.0"]
                 [ring/ring-json "0.5.1"]
                 [clj-jgit "1.0.7"]
                 [org.xerial/sqlite-jdbc "3.45.1.0"]
                 [hugsql "0.5.1"]
                 [cheshire "5.13.0"]
                 [metosin/ring-http-response "0.9.2"]
                 [prismatic/schema "1.1.12"]
                 [org.clojure/test.check "1.1.1"]]
  :main book-api.core
  :plugins [[lein-hugsql "0.5.1"]]
  :target-path "target"
  :profiles {:uberjar {:aot :all
                       :source-paths ["env/prod"]
                       :prep-tasks ["compile" ["hugsql" :db-sql "resources/db.sql"]]
                       :global-vars {*warn-on-reflection* true
                                     *assert* true}
                       :jvm-opts ["-Dserver.port=3000" "-Dclojure.wall=:warn"]}
             :dev {:source-paths ["env/dev" "src" "test"]
                   :prep-tasks ["compile" ["hugsql" :db-sql "resources/db.sql"]]
                   :global-vars {*warn-on-reflection* false
                                 *assert* true}}})
