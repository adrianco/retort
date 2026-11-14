(ns brsoccer.test-runner
  "Runs every test namespace and exits non-zero on failure: `clojure -M:test`."
  (:require [clojure.test :as t]
            brsoccer.data-test
            brsoccer.queries-test
            brsoccer.mcp-test))

(defn -main [& _]
  (let [{:keys [fail error]} (t/run-tests 'brsoccer.data-test 'brsoccer.queries-test 'brsoccer.mcp-test)]
    (shutdown-agents)
    (System/exit (if (zero? (+ fail error)) 0 1))))
