;; =============================================================================
;; brazilian-soccer.test-helper
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   Shared fixtures for the test suite. The full knowledge graph is expensive to
;;   build (it parses ~42k CSV rows), so it is loaded once lazily and reused
;;   across all test namespaces via a delay.
;; =============================================================================
(ns brazilian-soccer.test-helper
  (:require [brazilian-soccer.knowledge-graph :as kg]))

(def data-dir "data/kaggle")

;; Built once, shared by every test namespace.
(def the-graph (delay (kg/load-graph data-dir)))

(defn graph [] @the-graph)
