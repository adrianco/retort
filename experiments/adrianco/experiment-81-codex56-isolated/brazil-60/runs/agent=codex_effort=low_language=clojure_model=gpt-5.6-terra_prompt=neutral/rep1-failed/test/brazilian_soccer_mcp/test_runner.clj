(ns brazilian-soccer-mcp.test-runner (:require [clojure.test :as t] [brazilian-soccer-mcp.core-test]))
(defn -main [& _] (let [result (t/run-tests 'brazilian-soccer-mcp.core-test)] (when (pos? (+ (:fail result) (:error result))) (System/exit 1))))
