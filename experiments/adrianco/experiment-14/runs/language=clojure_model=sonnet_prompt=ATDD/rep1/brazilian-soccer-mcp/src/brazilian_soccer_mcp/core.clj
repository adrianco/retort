(ns brazilian-soccer-mcp.core
  "MCP server entry point. Implements JSON-RPC 2.0 over stdin/stdout."
  (:require [cheshire.core :as json]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.tools :as tools]
            [clojure.string :as str])
  (:gen-class))

;; ---------------------------------------------------------------------------
;; Tool schema definitions (for tools/list)
;; ---------------------------------------------------------------------------

(def ^:private tool-schemas
  [{:name        "find-matches"
    :description "Find soccer matches by team, competition, season, or date range"
    :inputSchema {:type "object"
                  :properties
                  {:team        {:type "string" :description "Team name (either home or away)"}
                   :team1       {:type "string" :description "First team for head-to-head search"}
                   :team2       {:type "string" :description "Second team for head-to-head search"}
                   :competition {:type "string" :description "Competition: brasileirao, copa-do-brasil, libertadores"}
                   :season      {:type "integer" :description "Season year (e.g. 2023)"}
                   :date-from   {:type "string" :description "Start date yyyy-MM-dd"}
                   :date-to     {:type "string" :description "End date yyyy-MM-dd"}
                   :limit       {:type "integer" :description "Max results (default 200)"}}}}
   {:name        "get-team-stats"
    :description "Get win/draw/loss statistics for a team"
    :inputSchema {:type "object"
                  :required ["team"]
                  :properties
                  {:team        {:type "string"}
                   :competition {:type "string"}
                   :season      {:type "integer"}
                   :venue       {:type "string" :enum ["home" "away" "all"]}}}}
   {:name        "find-players"
    :description "Find FIFA players by name, nationality, club, or position"
    :inputSchema {:type "object"
                  :properties
                  {:name        {:type "string"}
                   :nationality {:type "string"}
                   :club        {:type "string"}
                   :position    {:type "string"}
                   :min-overall {:type "integer"}
                   :sort-by     {:type "string" :enum ["overall" "potential" "age"]}
                   :limit       {:type "integer"}}}}
   {:name        "get-head-to-head"
    :description "Get head-to-head record between two teams"
    :inputSchema {:type "object"
                  :required ["team1" "team2"]
                  :properties
                  {:team1       {:type "string"}
                   :team2       {:type "string"}
                   :competition {:type "string"}
                   :season      {:type "integer"}}}}
   {:name        "get-standings"
    :description "Calculate league standings for a season"
    :inputSchema {:type "object"
                  :required ["season"]
                  :properties
                  {:season      {:type "integer"}
                   :competition {:type "string"}}}}
   {:name        "get-statistics"
    :description "Compute aggregate statistics"
    :inputSchema {:type "object"
                  :required ["stat-type"]
                  :properties
                  {:stat-type   {:type "string"
                                 :enum ["biggest-wins" "goals-per-match"
                                        "home-away-record" "top-scoring-teams"]}
                   :competition {:type "string"}
                   :season      {:type "integer"}
                   :limit       {:type "integer"}}}}])

;; ---------------------------------------------------------------------------
;; JSON-RPC dispatch
;; ---------------------------------------------------------------------------

(defn- keywordize-args [m]
  (reduce-kv (fn [acc k v]
               (assoc acc (keyword (str/replace (name k) #"_" "-")) v))
             {} m))

(defn- handle-call [db tool-name arguments]
  (let [args (keywordize-args (or arguments {}))]
    (case tool-name
      "find-matches"    (tools/find-matches db args)
      "get-team-stats"  (tools/get-team-stats db args)
      "find-players"    (tools/find-players db args)
      "get-head-to-head" (tools/get-head-to-head db args)
      "get-standings"   (tools/get-standings db args)
      "get-statistics"  (tools/get-statistics db args)
      {:error (str "Unknown tool: " tool-name)})))

(defn- respond [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn- error-response [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn- handle-request [db request]
  (let [id     (:id request)
        method (:method request)
        params (:params request {})]
    (case method
      "initialize"
      (respond id {:protocolVersion "2024-11-05"
                   :capabilities    {:tools {}}
                   :serverInfo      {:name "brazilian-soccer-mcp" :version "0.1.0"}})

      "notifications/initialized" nil

      "tools/list"
      (respond id {:tools tool-schemas})

      "tools/call"
      (let [tool-name  (:name params)
            arguments  (:arguments params)]
        (try
          (let [result (handle-call db tool-name arguments)]
            (respond id {:content [{:type "text"
                                    :text (json/generate-string result {:pretty true})}]}))
          (catch Exception e
            (error-response id -32603 (.getMessage e)))))

      (error-response id -32601 (str "Method not found: " method)))))

;; ---------------------------------------------------------------------------
;; Main loop
;; ---------------------------------------------------------------------------

(defn -main [& args]
  (let [data-dir (or (first args)
                     (System/getenv "SOCCER_DATA_DIR")
                     "data/kaggle")
        _  (binding [*out* *err*]
             (println "Loading Brazilian soccer data from:" data-dir))
        db (data/load-all-data data-dir)
        _  (binding [*out* *err*]
             (println "Data loaded. MCP server ready."))]
    (loop []
      (when-let [line (try (read-line) (catch Exception _ nil))]
        (when (not (str/blank? line))
          (try
            (let [request  (json/parse-string line true)
                  response (handle-request db request)]
              (when response
                (println (json/generate-string response))
                (flush)))
            (catch Exception e
              (println (json/generate-string
                        {:jsonrpc "2.0" :id nil
                         :error {:code -32700 :message (str "Parse error: " (.getMessage e))}}))
              (flush))))
        (recur)))))
