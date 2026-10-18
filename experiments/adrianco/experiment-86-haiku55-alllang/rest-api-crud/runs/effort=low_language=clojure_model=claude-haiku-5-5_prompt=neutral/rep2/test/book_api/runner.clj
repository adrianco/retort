(ns book-api.runner
  "Runs all book-api test namespaces. Exits non-zero on failure."
  (:require [clojure.test :as t]
            [book-api.handler-test]
            [book-api.validation-test]))

(defn -main [& _]
  (let [{:keys [fail error]} (t/run-tests 'book-api.handler-test 'book-api.validation-test)]
    (shutdown-agents)
    (System/exit (if (zero? (+ fail error)) 0 1))))
