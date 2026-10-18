(ns books.runner
  (:require [clojure.test :as t]
            [books.api-test]))

(defn -main [& _]
  (let [{:keys [fail error]} (t/run-tests 'books.api-test)]
    (shutdown-agents)
    (System/exit (if (zero? (+ fail error)) 0 1))))
