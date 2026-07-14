;; =============================================================================
;; brazilian-soccer.mcp-server
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   A Model Context Protocol (MCP) server that exposes the Brazilian soccer
;;   knowledge graph as a set of callable tools, so an LLM can answer natural
;;   language questions about players, teams, matches and competitions.
;;
;;   Transport: MCP stdio — newline-delimited JSON-RPC 2.0 messages on
;;   stdin/stdout. Diagnostics go to stderr so they never corrupt the protocol
;;   stream. Run with:  clojure -M -m brazilian-soccer.mcp-server
;;
;;   Methods implemented: initialize, notifications/initialized, ping,
;;   tools/list, tools/call.
;;
;;   The knowledge graph (knowledge_graph.clj) is loaded once at startup and
;;   cached, so simple tool calls answer well within the latency budget.
;;
;; TOOLS
;;   find_matches, head_to_head, team_stats, find_players, standings,
;;   league_stats, biggest_wins, list_competitions, graph_info
;; =============================================================================
(ns brazilian-soccer.mcp-server
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [clojure.java.io :as io]
            [brazilian-soccer.knowledge-graph :as kg]
            [brazilian-soccer.queries :as q]
            [brazilian-soccer.format :as fmt])
  (:gen-class))

(def protocol-version "2024-11-05")
(def server-info {:name "brazilian-soccer-mcp" :version "1.0.0"})

(defn- log [& xs]
  (binding [*out* *err*]
    (apply println xs)
    (flush)))

;; ---------------------------------------------------------------------------
;; Tool definitions (name -> {:description :inputSchema :handler})
;; ---------------------------------------------------------------------------

(defn- str-prop  [desc] {:type "string"  :description desc})
(defn- int-prop  [desc] {:type "integer" :description desc})
(defn- bool-prop [desc] {:type "boolean" :description desc})

