(ns brazilian-soccer-mcp.test-runner (:require [clojure.test :as test] [brazilian-soccer-mcp.core-test]))
(defn -main [& _] (let [r (test/run-tests 'brazilian-soccer-mcp.core-test)] (System/exit (if (test/successful? r) 0 1))))
