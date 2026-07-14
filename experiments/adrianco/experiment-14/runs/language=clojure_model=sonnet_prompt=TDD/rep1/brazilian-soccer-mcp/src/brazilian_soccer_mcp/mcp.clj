(ns brazilian-soccer-mcp.mcp
  (:require [clojure.string :as str]
            [cheshire.core :as json]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.tools :as tools]
            [brazilian-soccer-mcp.queries :as q]))

(def server-info
  {:name    "brazilian-soccer-mcp"
   :version "0.1.0"})

(defn- success-response [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn- error-response [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn handle-initialize [req]
  (success-response (:id req)
                    {:protocolVersion "2024-11-05"
                     :capabilities    {:tools {}}
                     :serverInfo      server-info}))

(defn handle-tools-list [req]
  (success-response (:id req) {:tools (tools/list-tools)}))

(defn- arg [arguments k]
  (let [sk (if (keyword? k) (name k) (str k))
        kk (keyword sk)]
    (or (get arguments sk) (get arguments kk))))

(defn dispatch-tool
  "Dispatches a tool call. Uses data from db atom if loaded, else returns an error message."
  [tool-name arguments]
  (let [db      (data/get-db)
        matches (if db (data/all-matches) [])
        players (if db (data/fifa-players) [])]
    (cond
      (= tool-name "find_matches")
      (tools/call-find-matches matches arguments)

      (= tool-name "team_stats")
      (let [team        (arg arguments "team")
            season      (when-let [s (arg arguments "season")] (Integer/parseInt (str s)))
            competition (arg arguments "competition")]
        (if team
          (tools/call-team-stats matches team season competition)
          "Error: 'team' parameter is required"))

      (= tool-name "find_players")
      (tools/call-find-players players arguments)

      (= tool-name "standings")
      (let [season      (when-let [s (arg arguments "season")] (Integer/parseInt (str s)))
            competition (arg arguments "competition")]
        (tools/call-standings matches season competition))

      (= tool-name "biggest_wins")
      (let [n           (or (when-let [n (arg arguments "n")] (Integer/parseInt (str n))) 10)
            competition (arg arguments "competition")
            season      (when-let [s (arg arguments "season")] (Integer/parseInt (str s)))
            filtered    (q/find-matches matches (cond-> {}
                                                  competition (assoc :competition competition)
                                                  season      (assoc :season season)))]
        (tools/call-biggest-wins filtered n))

      (= tool-name "head_to_head")
      (let [team1    (arg arguments "team1")
            team2    (arg arguments "team2")
            season   (when-let [s (arg arguments "season")] (Integer/parseInt (str s)))
            filtered (if season
                       (q/find-matches matches {:season season})
                       matches)]
        (if (and team1 team2)
          (tools/call-head-to-head filtered team1 team2)
          "Error: 'team1' and 'team2' parameters are required"))

      :else
      (str "Unknown tool: " tool-name))))

(defn- get-either [m string-key]
  (or (get m string-key) (get m (keyword string-key))))

(defn handle-tools-call [req]
  (let [params    (:params req)
        tool-name (get-either params "name")
        arguments (or (get-either params "arguments") {})]
    (try
      (let [text (dispatch-tool tool-name arguments)]
        (success-response (:id req)
                          {:content [{:type "text" :text text}]}))
      (catch Exception e
        (error-response (:id req) -32603
                        (str "Internal error: " (.getMessage e)))))))

(defn handle-request
  "Handles a single JSON-RPC 2.0 request map. Returns a response map or nil for notifications."
  [req]
  (let [method (:method req)
        id     (:id req)]
    (cond
      ;; Notifications (no id) → no response
      (nil? id)
      nil

      (= method "initialize")
      (handle-initialize req)

      (= method "tools/list")
      (handle-tools-list req)

      (= method "tools/call")
      (handle-tools-call req)

      :else
      (error-response id -32601 (str "Method not found: " method)))))

(defn run-server!
  "Runs the MCP server loop reading from stdin and writing to stdout."
  [data-dir]
  (binding [*out* (java.io.PrintWriter. System/out true)]
    (data/load-all-data! data-dir)
    (loop []
      (when-let [line (try (read-line) (catch Exception _ nil))]
        (when-not (str/blank? line)
          (try
            (let [req  (json/decode line true)
                  resp (handle-request req)]
              (when resp
                (println (json/encode resp))
                (.flush *out*)))
            (catch Exception e
              (println (json/encode
                        {:jsonrpc "2.0" :id nil
                         :error {:code -32700 :message (str "Parse error: " (.getMessage e))}}))
              (.flush *out*))))
        (recur)))))
