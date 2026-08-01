(ns book-service.test-runner
  (:require [clojure.test :as test]
            [book-service.core-test]))

(defn -main [& _]
  (let [result (test/run-tests 'book-service.core-test)]
    (when (pos? (+ (:fail result) (:error result)))
      (System/exit 1))))
