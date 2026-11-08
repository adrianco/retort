(ns books.test-runner
  (:require [clojure.test :as test]
            [books.core-test]))

(defn -main [& _]
  (let [result (test/run-tests 'books.core-test)]
    (when (pos? (+ (:fail result) (:error result)))
      (System/exit 1))))
