(ns book-api.test-runner
  "Minimal `clj -M:test` entry point — no external test-runner dependency."
  (:require [clojure.test :as t]))

(def ^:private test-namespaces
  '[book-api.validation-test
    book-api.db-test
    book-api.api-test])

(defn -main [& _args]
  (apply require test-namespaces)
  (let [{:keys [fail error]} (apply t/run-tests test-namespaces)]
    (shutdown-agents)
    (System/exit (if (zero? (+ fail error)) 0 1))))
