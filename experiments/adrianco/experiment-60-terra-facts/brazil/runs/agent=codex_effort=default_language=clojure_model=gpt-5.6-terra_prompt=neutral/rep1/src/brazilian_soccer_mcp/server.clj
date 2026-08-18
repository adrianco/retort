(ns brazilian-soccer-mcp.server
  (:require [brazilian-soccer-mcp.core :as soccer] [clojure.data.json :as json] [clojure.string :as str]))

(def tool-definitions
  [{:name "search_matches" :description "Find matches by team, two teams, competition, season, or date range. Team matching is accent- and state-suffix-insensitive."
    :inputSchema {:type "object" :properties {:team {:type "string"} :team-a {:type "string"} :team-b {:type "string"} :competition {:type "string"} :season {:type "integer"} :from {:type "string"} :to {:type "string"} :limit {:type "integer"}}}}
   {:name "team_stats" :description "Calculate a team's win/loss/draw and goal record." :inputSchema {:type "object" :required ["team"] :properties {:team {:type "string"} :competition {:type "string"} :season {:type "integer"} :venue {:type "string" :description "home, away, or omitted"}}}}
   {:name "head_to_head" :description "Compare two teams and return their record plus recent matches." :inputSchema {:type "object" :required ["team-a" "team-b"] :properties {:team-a {:type "string"} :team-b {:type "string"} :competition {:type "string"} :season {:type "integer"}}}}
   {:name "search_players" :description "Find FIFA players by name, nationality, club, or position, ordered by rating." :inputSchema {:type "object" :properties {:name {:type "string"} :nationality {:type "string"} :club {:type "string"} :position {:type "string"} :limit {:type "integer"}}}}
   {:name "standings" :description "Calculate league standings from loaded match results." :inputSchema {:type "object" :required ["season"] :properties {:competition {:type "string"} :season {:type "integer"}}}}
   {:name "dataset_statistics" :description "Calculate match and goal aggregates, including home/draw/away results." :inputSchema {:type "object" :properties {:competition {:type "string"} :season {:type "integer"}}}}])

(defn keywordize [m] (into {} (map (fn [[k v]] [(keyword k) v]) m)))
(defn result [x] {:content [{:type "text" :text (json/write-str x)}] :structuredContent x})
(defn dispatch [db name args]
  (let [args (keywordize args)]
    (case name "search_matches" (soccer/search-matches db args) "team_stats" (soccer/team-stats db args)
          "head_to_head" (soccer/head-to-head db (:team-a args) (:team-b args) args) "search_players" (soccer/search-players db args)
          "standings" (soccer/standings db args) "dataset_statistics" (soccer/dataset-statistics db args)
          (throw (ex-info "Unknown tool" {:tool name})))))

(defn handle [db request]
  (let [id (get request "id") method (get request "method") params (get request "params")]
    (cond-> {"jsonrpc" "2.0" "id" id}
      (= method "initialize") (assoc "result" {"protocolVersion" "2024-11-05" "capabilities" {"tools" {}} "serverInfo" {"name" "brazilian-soccer-mcp" "version" "1.0.0"}})
      (= method "tools/list") (assoc "result" {"tools" tool-definitions})
      (= method "tools/call") (assoc "result" (result (dispatch db (get params "name") (or (get params "arguments") {}))))
      (and (not= method "initialize") (not= method "tools/list") (not= method "tools/call")) (assoc "error" {"code" -32601 "message" "Method not found"}))))

(defn -main [& _]
  (let [db (soccer/load-data)]
    (doseq [line (line-seq (java.io.BufferedReader. *in*)) :when (not (str/blank? line))]
      (try (println (json/write-str (handle db (json/read-str line))) ) (flush)
           (catch Exception e (println (json/write-str {"jsonrpc" "2.0" "error" {"code" -32603 "message" (.getMessage e)}})) (flush))))))
