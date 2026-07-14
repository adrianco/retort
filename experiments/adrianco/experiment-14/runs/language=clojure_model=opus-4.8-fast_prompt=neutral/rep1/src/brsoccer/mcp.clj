;; =============================================================================
;; brsoccer.mcp
;;
;; Context:
;;   Implements the Model Context Protocol (https://modelcontextprotocol.io) as a
;;   JSON-RPC 2.0 server over stdio.  An LLM host (Claude Desktop, etc.) launches
;;   this process, performs the `initialize` handshake, lists tools, and calls
;;   them with `tools/call`.  Each tool wraps a brsoccer.query function and
;;   returns BOTH formatted text (for the model to read) and the underlying
;;   structured data (under `structuredContent`) so the model can reason over it.
;;
;;   The protocol plumbing (frame read/write, request dispatch) is deliberately
;;   small and dependency-free; `handle-request` is pure and unit-tested, so the
;;   whole server can be exercised without spawning a process.
;; =============================================================================
(ns brsoccer.mcp
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [brsoccer.data :as data]
            [brsoccer.query :as q]
            [brsoccer.format :as fmt])
  (:import [java.io BufferedReader]))

(def protocol-version "2024-11-05")
(def server-info {:name "brazilian-soccer-mcp" :version "1.0.0"})

;; ---------------------------------------------------------------------------
;; Tool definitions
;; ---------------------------------------------------------------------------

(defn- str-prop [desc] {:type "string" :description desc})
(defn- int-prop [desc] {:type "integer" :description desc})

(def tools
  "Each tool: :name :description :inputSchema (JSON Schema) and :handler.
   A handler receives [graph args] (args has keyword keys) and returns
   {:text <string> :data <edn>}."
  [{:name "find_matches"
    :description "Find soccer matches by team, opponent, venue, competition, season or date range. Returns match list plus head-to-head summary when two teams are given."
    :inputSchema {:type "object"
                  :properties {:team (str-prop "Team that played (home or away)")
                               :opponent (str-prop "Restrict to matches against this team")
                               :home (str-prop "Team must have played at home")
                               :away (str-prop "Team must have played away")
                               :competition (str-prop "Competition name substring, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'")
                               :season (int-prop "Season year, e.g. 2019")
                               :from (str-prop "Inclusive start date YYYY-MM-DD")
                               :to (str-prop "Inclusive end date YYYY-MM-DD")
                               :limit (int-prop "Max matches to return (default 20)")}}
    :handler (fn [g a]
               (let [a (update a :limit #(or % 20))
                     ms (q/find-matches g a)]
                 (if (and (:team a) (:opponent a))
                   (let [h (q/head-to-head g {:team-a (:team a) :team-b (:opponent a)
                                              :season (:season a) :competition (:competition a)})]
                     {:text (fmt/head-to-head-block h) :data h})
                   {:text (fmt/matches-block ms :header (format "Found %d match(es):" (count ms)))
                    :data ms})))}

   {:name "team_record"
    :description "Win/draw/loss record, goals and points for a team, optionally filtered by season, competition or venue (home/away)."
    :inputSchema {:type "object"
                  :required ["team"]
                  :properties {:team (str-prop "Team name")
                               :season (int-prop "Season year")
                               :competition (str-prop "Competition name substring")
                               :venue {:type "string" :enum ["home" "away" "all"]
                                       :description "Restrict to home or away matches"}}}
    :handler (fn [g a]
               (let [venue (case (:venue a) "home" :home "away" :away nil)
                     r (q/team-record g (assoc a :venue venue))]
                 {:text (fmt/record-block r) :data r}))}

   {:name "head_to_head"
    :description "Head-to-head record between two teams across the datasets (wins, draws, goals and the matches themselves)."
    :inputSchema {:type "object"
                  :required ["team_a" "team_b"]
                  :properties {:team_a (str-prop "First team")
                               :team_b (str-prop "Second team")
                               :season (int-prop "Restrict to a season")
                               :competition (str-prop "Restrict to a competition")}}
    :handler (fn [g a]
               (let [h (q/head-to-head g {:team-a (:team_a a) :team-b (:team_b a)
                                          :season (:season a) :competition (:competition a)})]
                 {:text (fmt/head-to-head-block h) :data h}))}

   {:name "search_players"
    :description "Search the FIFA player database by name, nationality, club, position and minimum overall rating. Sorted by overall rating descending."
    :inputSchema {:type "object"
                  :properties {:name (str-prop "Player name substring")
                               :nationality (str-prop "Nationality, e.g. 'Brazil'")
                               :club (str-prop "Club name")
                               :position (str-prop "Position substring, e.g. 'ST', 'GK', 'CB'")
                               :min_overall (int-prop "Minimum FIFA overall rating")
                               :limit (int-prop "Max players to return (default 20)")}}
    :handler (fn [g a]
               (let [ps (q/search-players g {:name (:name a) :nationality (:nationality a)
                                             :club (:club a) :position (:position a)
                                             :min-overall (:min_overall a)
                                             :limit (or (:limit a) 20)})]
                 {:text (fmt/players-block ps :header (format "Found %d player(s):" (count ps)))
                  :data ps}))}

   {:name "brazilian_players_by_club"
    :description "Brazilian players grouped by their (Brazilian) club, with player counts and average overall rating."
    :inputSchema {:type "object" :properties {}}
    :handler (fn [g _]
               (let [rows (q/players-by-brazilian-club g)]
                 {:text (str "Brazilian players at Brazilian clubs:\n"
                             (->> rows
                                  (map #(format "- %s: %d players (avg rating: %s)"
                                                (:club %) (:count %) (:avg-overall %)))
                                  (str/join "\n")))
                  :data rows}))}

   {:name "standings"
    :description "Compute a league table (standings) for a competition and season from match results: points, W/D/L, goals for/against, goal difference."
    :inputSchema {:type "object"
                  :required ["competition" "season"]
                  :properties {:competition (str-prop "Competition name substring, e.g. 'Brasileirão'")
                               :season (int-prop "Season year, e.g. 2019")}}
    :handler (fn [g a]
               (let [rows (q/standings g a)]
                 {:text (fmt/standings-block
                          rows :header (format "%s %s standings (calculated from matches):"
                                               (:competition a) (:season a)))
                  :data rows}))}

   {:name "biggest_wins"
    :description "Largest-margin victories, optionally filtered by competition and season."
    :inputSchema {:type "object"
                  :properties {:competition (str-prop "Competition name substring")
                               :season (int-prop "Season year")
                               :limit (int-prop "How many to return (default 10)")}}
    :handler (fn [g a]
               (let [ms (q/biggest-wins g a)]
                 {:text (fmt/matches-block ms :header "Biggest victories in dataset:" :show (or (:limit a) 10))
                  :data ms}))}

   {:name "match_statistics"
    :description "Aggregate statistics over a match set: total/average goals per match and home/away/draw win rates."
    :inputSchema {:type "object"
                  :properties {:competition (str-prop "Competition name substring")
                               :season (int-prop "Season year")}}
    :handler (fn [g a]
               (let [s (q/summary-stats g a)]
                 {:text (fmt/stats-block s) :data s}))}

   {:name "best_record"
    :description "Teams ranked by win rate, optionally for home or away matches only, within a competition/season."
    :inputSchema {:type "object"
                  :properties {:competition (str-prop "Competition name substring")
                               :season (int-prop "Season year")
                               :venue {:type "string" :enum ["home" "away" "all"]}
                               :limit (int-prop "How many teams (default 10)")}}
    :handler (fn [g a]
               (let [venue (case (:venue a) "home" :home "away" :away nil)
                     rows (q/best-record g (assoc a :venue venue))
                     label (case (:venue a) "home" "home " "away" "away " "")]
                 {:text (str (format "Best %srecords:\n" label)
                             (->> rows
                                  (map-indexed (fn [i r]
                                                 (format "%d. %s - %.1f%% (%dW %dD %dL of %d)"
                                                         (inc i) (:team r) (double (:win-rate r))
                                                         (:wins r) (:draws r) (:losses r) (:matches r))))
                                  (str/join "\n")))
                  :data rows}))}

   {:name "list_competitions"
    :description "List the competitions available in the knowledge graph with season coverage and match counts."
    :inputSchema {:type "object" :properties {}}
    :handler (fn [g _]
               (let [cs (q/list-competitions g)]
                 {:text (fmt/competitions-block cs) :data cs}))}])

