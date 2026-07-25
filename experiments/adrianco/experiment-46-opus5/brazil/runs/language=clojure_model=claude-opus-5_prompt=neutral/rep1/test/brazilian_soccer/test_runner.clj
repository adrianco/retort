(ns brazilian-soccer.test-runner
  "Test entry point.

  CONTEXT
  -------
  A hand-rolled runner keeps the project dependency-free beyond data.csv and
  data.json.  It requires every *-test namespace, runs them in a stable order
  and exits non-zero when anything fails, so CI can rely on the exit status.

  Both Clojure CLI calling conventions reach the same code, because a CI
  harness may pick either of them:

      clojure -M:test  -> -main  (:main-opts)
      clojure -X:test  -> run    (:exec-fn)"
  (:require [clojure.test :as t]))

(def test-namespaces
  '[brazilian-soccer.names-test
    brazilian-soccer.data-test
    brazilian-soccer.features-test
    brazilian-soccer.tools-test
    brazilian-soccer.mcp-test
    brazilian-soccer.samples-test
    brazilian-soccer.performance-test])

(defn run-tests
  "Run the suite and return the clojure.test summary.  No side effects beyond
  printing, so it is also usable from a REPL."
  []
  (apply require test-namespaces)
  (let [summary (apply t/run-tests test-namespaces)]
    (println)
    (println "Summary:" summary)
    summary))

(defn- exit! [{:keys [fail error]}]
  (shutdown-agents)
  (System/exit (if (zero? (+ fail error)) 0 1)))

(defn run
  "Entry point for `clojure -X:test` / `clojure -T:test`."
  [_]
  (exit! (run-tests)))

(defn -main
  "Entry point for `clojure -M:test`."
  [& _]
  (exit! (run-tests)))