(def tools
  [{:name "find_matches"
    :description "Find soccer matches by team, opponent, competition, season or date range. Returns a formatted list of matches with dates, scores and competition."
    :inputSchema
    {:type "object"
     :properties {:team        (str-prop "Team name (home or away), e.g. \"Flamengo\"")
                  :opponent    (str-prop "Restrict to matches against this team")
                  :competition (str-prop "Competition name substring, e.g. \"Libertadores\"")
                  :season      (int-prop "Season year, e.g. 2019")
                  :home        (bool-prop "Only matches where :team played at home")
                  :away        (bool-prop "Only matches where :team played away")
                  :date_from   (str-prop "Inclusive start date (YYYY-MM-DD)")
                  :date_to     (str-prop "Inclusive end date (YYYY-MM-DD)")
                  :limit       (int-prop "Max results (default 50)")}}
    :handler (fn [g a]
               (fmt/format-matches (q/find-matches g a)
                                   {:title (str "Matches"
                                                (when (:team a) (str " for " (:team a)))
                                                (when (:opponent a) (str " vs " (:opponent a))) ":")}))}

   {:name "head_to_head"
    :description "Head-to-head rivalry record between two teams across all competitions in the dataset (wins, draws, goals and recent meetings)."
    :inputSchema
    {:type "object"
     :properties {:team_a (str-prop "First team")
                  :team_b (str-prop "Second team")}
     :required ["team_a" "team_b"]}
    :handler (fn [g a]
               (fmt/format-head-to-head (q/head-to-head g (:team-a a) (:team-b a))))}

   {:name "team_stats"
    :description "Win/draw/loss record, goals for/against and win rate for a team, optionally filtered by season, competition, or home/away."
    :inputSchema
    {:type "object"
     :properties {:team        (str-prop "Team name (required)")
                  :season      (int-prop "Season year")
                  :competition (str-prop "Competition name substring")
                  :home        (bool-prop "Only home matches")
                  :away        (bool-prop "Only away matches")}
     :required ["team"]}
    :handler (fn [g a] (fmt/format-team-stats (q/team-stats g a)))}

   {:name "find_players"
    :description "Search FIFA player data by name, nationality (e.g. \"Brazil\"), club, position, or minimum overall rating. Sorted by rating."
    :inputSchema
    {:type "object"
     :properties {:name        (str-prop "Player name substring")
                  :nationality (str-prop "Nationality, e.g. \"Brazil\"")
                  :club        (str-prop "Club name substring")
                  :position    (str-prop "Position code, e.g. \"GK\", \"LW\", \"CB\"")
                  :min_overall (int-prop "Minimum FIFA overall rating")
                  :limit       (int-prop "Max results (default 25)")}}
    :handler (fn [g a]
               (fmt/format-players (q/find-players g a)
                                   {:title "Players:"}))}

   {:name "standings"
    :description "League table for a competition and season, calculated from match results (points, W/D/L, goals for/against, goal difference)."
    :inputSchema
    {:type "object"
     :properties {:competition (str-prop "Competition name, e.g. \"Brasileirão Série A\"")
                  :season      (int-prop "Season year, e.g. 2019")}
     :required ["competition" "season"]}
    :handler (fn [g a]
               (fmt/format-standings (q/standings g (:competition a) (:season a))
                                     {:competition (:competition a) :season (:season a)}))}

   {:name "league_stats"
    :description "Aggregate statistics over a competition/season: average goals per match, home/away win rates and draw rate."
    :inputSchema
    {:type "object"
     :properties {:competition (str-prop "Competition name substring")
                  :season      (int-prop "Season year")}}
    :handler (fn [g a]
               (fmt/format-league-stats (q/league-stats g a)
                                        {:competition (:competition a) :season (:season a)}))}

   {:name "biggest_wins"
    :description "The matches with the largest goal margin, optionally filtered by competition, season or team."
    :inputSchema
    {:type "object"
     :properties {:competition (str-prop "Competition name substring")
                  :season      (int-prop "Season year")
                  :team        (str-prop "Restrict to matches involving this team")
                  :limit       (int-prop "Max results (default 10)")}}
    :handler (fn [g a]
               (fmt/format-biggest-wins (q/biggest-wins g a) {}))}

   {:name "list_competitions"
    :description "List all competitions in the knowledge graph with match counts, team counts and season coverage."
    :inputSchema {:type "object" :properties {}}
    :handler (fn [g _] (fmt/format-competitions (q/list-competitions g)))}

   {:name "graph_info"
    :description "Diagnostics: number of matches, players, teams and competitions loaded into the knowledge graph."
    :inputSchema {:type "object" :properties {}}
    :handler (fn [g _]
               (let [s (kg/stats-summary g)]
                 (str "Knowledge graph loaded:\n"
                      "- Matches: " (:matches s) "\n"
                      "- Players: " (:players s) "\n"
                      "- Teams: " (:teams s) "\n"
                      "- Competitions: " (:competitions s) "\n"
                      (str/join "\n" (map #(str "  • " %) (:competition-names s))))))}])

(def tools-by-name (into {} (map (juxt :name identity) tools)))

(defn tool-list-payload []
  {:tools (mapv #(select-keys % [:name :description :inputSchema]) tools)})

;; ---------------------------------------------------------------------------
;; JSON-RPC handling
;; ---------------------------------------------------------------------------

(defn- ok [id result] {:jsonrpc "2.0" :id id :result result})
(defn- err [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn- text-result [s] {:content [{:type "text" :text s}] :isError false})
(defn- error-result [s] {:content [{:type "text" :text s}] :isError true})

(defn call-tool [graph name arguments]
  (if-let [tool (tools-by-name name)]
    (try
      (text-result ((:handler tool) graph (or arguments {})))
      (catch Exception e
        (log "Tool error" name "->" (.getMessage e))
        (error-result (str "Error running tool '" name "': " (.getMessage e)))))
    (error-result (str "Unknown tool: " name))))

(defn handle-request
  "Handle a single parsed JSON-RPC message. Returns a response map, or nil for
   notifications (which must not be answered)."
  [graph {:keys [id method params]}]
  (case method
    "initialize"
    (ok id {:protocolVersion (or (:protocolVersion params) protocol-version)
            :capabilities {:tools {}}
            :serverInfo server-info})

    "notifications/initialized" nil
    "initialized" nil
    "notifications/cancelled" nil

    "ping" (ok id {})

    "tools/list" (ok id (tool-list-payload))

    "tools/call"
    (ok id (call-tool graph (:name params) (:arguments params)))

    ;; default
    (if (nil? id)
      nil ;; unknown notification — ignore
      (err id -32601 (str "Method not found: " method)))))

;; ---------------------------------------------------------------------------
;; stdio transport loop
;; ---------------------------------------------------------------------------

(defn- read-message [line]
  ;; snake_case JSON keys -> kebab-case keywords for ergonomic destructuring
  (json/read-str line :key-fn #(keyword (str/replace % "_" "-"))))

(defn- write-message [writer msg]
  (locking writer
    (.write writer (json/write-str msg))
    (.write writer "\n")
    (.flush writer)))

(defn serve
  "Run the stdio JSON-RPC loop reading from `in` and writing to `out`."
  [graph in out]
  (let [writer (io/writer out)]
    (with-open [^java.io.BufferedReader reader (io/reader in)]
      (loop []
        (when-let [line (.readLine reader)]
          (when-not (str/blank? line)
            (try
              (let [msg (read-message line)
                    resp (handle-request graph msg)]
                (when resp (write-message writer resp)))
              (catch Exception e
                (log "Message handling error:" (.getMessage e))
                (write-message writer (err nil -32700 (str "Parse error: " (.getMessage e)))))))
          (recur))))))

(defn -main [& _args]
  (log "Loading Brazilian soccer knowledge graph...")
  (let [graph (kg/graph)
        s (kg/stats-summary graph)]
    (log (format "Loaded %d matches, %d players, %d teams, %d competitions."
                 (:matches s) (:players s) (:teams s) (:competitions s)))
    (log "Brazilian Soccer MCP server ready on stdio.")
    (serve graph System/in System/out)))
