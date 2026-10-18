(ns brazilian-soccer.test-runner
  "Runs every test namespace and exits non-zero on failure."
  (:require [clojure.test :as t]
            [brazilian-soccer.csv-test]
            [brazilian-soccer.json-test]
            [brazilian-soccer.names-test]
            [brazilian-soccer.data-test]
            [brazilian-soccer.queries-test]
            [brazilian-soccer.server-test]))

(defn -main [& _]
  (let [{:keys [fail error]} (t/run-tests 'brazilian-soccer.csv-test
                                          'brazilian-soccer.json-test
                                          'brazilian-soccer.names-test
                                          'brazilian-soccer.data-test
                                          'brazilian-soccer.queries-test
                                          'brazilian-soccer.server-test)]
    (shutdown-agents)
    (System/exit (if (zero? (+ fail error)) 0 1))))
