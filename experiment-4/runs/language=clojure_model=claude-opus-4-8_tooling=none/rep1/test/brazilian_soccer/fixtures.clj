(ns brazilian-soccer.fixtures
  "=============================================================================
   Shared test fixture - the loaded knowledge graph.
   =============================================================================
   Loading the six CSVs is mildly expensive, so the database is memoized in a
   delay and shared across all query/MCP test namespaces via `db`."
  (:require [brazilian-soccer.data :as data]))

(def ^:private db* (delay (data/load-database data/default-data-dir)))

(defn db [] @db*)
