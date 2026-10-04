(ns brsoccer.test-runner
  "Entry point for `clojure -M:test`: runs every test namespace and exits
  non-zero on any failure or error."
  (:require [clojure.test :as t]
            brsoccer.names-test
            brsoccer.data-test
            brsoccer.query-test
            brsoccer.server-test))

(defn -main [& _]
  (let [{:keys [fail error]} (t/run-tests 'brsoccer.names-test
                                          'brsoccer.data-test
                                          'brsoccer.query-test
                                          'brsoccer.server-test)]
    (shutdown-agents)
    (System/exit (if (zero? (+ fail error)) 0 1))))
