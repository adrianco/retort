(ns book-api.test-all
  (:require [clojure.test :refer :all]
            [book-api.test-db]
            [book-api.test-routes]))

(run-tests)
