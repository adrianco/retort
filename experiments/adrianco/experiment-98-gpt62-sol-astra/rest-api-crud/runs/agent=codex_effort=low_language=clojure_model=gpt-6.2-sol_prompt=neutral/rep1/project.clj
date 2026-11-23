(defproject book-api "0.1.0"
  :dependencies [[org.clojure/clojure "1.12.0"]
                 [ring/ring-jetty-adapter "1.13.0"]
                 [cheshire "5.13.0"]
                 [org.xerial/sqlite-jdbc "3.47.1.0"]]
  :main book-api.core
  :profiles {:uberjar {:aot [book-api.core]}})
