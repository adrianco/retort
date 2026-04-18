(ns brazilian-soccer-mcp.test-runner
  (:require [clojure.test :as test]
            ;; Load all test namespaces
            [brazilian-soccer-mcp.core-test])
  (:gen-class))

(defn -main [& _args]
  (let [result (test/run-tests 'brazilian-soccer-mcp.core-test)]
    (System/exit (if (and (zero? (:fail result 0))
                          (zero? (:error result 0)))
                   0 1))))
