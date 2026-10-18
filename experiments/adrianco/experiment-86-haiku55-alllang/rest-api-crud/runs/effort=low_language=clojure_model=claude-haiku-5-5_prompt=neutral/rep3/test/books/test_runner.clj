(ns books.test-runner
  (:require [clojure.test :as t]
            [books.api-test]
            [books.validation-test]))

(defn -main [& _]
  (let [{:keys [fail error]} (t/run-tests 'books.api-test 'books.validation-test)]
    (System/exit (if (zero? (+ fail error)) 0 1))))
