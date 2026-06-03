;; =============================================================================
;; brazilian-soccer.mcp
;; -----------------------------------------------------------------------------
;; CONTEXT
;;   Entry point for the Brazilian Soccer MCP server (see TASK.md). Implements
;;   the Model Context Protocol (https://modelcontextprotocol.io) stdio
;;   transport: newline-delimited JSON-RPC 2.0 messages on stdin/stdout, with
;;   all human-facing logging directed to stderr so it never corrupts the
;;   protocol stream.
;;
;;   Supported JSON-RPC methods:
;;     initialize, notifications/initialized, ping, tools/list, tools/call
;;
;;   Each entry in `tools` declares an MCP tool (name, description, JSON-Schema
;;   for its arguments) and a handler. Handlers call brazilian-soccer.queries,
;;   then return BOTH a formatted prose block (brazilian-soccer.format) and the
;;   raw structured data as JSON, so an LLM client can present prose or reason
;;   over the structure. Tool coverage maps onto the spec's five capability
;;   categories (match / team / player / competition / statistical queries).
;;
;;   Run with:  clojure -M:run        (speaks MCP over stdio)
;; =============================================================================
(ns brazilian-soccer.mcp
  (:require [brazilian-soccer.data :as data]
            [brazilian-soccer.format :as fmt]
            [brazilian-soccer.queries :as q]
            [clojure.data.json :as json]
            [clojure.string :as str])
  (:gen-class))

(def protocol-version "2024-11-05")
(def server-info {:name "brazilian-soccer-mcp" :version "1.0.0"})

(defn- log [& xs]
  (binding [*out* *err*]
    (apply println xs)
    (flush)))

;; -----------------------------------------------------------------------------
;; Tool handlers — each takes a keyword-keyed argument map and returns
;; {:text <prose> :data <edn>}.
;; -----------------------------------------------------------------------------

(defn- h-search-matches [a]
  (let [ms (q/search-matches (select-keys a [:team :home :away :opponent
                                             :competition :season :from :to :limit]))]
    {:text (str (count ms) " match(es) found:\n" (fmt/matches->text ms))
     :data ms}))

(defn- h-head-to-head [a]
  (let [r (q/head-to-head (:team_a a) (:team_b a))]
    {:text (fmt/head-to-head->text r) :data (dissoc r :matches)}))

(defn- h-team-stats [a]
  (let [venue (case (some-> (:venue a) str/lower-case)
                "home" :home "away" :away :all)
        r (q/team-stats (:team a)
                        (-> (select-keys a [:competition :season :from :to])
                            (assoc :venue venue)))]
    {:text (fmt/team-stats->text r) :data r}))

(defn- h-standings [a]
  (let [rows (q/standings (:competition a) (:season a))]
    {:text (fmt/standings->text rows a) :data rows}))

(defn- h-competition-stats [a]
  (let [r (q/competition-stats (select-keys a [:competition :season :team :from :to]))]
    {:text (fmt/competition-stats->text r) :data r}))

(defn- h-biggest-wins [a]
  (let [ms (q/biggest-wins (select-keys a [:competition :season :team :limit]))]
    {:text (fmt/biggest-wins->text ms) :data ms}))

(defn- h-search-players [a]
  (let [ps (q/search-players (-> (select-keys a [:name :nationality :club :position :limit])
                                 (assoc :min-overall (:min_overall a))))]
    {:text (str (count ps) " player(s) found:\n" (fmt/players->text ps)) :data ps}))

(defn- h-top-players [a]
  (let [ps (q/top-players (select-keys a [:nationality :club :position :limit]))]
    {:text (fmt/players->text ps) :data ps}))

(defn- h-list-competitions [_]
  (let [ms (data/all-matches)
        comps (->> ms (map :competition) frequencies
                   (sort-by (comp - val)))
        seasons (->> ms (keep :season) distinct sort vec)]
    {:text (str "Competitions (with match counts):\n"
                (str/join "\n" (map (fn [[c n]] (format "- %s: %d matches" c n)) comps))
                (format "\n\nSeasons covered: %s–%s"
                        (first seasons) (last seasons)))
     :data {:competitions (mapv (fn [[c n]] {:competition c :matches n}) comps)
            :seasons seasons
            :total-matches (count ms)
            :total-players (count (data/all-players))}}))

;; -----------------------------------------------------------------------------
;; Tool registry
;; -----------------------------------------------------------------------------

(def ^:private str-schema  {:type "string"})
(def ^:private int-schema  {:type "integer"})

(def tools
  [{:name "search_matches"
    :description "Search matches across all competitions by team, opponent, home/away, competition, season, or date range. Returns matches most-recent first."
    :inputSchema {:type "object"
                  :properties {:team        (assoc str-schema :description "Team involved as home or away (fuzzy, accent-insensitive)")
                               :opponent    (assoc str-schema :description "With `team`, narrows to matches between the two teams")
                               :home        (assoc str-schema :description "Team as home side only")
                               :away        (assoc str-schema :description "Team as away side only")
                               :competition (assoc str-schema :description "Competition name substring, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'")
                               :season      (assoc int-schema :description "Season year, e.g. 2019")
                               :from        (assoc str-schema :description "Earliest match date, ISO YYYY-MM-DD")
                               :to          (assoc str-schema :description "Latest match date, ISO YYYY-MM-DD")
                               :limit       (assoc int-schema :description "Max results (default 100)")}}
    :handler h-search-matches}

   {:name "head_to_head"
    :description "Head-to-head record and match list between two teams across all competitions."
    :inputSchema {:type "object"
                  :properties {:team_a (assoc str-schema :description "First team")
                               :team_b (assoc str-schema :description "Second team")}
                  :required ["team_a" "team_b"]}
    :handler h-head-to-head}

   {:name "team_stats"
    :description "Win/draw/loss and goals record for a team, optionally restricted by competition, season, date range and venue (home/away/all)."
    :inputSchema {:type "object"
                  :properties {:team        (assoc str-schema :description "Team name")
                               :competition (assoc str-schema :description "Competition name substring")
                               :season      (assoc int-schema :description "Season year")
                               :venue       (assoc str-schema :description "'home', 'away' or 'all' (default all)")
                               :from        (assoc str-schema :description "Earliest date ISO")
                               :to          (assoc str-schema :description "Latest date ISO")}
                  :required ["team"]}
    :handler h-team-stats}

   {:name "standings"
    :description "League table for a competition and season, computed from match results (3 pts win, 1 draw). Best for Brasileirão Série A."
    :inputSchema {:type "object"
                  :properties {:competition (assoc str-schema :description "Competition name, e.g. 'Brasileirão Série A'")
                               :season      (assoc int-schema :description "Season year, e.g. 2019")
                               :limit       (assoc int-schema :description "Number of table rows to show (default 20)")}
                  :required ["competition" "season"]}
    :handler h-standings}

   {:name "competition_stats"
    :description "Aggregate statistics (match count, total/average goals, home/away/draw rates) over a filtered match set."
    :inputSchema {:type "object"
                  :properties {:competition (assoc str-schema :description "Competition name substring")
                               :season      (assoc int-schema :description "Season year")
                               :team        (assoc str-schema :description "Restrict to a team's matches")
                               :from        (assoc str-schema :description "Earliest date ISO")
                               :to          (assoc str-schema :description "Latest date ISO")}}
    :handler h-competition-stats}

   {:name "biggest_wins"
    :description "Matches with the largest goal margins, optionally filtered by competition, season or team."
    :inputSchema {:type "object"
                  :properties {:competition (assoc str-schema :description "Competition name substring")
                               :season      (assoc int-schema :description "Season year")
                               :team        (assoc str-schema :description "Restrict to a team's matches")
                               :limit       (assoc int-schema :description "Max results (default 10)")}}
    :handler h-biggest-wins}

   {:name "search_players"
    :description "Search the FIFA player database by name, nationality, club, position and/or minimum overall rating. Sorted by rating."
    :inputSchema {:type "object"
                  :properties {:name        (assoc str-schema :description "Player name substring")
                               :nationality (assoc str-schema :description "Nationality, e.g. 'Brazil'")
                               :club        (assoc str-schema :description "Club name substring, e.g. 'Flamengo'")
                               :position    (assoc str-schema :description "Position code, e.g. 'ST', 'GK', 'LW'")
                               :min_overall (assoc int-schema :description "Minimum FIFA overall rating")
                               :limit       (assoc int-schema :description "Max results (default 50)")}}
    :handler h-search-players}

   {:name "top_players"
    :description "Highest-rated players, optionally filtered by nationality, club or position. E.g. top Brazilian players."
    :inputSchema {:type "object"
                  :properties {:nationality (assoc str-schema :description "Nationality filter, e.g. 'Brazil'")
                               :club        (assoc str-schema :description "Club filter")
                               :position    (assoc str-schema :description "Position filter")
                               :limit       (assoc int-schema :description "Max results (default 10)")}}
    :handler h-top-players}

   {:name "list_competitions"
    :description "List the competitions and seasons available in the dataset, with match and player counts. Good first call to discover coverage."
    :inputSchema {:type "object" :properties {}}
    :handler h-list-competitions}])

(def ^:private tool-by-name
  (into {} (map (juxt :name identity) tools)))

(defn- tool-defs
  "Tool list for tools/list (handlers stripped)."
  []
  (mapv #(dissoc % :handler) tools))

;; -----------------------------------------------------------------------------
;; JSON-RPC dispatch
;; -----------------------------------------------------------------------------

(defn- call-tool [name arguments]
  (if-let [{:keys [handler]} (tool-by-name name)]
    (let [{:keys [text data]} (handler (or arguments {}))]
      {:content [{:type "text" :text text}
                 {:type "text"
                  :text (str "```json\n"
                             (json/write-str data {:escape-unicode false})
                             "\n```")}]
       :isError false})
    {:content [{:type "text" :text (str "Unknown tool: " name)}]
     :isError true}))

(defn handle-request
  "Pure dispatch from a parsed JSON-RPC request map (keyword keys) to a result
   value or {:error {...}}. Returns nil for notifications (no response)."
  [{:keys [method params id]}]
  (case method
    "initialize"
    {:protocolVersion protocol-version
     :capabilities {:tools {}}
     :serverInfo server-info}

    ("notifications/initialized" "initialized" "notifications/cancelled")
    nil

    "ping" {}

    "tools/list" {:tools (tool-defs)}

    "tools/call"
    (try
      (call-tool (:name params) (:arguments params))
      (catch Exception e
        (log "tool error:" (.getMessage e))
        {:content [{:type "text" :text (str "Error: " (.getMessage e))}]
         :isError true}))

    ;; unknown method
    (if id
      {:error {:code -32601 :message (str "Method not found: " method)}}
      nil)))

(defn- response-for [req]
  (let [{:keys [id method]} req]
    (when (some? id) ; requests (with id) get a response; notifications don't
      (let [result (handle-request req)]
        (cond
          (and (map? result) (:error result))
          {:jsonrpc "2.0" :id id :error (:error result)}
          :else
          {:jsonrpc "2.0" :id id :result result})))))

;; -----------------------------------------------------------------------------
;; stdio loop
;; -----------------------------------------------------------------------------

(defn- write-message! [writer msg]
  (locking writer
    (.write writer ^String (json/write-str msg {:escape-unicode false}))
    (.write writer "\n")
    (.flush writer)))

(defn serve!
  "Read newline-delimited JSON-RPC requests from `reader`, write responses to
   `writer`. Blocks until EOF."
  [reader writer]
  (loop []
    (when-let [line (.readLine ^java.io.BufferedReader reader)]
      (when-not (str/blank? line)
        (let [req (try (json/read-str line {:key-fn keyword})
                       (catch Exception e
                         (log "parse error:" (.getMessage e)) nil))]
          (when req
            (try
              (when-let [resp (response-for req)]
                (write-message! writer resp))
              (catch Exception e
                (log "dispatch error:" (.getMessage e))
                (when-let [id (:id req)]
                  (write-message! writer
                                  {:jsonrpc "2.0" :id id
                                   :error {:code -32603 :message (.getMessage e)}})))))))
      (recur))))

(defn -main [& _]
  (log "Brazilian Soccer MCP server starting"
       (format "(%d matches, %d players)"
               (count (data/all-matches)) (count (data/all-players))))
  (let [reader (java.io.BufferedReader. *in*)
        writer *out*]
    (serve! reader writer)
    (log "Brazilian Soccer MCP server stopped")))
