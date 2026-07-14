(ns soccer.mcp
  "Minimal MCP (JSON-RPC over stdio) server exposing soccer query tools."
  (:require [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [soccer.data :as data]
            [soccer.query :as q])
  (:gen-class))

(def protocol-version "2024-11-05")
(def server-info {:name "brazilian-soccer-mcp" :version "0.1.0"})

(defonce state (atom nil))

(defn- dataset! []
  (or @state
      (reset! state (data/load-dataset))))

(def tools
  [{:name "list_matches_between"
    :description "List matches between two teams."
    :inputSchema {:type "object"
                  :properties {:team_a {:type "string"}
                               :team_b {:type "string"}
                               :limit  {:type "integer"}}
                  :required ["team_a" "team_b"]}}
   {:name "team_matches"
    :description "List matches for a team, optionally filtered by season/competition."
    :inputSchema {:type "object"
                  :properties {:team {:type "string"}
                               :season {:type "integer"}
                               :competition {:type "string"}
                               :limit {:type "integer"}}
                  :required ["team"]}}
   {:name "team_record"
    :description "Get win/draw/loss record for a team. Optional side (home|away)."
    :inputSchema {:type "object"
                  :properties {:team {:type "string"}
                               :season {:type "integer"}
                               :competition {:type "string"}
                               :side {:type "string" :enum ["home" "away" "either"]}}
                  :required ["team"]}}
   {:name "head_to_head"
    :description "Head-to-head W/D/L between two teams."
    :inputSchema {:type "object"
                  :properties {:team_a {:type "string"}
                               :team_b {:type "string"}}
                  :required ["team_a" "team_b"]}}
   {:name "standings"
    :description "Compute competition standings. Requires season + competition."
    :inputSchema {:type "object"
                  :properties {:season {:type "integer"}
                               :competition {:type "string"}}
                  :required ["season"]}}
   {:name "search_players"
    :description "Search FIFA players by name, nationality, club, or position."
    :inputSchema {:type "object"
                  :properties {:name {:type "string"}
                               :nationality {:type "string"}
                               :club {:type "string"}
                               :position {:type "string"}
                               :limit {:type "integer"}}}}
   {:name "top_players"
    :description "Top N players by Overall rating, optionally filtered."
    :inputSchema {:type "object"
                  :properties {:nationality {:type "string"}
                               :club {:type "string"}
                               :limit {:type "integer"}}}}
   {:name "biggest_wins"
    :description "Biggest margin matches, optionally filtered."
    :inputSchema {:type "object"
                  :properties {:season {:type "integer"}
                               :competition {:type "string"}
                               :limit {:type "integer"}}}}
   {:name "statistics"
    :description "Aggregated stats (avg goals/match, home win rate) for filtered matches."
    :inputSchema {:type "object"
                  :properties {:season {:type "integer"}
                               :competition {:type "string"}
                               :team {:type "string"}}}}])

(defn- filter-matches [ds {:keys [season competition team]}]
  (cond->> (:matches ds)
    season      (q/matches-by-season season)
    competition (#(q/matches-by-competition % competition))
    team        (#(q/matches-by-team % team))))

(defn- limit* [coll n]
  (if n (take n coll) coll))

(defn- kw-args [args]
  (reduce-kv (fn [m k v] (assoc m (keyword k) v)) {} args))

(defn dispatch-tool [name args]
  (let [ds (dataset!)
        a  (kw-args args)]
    (case name
      "list_matches_between"
      (->> (q/matches-between (:matches ds) (:team_a a) (:team_b a))
           (limit* (:limit a)) vec)

      "team_matches"
      (->> (filter-matches ds a)
           (q/matches-by-team (:team a))
           (limit* (:limit a)) vec)

      "team_record"
      (let [ms (filter-matches ds a)
            side (some-> (:side a) keyword)]
        (q/team-record ms (:team a) (when (#{:home :away} side) side)))

      "head_to_head"
      (q/head-to-head (:matches ds) (:team_a a) (:team_b a))

      "standings"
      (let [ms (filter-matches ds (assoc a :competition (or (:competition a) "Brasileirão")))]
        (vec (q/standings ms)))

      "search_players"
      (let [ps (cond->> (:players ds)
                 (:name a)        (q/players-by-name (:name a))
                 (:nationality a) (#(q/players-by-nationality % (:nationality a)))
                 (:club a)        (#(q/players-by-club % (:club a)))
                 (:position a)    (#(q/players-by-position % (:position a))))]
        (vec (limit* ps (or (:limit a) 25))))

      "top_players"
      (let [ps (cond->> (:players ds)
                 (:nationality a) (#(q/players-by-nationality % (:nationality a)))
                 (:club a)        (#(q/players-by-club % (:club a))))]
        (q/top-players ps (or (:limit a) 10)))

      "biggest_wins"
      (q/biggest-wins (filter-matches ds a) (or (:limit a) 10))

      "statistics"
      (let [ms (filter-matches ds a)]
        {:match-count (count ms)
         :avg-goals-per-match (q/avg-goals-per-match ms)
         :home-win-rate (q/home-win-rate ms)})

      (throw (ex-info (str "unknown tool: " name) {:tool name})))))

(defn- json-response [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn- json-error [id code msg]
  {:jsonrpc "2.0" :id id :error {:code code :message msg}})

(defn handle-request [{:strs [id method params]}]
  (try
    (case method
      "initialize"
      (json-response id {:protocolVersion protocol-version
                         :capabilities {:tools {}}
                         :serverInfo server-info})

      "tools/list"
      (json-response id {:tools tools})

      "tools/call"
      (let [tool-name (get params "name")
            args (get params "arguments")
            result (dispatch-tool tool-name args)
            text (json/write-str result)]
        (json-response id {:content [{:type "text" :text text}]
                           :isError false}))

      "ping" (json-response id {})

      "notifications/initialized" nil

      (json-error id -32601 (str "method not found: " method)))
    (catch Throwable t
      (json-error id -32000 (.getMessage t)))))

(defn -main [& _]
  (let [in  (io/reader System/in)
        out *out*]
    (loop []
      (when-let [line (.readLine ^java.io.BufferedReader in)]
        (when-not (str/blank? line)
          (let [req (json/read-str line)
                resp (handle-request req)]
            (when resp
              (.write out (json/write-str resp))
              (.write out "\n")
              (.flush out))))
        (recur)))))
