(ns soccer.test-runner
  (:require [clojure.test :as test]
            [soccer.integration-test]))

(defn -main [& _]
  (let [{:keys [fail error]} (test/run-tests 'soccer.integration-test)]
    (when (pos? (+ fail error))
      (System/exit 1))))
