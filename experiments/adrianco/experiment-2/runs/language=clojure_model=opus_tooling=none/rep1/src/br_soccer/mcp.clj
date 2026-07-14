(ns br-soccer.mcp
  "Minimal MCP-style JSON-RPC server over stdio exposing soccer query tools."
  (:require [br-soccer.query :as q]
            [clojure.data.json :as json]
            [clojure.java.io :as io])
  (:gen-class))

(def tools
  [{:name "search_matches"
    :description "Find matches by team, optional opponent, season, or competition."
    :inputSchema {:type "object"
                  :properties {:team {:type "string"}
                               :opponent {:type "string"}
                               :season {:type "integer"}
                               :competition {:type "string"}
                               :limit {:type "integer"}}}}
   {:name "team_stats"
    :description "Wins/draws/losses/goals for a team, optionally filtered by season, competition, or side (home/away/either)."
    :inputSchema {:type "object"
                  :required ["team"]
                  :properties {:team {:type "string"}
                               :season {:type "integer"}
                               :competition {:type "string"}
                               :side {:type "string" :enum ["home" "away" "either"]}}}}
   {:name "head_to_head"
    :description "Head-to-head record between two teams."
    :inputSchema {:type "object"
                  :required ["team_a" "team_b"]
                  :properties {:team_a {:type "string"}
                               :team_b {:type "string"}}}}
   {:name "standings"
    :description "League standings for a competition and season."
    :inputSchema {:type "object"
                  :required ["competition" "season"]
                  :properties {:competition {:type "string"}
                               :season {:type "integer"}}}}
   {:name "biggest_wins"
    :description "Matches sorted by largest goal margin."
    :inputSchema {:type "object"
                  :properties {:limit {:type "integer"}}}}
   {:name "avg_goals"
    :description "Average goals per match, optionally for a competition."
    :inputSchema {:type "object"
                  :properties {:competition {:type "string"}}}}
   {:name "search_players"
    :description "Find FIFA players by name substring."
    :inputSchema {:type "object"
                  :required ["name"]
                  :properties {:name {:type "string"}
                               :limit {:type "integer"}}}}
   {:name "top_players"
    :description "Top-rated players, optionally filtered by nationality, club, or position."
    :inputSchema {:type "object"
                  :properties {:limit {:type "integer"}
                               :nationality {:type "string"}
                               :club {:type "string"}
                               :position {:type "string"}}}}])

(defn- k [m key] (get m (keyword key) (get m key)))

(defn- limit* [n default] (or (some-> n long) default))

(defn dispatch [tool-name args]
  (case tool-name
    "search_matches"
    (let [team (k args "team")
          opp  (k args "opponent")
          season (k args "season")
          comp (k args "competition")
          lim (limit* (k args "limit") 50)
          ms (cond
               (and team opp) (q/matches-between team opp)
               team (q/matches-by-team team)
               season (q/matches-by-season season)
               comp (q/matches-by-competition comp)
               :else [])
          ms (cond->> ms
               season (filter #(= season (:season %)))
               comp (filter #(clojure.string/includes?
                              (clojure.string/lower-case (or (:competition %) ""))
                              (clojure.string/lower-case comp))))]
      {:count (count ms) :matches (vec (take lim ms))})

    "team_stats"
    (q/team-stats (k args "team")
                  {:season (k args "season")
                   :competition (k args "competition")
                   :side (keyword (or (k args "side") "either"))})

    "head_to_head"
    (let [r (q/head-to-head (k args "team_a") (k args "team_b"))]
      (update r :results #(vec (take 20 %))))

    "standings"
    (q/standings (k args "competition") (k args "season"))

    "biggest_wins"
    {:matches (q/biggest-wins (limit* (k args "limit") 10))}

    "avg_goals"
    {:average (q/avg-goals-per-match (k args "competition"))}

    "search_players"
    (let [lim (limit* (k args "limit") 20)]
      {:players (vec (take lim (q/players-by-name (k args "name"))))})

    "top_players"
    {:players (q/top-players (limit* (k args "limit") 10)
                             {:nationality (k args "nationality")
                              :club (k args "club")
                              :position (k args "position")})}

    (throw (ex-info "unknown tool" {:tool tool-name}))))

(defn- response [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn- error-response [id code msg]
  {:jsonrpc "2.0" :id id :error {:code code :message msg}})

(defn handle-request [req]
  (let [id (get req "id")
        method (get req "method")
        params (get req "params")]
    (try
      (case method
        "initialize"
        (response id {:protocolVersion "2024-11-05"
                      :capabilities {:tools {}}
                      :serverInfo {:name "br-soccer-mcp" :version "0.1.0"}})

        "tools/list"
        (response id {:tools tools})

        "tools/call"
        (let [tool (get params "name")
              args (get params "arguments" {})
              result (dispatch tool args)]
          (response id {:content [{:type "text"
                                   :text (json/write-str result)}]}))

        "ping" (response id {})

        (error-response id -32601 (str "method not found: " method)))
      (catch Exception e
        (error-response id -32000 (.getMessage e))))))

(defn -main [& _]
  (let [r (io/reader *in*)
        w (io/writer *out*)]
    (loop []
      (when-let [line (.readLine ^java.io.BufferedReader r)]
        (when-not (clojure.string/blank? line)
          (let [req (try (json/read-str line) (catch Exception _ nil))]
            (when req
              (let [resp (handle-request req)]
                (.write w (json/write-str resp))
                (.write w "\n")
                (.flush w)))))
        (recur)))))
