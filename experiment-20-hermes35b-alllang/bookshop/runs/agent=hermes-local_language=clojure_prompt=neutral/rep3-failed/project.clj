(defproject book-api "0.1.0-SNAPSHOT"
  :description "A REST API service for managing a book collection"
  :url "https://example.com/book-api"
  :license {:name "EPL-2.0 OR GPL-2.0-or-later WITH Classpath-exception-2.0"
            :url "https://www.eclipse.org/legal/epl-2.0/"}
  :dependencies [[org.clojure/clojure "1.12.2"]
                 [compojure/compojure "1.7.2"]
                 [ring/ring-defaults "0.3.2"]
                 [ring/ring-json "0.5.1"]
                 [ring/ring-jetty-adapter "1.15.5"]
                 [ring/ring-mock "0.6.2"]
                 [cheshire/cheshire "6.2.0"]
                 ["org.clojure/java.jdbc" "0.7.12"]
                 ["org.xerial/sqlite-jdbc" "3.46.1.3"]]
  :main ^:skip-aot book-api.core
  :target-path "target/%s"
  :profiles {:uberjar {:aot :all
                       :jvm-opts ["-Dclojure.compiler.direct-linking=true"]}})
