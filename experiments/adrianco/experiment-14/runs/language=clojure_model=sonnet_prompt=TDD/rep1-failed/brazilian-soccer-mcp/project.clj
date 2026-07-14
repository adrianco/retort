(defproject brazilian-soccer-mcp "0.1.0-SNAPSHOT"
  :description "MCP server for Brazilian soccer data queries"
  :license {:name "EPL-2.0 OR GPL-2.0-or-later WITH Classpath-exception-2.0"
            :url "https://www.eclipse.org/legal/epl-2.0/"}
  :dependencies [[org.clojure/clojure "1.12.2"]
                 [org.clojure/data.csv "1.1.0"]
                 [cheshire "5.13.0"]]
  :main ^:skip-aot brazilian-soccer-mcp.core
  :target-path "target/%s"
  :test-paths ["test"]
  :profiles {:uberjar {:aot :all
                       :jvm-opts ["-Dclojure.compiler.direct-linking=true"]}})
