(ns brazil-soccer.test-runner
  "Runs every test namespace. Exits non-zero when any test fails or errors."
  (:require [clojure.test :as t]
            brazil-soccer.teams-test
            brazil-soccer.data-test
            brazil-soccer.queries-test
            brazil-soccer.tools-test
            brazil-soccer.mcp-test))

(defn -main [& _]
  (let [{:keys [fail error]} (apply t/run-tests '[brazil-soccer.teams-test
                                                  brazil-soccer.data-test
                                                  brazil-soccer.queries-test
                                                  brazil-soccer.tools-test
                                                  brazil-soccer.mcp-test])]
    (shutdown-agents)
    (System/exit (if (zero? (+ fail error)) 0 1))))
