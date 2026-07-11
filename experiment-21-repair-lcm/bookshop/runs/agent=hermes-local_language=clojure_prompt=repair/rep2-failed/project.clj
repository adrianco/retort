(defproject bookapi "0.1.0-SNAPSHOT"
  :description "REST API for managing a book collection"
  :url "https://github.com/example/bookapi"
  :license {:name "EPL-2.0"
            :url "https://www.eclipse.org/legal/epl-v20.html"}
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [compojure "1.7.1"]
                 [ring/ring-json "0.5.1"]
                 [ring/ring-mock "0.4.0"]
                 [org.clojure/java.jdbc "0.7.12"]
                 [org.xerial/sqlite-jdbc "3.46.1.3"]]
  :repl-options {:init-ns bookapi.core}
  :main ^:skip-aot bookapi.core
  :target-path "target/%s"
  :profiles
  {:dev {:dependencies [[pjstadig/humane-test-output "0.11.0"]]}})
