(ns run-tests
  (:require [clojure.test :as t]
            [book-api.core-test]))

(defn -main [& _args]
  (let [{:keys [fail error]} (t/run-all-tests #"book-api\..*")]
    (System/exit (if (zero? (+ fail error)) 0 1))))
