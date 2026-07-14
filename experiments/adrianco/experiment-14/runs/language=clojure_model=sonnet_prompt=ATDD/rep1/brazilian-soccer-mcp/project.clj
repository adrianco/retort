(defproject brazilian-soccer-mcp "0.1.0-SNAPSHOT"
  :description "MCP server for Brazilian soccer data"
  :license {:name "EPL-2.0"}
  :dependencies [[org.clojure/clojure "1.12.2"]
                 [org.clojure/data.csv "1.1.0"]
                 [cheshire "5.12.0"]]
  :main ^:skip-aot brazilian-soccer-mcp.core
  :target-path "target/%s"
  :profiles {:uberjar {:aot :all
                       :jvm-opts ["-Dclojure.compiler.direct-linking=true"]}})
