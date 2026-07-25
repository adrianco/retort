(ns brazilian-soccer.bdd
  "A tiny Gherkin-flavoured DSL on top of clojure.test.

  CONTEXT
  -------
  The specification asks for Given/When/Then scenarios.  Rather than pull in a
  Cucumber runner and keep feature files in sync with glue code, scenarios are
  written directly in Clojure:

      (feature \"Match Queries\"
        (scenario \"Find matches between two teams\"
          (given \"the match data is loaded\" [db (test-db)])
          (when* \"I search for matches between Flamengo and Fluminense\"
            [result (q/find-matches db {...})])
          (then \"I should receive a list of matches\" (seq result))
          (and* \"each match has a date, scores and a competition\"
            (every? :date result))))

  `feature` expands to a deftest, each `scenario` to a testing block, and every
  then/and step to an assertion whose failure message quotes the step text, so
  a failure reads like the specification it came from."
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest testing is]]))

(defmacro feature
  "A feature is a deftest named after it."
  [description & body]
  (let [test-name (-> description
                      (str/replace #"[^a-zA-Z0-9]+" "-")
                      str/lower-case
                      (->> (str "feature-"))
                      symbol)]
    `(deftest ~test-name
       (testing ~(str "Feature: " description)
         ~@body))))

(defmacro scenario [description & body]
  `(testing ~(str "Scenario: " description)
     ~@body))

(defmacro given
  "Binds values for the rest of the scenario: (given \"...\" [db (test-db)] body...)"
  [description bindings & body]
  `(testing ~(str "Given " description)
     (let ~bindings ~@body)))

(defmacro when*
  "Same shape as `given`, kept separate so scenarios read as Gherkin."
  [description bindings & body]
  `(testing ~(str "When " description)
     (let ~bindings ~@body)))

(defmacro then [description expr]
  `(is ~expr ~(str "Then " description)))

(defmacro and* [description expr]
  `(is ~expr ~(str "And " description)))
