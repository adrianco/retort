(ns brazilian-soccer-mcp.test-runner
  "Runs every test namespace. Start with: clojure -M:test"
  (:require [clojure.test :as t]
            [brazilian-soccer-mcp.normalize-test]
            [brazilian-soccer-mcp.data-test]
            [brazilian-soccer-mcp.query-test]
            [brazilian-soccer-mcp.mcp-test])
  (:gen-class))

(defn -main [& _]
  (let [{:keys [fail error]} (t/run-tests 'brazilian-soccer-mcp.normalize-test
                                          'brazilian-soccer-mcp.data-test
                                          'brazilian-soccer-mcp.query-test
                                          'brazilian-soccer-mcp.mcp-test)]
    (System/exit (if (zero? (+ fail error)) 0 1))))