(def ^:private tools-by-name (into {} (map (juxt :name identity) tools)))

(defn tool-list-payload
  "The public {:name :description :inputSchema} view returned by tools/list."
  []
  (mapv #(select-keys % [:name :description :inputSchema]) tools))

;; ---------------------------------------------------------------------------
;; Tool invocation
;; ---------------------------------------------------------------------------

(defn call-tool
  "Invoke a tool by name with an argument map (string OR keyword keys).
   Returns an MCP tool result map. Errors are reported via :isError true so the
   model can recover rather than the whole request failing."
  [tool-name raw-args]
  (if-let [tool (get tools-by-name tool-name)]
    (try
      (let [args (reduce-kv (fn [m k v] (assoc m (keyword k) v)) {} (or raw-args {}))
            {:keys [text data]} ((:handler tool) (data/graph) args)]
        {:content [{:type "text" :text text}]
         :structuredContent {:result data}
         :isError false})
      (catch Exception e
        {:content [{:type "text" :text (str "Error running tool '" tool-name "': " (.getMessage e))}]
         :isError true}))
    {:content [{:type "text" :text (str "Unknown tool: " tool-name)}]
     :isError true}))

;; ---------------------------------------------------------------------------
;; JSON-RPC request handling (pure)
;; ---------------------------------------------------------------------------

(defn handle-request
  "Pure JSON-RPC dispatch. Returns a response map, or nil for notifications
   (requests without an :id) which must not be answered."
  [{:keys [id method params] :as req}]
  (let [ok  (fn [result] {:jsonrpc "2.0" :id id :result result})
        err (fn [code msg] {:jsonrpc "2.0" :id id :error {:code code :message msg}})]
    (case method
      "initialize"
      (ok {:protocolVersion protocol-version
           :capabilities {:tools {:listChanged false}}
           :serverInfo server-info})

      "ping" (ok {})

      "tools/list" (ok {:tools (tool-list-payload)})

      "tools/call"
      (let [{:keys [name arguments]} params]
        (ok (call-tool name arguments)))

      ;; Notifications (initialized, cancelled, ...) carry no id -> no response.
      (if (nil? id)
        nil
        (err -32601 (str "Method not found: " method))))))

;; ---------------------------------------------------------------------------
;; stdio transport (line-delimited JSON, one message per line)
;; ---------------------------------------------------------------------------

(defn serve!
  "Run the stdio server loop, reading newline-delimited JSON-RPC messages from
   `in` and writing responses to `out`. Blocks until EOF."
  [^BufferedReader in out]
  (binding [*out* out]
    (loop []
      (when-let [line (.readLine in)]
        (when-not (str/blank? line)
          (let [resp (try
                       (handle-request (json/read-str line :key-fn keyword))
                       (catch Exception e
                         {:jsonrpc "2.0" :id nil
                          :error {:code -32700 :message (str "Parse error: " (.getMessage e))}}))]
            (when resp
              (println (json/write-str resp))
              (flush))))
        (recur)))))
