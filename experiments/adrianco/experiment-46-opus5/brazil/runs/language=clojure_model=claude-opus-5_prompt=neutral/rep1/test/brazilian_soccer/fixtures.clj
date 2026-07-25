(ns brazilian-soccer.fixtures
  "Shared, load-once database for the test suite.

  CONTEXT
  -------
  Parsing all six CSV files takes about half a second, so every namespace uses
  the same memoised instance rather than reloading.  `(test-db)` is the real
  data set - these are acceptance tests over the actual Kaggle files, which is
  the only way to verify de-duplication, name normalisation and encoding."
  (:require [brazilian-soccer.data :as data]))

(def ^:private cached (delay (data/load-db)))

(defn test-db [] @cached)
