(ns brazilian-soccer-mcp.server
  "Minimal MCP server (JSON-RPC 2.0 over stdio).

   Implements the subset of the Model Context Protocol needed for tool
   exposure: initialize / tools/list / tools/call / ping. Each tool
   delegates to brazilian-soccer-mcp.queries."
  (:require [brazilian-soccer-mcp.data    :as data]
            [brazilian-soccer-mcp.queries :as q]
            [clojure.data.json            :as json]
            [clojure.string               :as str])
  (:import  [java.io BufferedReader InputStreamReader OutputStreamWriter PrintWriter]))

(def protocol-version "2024-11-05")
(def server-info {:name "brazilian-soccer-mcp" :version "0.1.0"})

;; ---- tool catalog ------------------------------------------------------

(def tools
  [{:name        "search_matches"
    :description "Find matches by team(s), competition, season, or date range."
    :inputSchema {:type       "object"
                  :properties {:team        {:type "string"
                                             :description "Team name (matches loosely)"}
                               :opponent    {:type "string"}
                               :competition {:type "string"
                                             :description "e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'"}
                               :season      {:type "integer"}
                               :from        {:type "string"
                                             :description "ISO date YYYY-MM-DD (inclusive)"}
                               :to          {:type "string"
                                             :description "ISO date YYYY-MM-DD (inclusive)"}
                               :limit       {:type "integer" :default 25}}}}
   {:name        "head_to_head"
    :description "Aggregate W/D/L record between two teams across the dataset."
    :inputSchema {:type       "object"
                  :required   ["team_a" "team_b"]
                  :properties {:team_a      {:type "string"}
                               :team_b      {:type "string"}
                               :competition {:type "string"}
                               :season      {:type "integer"}}}}
   {:name        "team_stats"
    :description "Per-team summary (matches, W/D/L, GF/GA, points)."
    :inputSchema {:type       "object"
                  :required   ["team"]
                  :properties {:team        {:type "string"}
                               :competition {:type "string"}
                               :season      {:type "integer"}
                               :role        {:type "string"
                                             :enum ["home" "away" "either"]
                                             :default "either"}}}}
   {:name        "standings"
    :description "Calculated league table for a competition + season."
    :inputSchema {:type       "object"
                  :required   ["season"]
                  :properties {:season      {:type "integer"}
                               :competition {:type "string" :default "Brasileirão"}
                               :limit       {:type "integer" :default 20}}}}
   {:name        "search_players"
    :description "Search FIFA player database. Filter by name, nationality, club, position."
    :inputSchema {:type       "object"
                  :properties {:name        {:type "string"}
                               :nationality {:type "string"}
                               :club        {:type "string"}
                               :position    {:type "string"}
                               :min_overall {:type "integer"}
                               :limit       {:type "integer" :default 25}}}}
   {:name        "biggest_wins"
    :description "Matches sorted by absolute goal difference, descending."
    :inputSchema {:type       "object"
                  :properties {:competition {:type "string"}
                               :season      {:type "integer"}
                               :limit       {:type "integer" :default 10}}}}
   {:name        "average_goals"
    :description "Average goals per match across the filtered set."
    :inputSchema {:type       "object"
                  :properties {:competition {:type "string"}
                               :season      {:type "integer"}}}}
   {:name        "home_win_rate"
    :description "Fraction of matches won by the home side."
    :inputSchema {:type       "object"
                  :properties {:competition {:type "string"}
                               :season      {:type "integer"}}}}])

;; ---- tool dispatch -----------------------------------------------------

(defn- key-args
  "MCP tools pass arguments as a JSON object keyed by camel/snake case
   strings. Convert to keyword-style options the queries expect."
  [m]
  (reduce-kv (fn [acc k v]
               (assoc acc (-> k name (str/replace "_" "-") keyword) v))
             {} (or m {})))

(defn- as-text [s] {:content [{:type "text" :text s}]})

(defn- summarize-matches [matches]
  (if (empty? matches)
    "No matches found."
    (str (count matches) " match(es):\n"
         (str/join "\n" (map #(str "- " (q/format-match %))
                             (take 50 matches))))))

