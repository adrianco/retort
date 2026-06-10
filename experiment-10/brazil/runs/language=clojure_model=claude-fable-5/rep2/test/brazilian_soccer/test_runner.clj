(ns brazilian-soccer.test-runner
  "Runs all test namespaces. Invoke with: clojure -M:test"
  (:require [clojure.test :as t]
            [brazilian-soccer.data-test]
            [brazilian-soccer.query-test]
            [brazilian-soccer.server-test]
            [brazilian-soccer.acceptance-test]))

(defn -main [& _]
  (let [{:keys [fail error]} (t/run-tests 'brazilian-soccer.data-test
                                          'brazilian-soccer.query-test
                                          'brazilian-soccer.server-test
                                          'brazilian-soccer.acceptance-test)]
    (System/exit (if (zero? (+ fail error)) 0 1))))
