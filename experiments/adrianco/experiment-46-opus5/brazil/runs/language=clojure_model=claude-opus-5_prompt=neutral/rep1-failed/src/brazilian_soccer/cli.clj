(ns brazilian-soccer.cli
  "Human-facing entry point for the same tools the MCP server exposes.

  CONTEXT
  -------
  Useful for exploring the data and for demonstrating the server without an MCP
  client:

      clojure -M:cli tools
      clojure -M:cli call standings competition=brasileirao season=2019
      clojure -M:cli call search_matches team=Flamengo opponent=Fluminense limit=5
      clojure -M:cli demo            # every sample question from the spec
      clojure -M:cli demo \"derbies\"  # only questions matching a keyword

  Arguments are key=value pairs; values that look like integers are sent as
  integers so that the tool layer sees exactly what an MCP client would send."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.tools :as tools]))

(defn parse-args
  "[\"team=Flamengo\" \"limit=5\"] -> {\"team\" \"Flamengo\" \"limit\" 5}"
  [pairs]
  (into {}
        (for [p pairs
              :let [[k v] (str/split p #"=" 2)]
              :when v]
          [k (if (re-matches #"-?\d+" v) (Long/parseLong v) v)])))

(defn sample-questions []
  (edn/read-string (slurp (io/resource "sample_questions.edn"))))

(defn- run-demo [db filter-text]
  (let [questions (cond->> (sample-questions)
                    filter-text (filter #(str/includes?
                                          (str/lower-case (str (:question %) (:category %)))
                                          (str/lower-case filter-text))))]
    (doseq [{:keys [category question tool args]} questions]
      (println (str "\n" (apply str (repeat 78 "="))))
      (println (str "[" category "] " question))
      (println (str "-> " tool " " (pr-str args)))
      (println (apply str (repeat 78 "-")))
      (println (try (tools/call-tool db tool args)
                    (catch Exception e (str "ERROR: " (.getMessage e))))))
    (println (str "\n" (count questions) " sample questions answered."))))

(defn -main [& [command & args]]
  (let [db (data/load-db)]
    (case (or command "help")
      "tools"
      (doseq [t tools/tools]
        (println (str "\n" (:name t)))
        (println "  " (:description t))
        (println "   args:" (str/join ", " (sort (keys (get (:schema t) "properties"))))))

      "call"
      (let [[tool-name & kvs] args]
        (println (try (tools/call-tool db tool-name (parse-args kvs))
                      (catch Exception e (str "ERROR: " (.getMessage e))))))

      "demo" (run-demo db (first args))

      "info" (println (tools/call-tool db "dataset_info" {}))

      (println (str "Usage:\n"
                    "  clojure -M:cli tools                     list the MCP tools\n"
                    "  clojure -M:cli call <tool> k=v ...       call one tool\n"
                    "  clojure -M:cli demo [keyword]            answer the sample questions\n"
                    "  clojure -M:cli info                      dataset overview\n"
                    "  clojure -M:mcp                           run the MCP server on stdio")))))
