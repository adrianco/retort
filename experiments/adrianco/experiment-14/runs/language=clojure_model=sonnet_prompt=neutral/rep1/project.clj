(defproject brazilian-soccer-mcp "0.1.0-SNAPSHOT"
  :description "MCP server for Brazilian soccer data"
  :dependencies [[org.clojure/clojure "1.11.3"]
                 [org.clojure/data.csv "1.1.0"]
                 [cheshire "5.13.0"]]
  :main ^:skip-aot brazilian-soccer-mcp.core
  :target-path "target/%s"
  :profiles {:uberjar {:aot :all
                       :jvm-opts ["-Dclojure.compiler.direct-linking=true"]}}
  :jvm-opts ["-Dfile.encoding=UTF-8"])
