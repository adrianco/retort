(ns book-api.test-runner
  (:require [clojure.test :as test]
            [book-api.core-test]))

(defn -main [& _]
  (let [result (test/run-tests 'book-api.core-test)]
    (when (pos? (+ (:fail result) (:error result)))
      (System/exit 1))))
