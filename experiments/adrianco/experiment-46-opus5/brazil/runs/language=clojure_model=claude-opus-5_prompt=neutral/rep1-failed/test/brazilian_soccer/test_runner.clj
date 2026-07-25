(ns brazilian-soccer.test-runner
  "Test entry point: `clojure -M:test`.

  CONTEXT
  -------
  A hand-rolled runner keeps the project dependency-free beyond data.csv and
  data.json.  It requires every *-test namespace, runs them in a stable order
  and exits non-zero when anything fails, so CI can rely on the exit status."
  (:require [clojure.test :as t]))

(def test-namespaces
  '[brazilian-soccer.names-test
    brazilian-soccer.data-test
    brazilian-soccer.features-test
    brazilian-soccer.tools-test
    brazilian-soccer.mcp-test
    brazilian-soccer.samples-test
    brazilian-soccer.performance-test])

(defn -main [& _]
  (apply require test-namespaces)
  (let [{:keys [fail error] :as summary} (apply t/run-tests test-namespaces)]
    (println)
    (println "Summary:" summary)
    (shutdown-agents)
    (System/exit (if (zero? (+ fail error)) 0 1))))
