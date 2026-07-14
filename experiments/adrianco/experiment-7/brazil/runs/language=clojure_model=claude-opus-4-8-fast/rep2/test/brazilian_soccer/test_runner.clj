(ns brazilian-soccer.test-runner
  "=============================================================================
   test_runner.clj — Self-contained clojure.test runner
   -----------------------------------------------------------------------------
   Context:
     Avoids an extra test-runner dependency. Requires every test namespace,
     runs them, and exits non-zero if anything fails so CI / `clojure -X:test`
     reports correctly.
   ============================================================================="
  (:require [clojure.test :as t]
            [brazilian-soccer.normalize-test]
            [brazilian-soccer.queries-test]
            [brazilian-soccer.mcp-test]))

(def ^:private test-nses
  '[brazilian-soccer.normalize-test
    brazilian-soccer.queries-test
    brazilian-soccer.mcp-test])

(defn run
  "Entry point for `clojure -X:test`."
  [& _]
  (let [{:keys [fail error]} (apply t/run-tests test-nses)]
    (System/exit (if (zero? (+ fail error)) 0 1))))

(defn -main [& _] (run))
