(defproject books-api "0.1.0-SNAPSHOT"
  :description "REST API for managing a book collection"
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [ring/ring-core "1.11.0"]
                 [ring/ring-jetty-adapter "1.11.0"]
                 [ring/ring-json "0.5.1"]
                 [compojure "1.7.1"]
                 [cheshire "5.12.0"]
                 [com.github.seancorfield/next.jdbc "1.3.909"]
                 [org.xerial/sqlite-jdbc "3.45.1.0"]
                 [ring/ring-mock "0.4.0"]]
  :main ^:skip-aot books-api.core
  :target-path "target/%s"
  :profiles {:uberjar {:aot :all
                       :jvm-opts ["-Dclojure.compiler.direct-linking=true"]}})