(defn dispatch
  "Resolve an MCP tool call to a text result. Public so it's testable."
  [db tool-name raw-args]
  (let [a (key-args raw-args)]
    (case tool-name
      "search_matches"
      (let [team     (:team a)
            opp      (:opponent a)
            opts     (select-keys a [:competition :season :from :to :limit])
            ms (cond
                 (and team opp)  (q/matches-between db team opp opts)
                 team            (q/matches-by-team db team opts)
                 :else
                 (->> (:matches db)
                      ((fn [xs]
                         (cond->> xs
                           (:competition opts) (filter #(and (:competition %)
                                                             (str/includes?
                                                              (str/lower-case (:competition %))
                                                              (str/lower-case (:competition opts)))))
                           (:season opts)      (filter #(= (:season opts) (:season %))))))
                      (take (or (:limit opts) 25))
                      vec))]
        (as-text (summarize-matches ms)))

      "head_to_head"
      (let [{:keys [team-a team-b]} a
            h (q/head-to-head db team-a team-b
                              (select-keys a [:competition :season]))]
        (as-text
         (format "%s vs %s — %d matches: %s %d, %s %d, %d draws"
                 team-a team-b (:total h)
                 team-a (:a-wins h) team-b (:b-wins h) (:draws h))))

      "team_stats"
      (let [opts (select-keys a [:competition :season :role])
            opts (if (:role opts) (update opts :role keyword) opts)
            s    (q/team-stats db (:team a) opts)]
        (as-text (q/format-team-stats s)))

      "standings"
      (let [opts (select-keys a [:competition])
            limit (or (:limit a) 20)
            rows (q/standings db (:season a) opts)]
        (as-text
         (str "Standings " (:season a)
              (when (:competition opts) (str " (" (:competition opts) ")")) ":\n"
              (str/join "\n"
                        (map-indexed
                         (fn [i r]
                           (format "%2d. %-30s %2d pts %2dW %2dD %2dL  GF:%2d GA:%2d GD:%+d"
                                   (inc i) (:team r) (:points r)
                                   (:wins r) (:draws r) (:losses r)
                                   (:goals-for r) (:goals-against r)
                                   (:goal-difference r)))
                         (take limit rows))))))

      "search_players"
      (let [opts (select-keys a [:club :position :min-overall :limit])
            ps   (cond
                   (:name a)        (q/players-by-name db (:name a) opts)
                   (:nationality a) (q/players-by-nationality db (:nationality a) opts)
                   (:club a)        (q/players-by-club db (:club a) opts)
                   :else            [])]
        (as-text
         (if (empty? ps)
           "No players found."
           (str (count ps) " player(s):\n"
                (str/join "\n"
                          (map #(format "- %s (OVR %s) %s — %s"
                                        (:name %)
                                        (or (:overall %) "?")
                                        (or (:position %) "?")
                                        (or (:club %) "?"))
                               ps))))))

      "biggest_wins"
      (let [ms (q/biggest-wins db (select-keys a [:competition :season :limit]))]
        (as-text (summarize-matches ms)))

      "average_goals"
      (let [g (q/avg-goals-per-match db (select-keys a [:competition :season]))]
        (as-text (format "Average goals per match: %.3f" g)))

      "home_win_rate"
      (let [r (q/home-win-rate db (select-keys a [:competition :season]))]
        (as-text (format "Home win rate: %.1f%%" (* 100.0 r))))

      (throw (ex-info (str "Unknown tool: " tool-name)
                      {:code -32601 :tool tool-name})))))

;; ---- JSON-RPC handling -------------------------------------------------

(defn- ok [id result]
  {:jsonrpc "2.0" :id id :result result})

(defn- err [id code msg]
  {:jsonrpc "2.0" :id id :error {:code code :message msg}})

(defn handle-request
  "Take a parsed JSON-RPC request map (string keys preserved) and a db.
   Returns the response map, or nil for notifications."
  [db {:strs [id method params]}]
  (try
    (case method
      "initialize"
      (ok id {:protocolVersion protocol-version
              :capabilities    {:tools {}}
              :serverInfo      server-info})

      "ping"
      (ok id {})

      "tools/list"
      (ok id {:tools tools})

      "tools/call"
      (let [tool-name (get params "name")
            arguments (get params "arguments")
            result    (dispatch db tool-name arguments)]
        (ok id result))

      ;; MCP notifications carry no id and expect no response.
      ("notifications/initialized" "initialized")
      nil

      (err id -32601 (str "Method not found: " method)))
    (catch clojure.lang.ExceptionInfo e
      (err id (or (:code (ex-data e)) -32603) (.getMessage e)))
    (catch Exception e
      (err id -32603 (.getMessage e)))))

(defn run-stdio
  "Block reading line-delimited JSON-RPC requests from *in* and writing
   responses to *out*. MCP clients launch the server as a subprocess and
   talk over its stdio."
  ([] (run-stdio (data/db)))
  ([db]
   (let [in  (BufferedReader. (InputStreamReader. System/in "UTF-8"))
         out (PrintWriter. (OutputStreamWriter. System/out "UTF-8") true)]
     (loop []
       (when-let [line (.readLine in)]
         (when-not (str/blank? line)
           (let [req  (json/read-str line)
                 resp (handle-request db req)]
             (when resp
               (.println out (json/write-str resp))
               (.flush out))))
         (recur))))))
