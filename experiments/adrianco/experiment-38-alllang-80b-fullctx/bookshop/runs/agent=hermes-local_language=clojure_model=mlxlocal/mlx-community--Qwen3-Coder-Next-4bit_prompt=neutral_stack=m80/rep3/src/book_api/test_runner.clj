(ns book-api.test-runner
  (:require [clojure.test :refer :all]
            [book-api.test-db]
            [book-api.test-routes]))

(defn -main []
  (run-tests))
