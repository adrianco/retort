(ns brazilian-soccer.mcp
  "MCP (Model Context Protocol) server exposing the Brazilian soccer knowledge
  graph as a set of tools, spoken as JSON-RPC 2.0 over stdio.

  `handle-request` is a pure function of (db, request) -> response (or nil for
  notifications), which keeps the protocol logic fully unit-testable. `-main`
  loads the datasets once and then pumps stdin/stdout through it."
  (:require [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [clojure.walk :as walk]
            [brazilian-soccer.normalize :as normalize]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.queries :as q]
            [brazilian-soccer.format :as fmt])
  (:gen-class))

(def ^:private protocol-version "2024-11-05")

(def ^:private server-info
  {:name "brazilian-soccer" :version "1.0.0"})

;; ---------------------------------------------------------------------------
;; Tool definitions
;; ---------------------------------------------------------------------------

(defn- str-prop [desc] {:type "string" :description desc})
(defn- int-prop [desc] {:type "integer" :description desc})

(def tools
  "MCP tool descriptors advertised via tools/list."
  [{:name "find_matches"
    :description "Find soccer matches by team, opponent, competition, season, venue or date range."
    :inputSchema
    {:type "object"
     :properties {:team (str-prop "Team name (home or away), e.g. \"Flamengo\".")
                  :opponent (str-prop "Restrict to matches against this team.")
                  :competition (str-prop "Brasileirão, Copa do Brasil or Libertadores.")
                  :season (int-prop "Season/year, e.g. 2019.")
                  :venue (str-prop "\"home\" or \"away\" to restrict the team's side.")
                  :from (str-prop "Inclusive start date (YYYY-MM-DD).")
                  :to (str-prop "Inclusive end date (YYYY-MM-DD).")
                  :limit (int-prop "Maximum number of matches to return.")}}}
   {:name "head_to_head"
    :description "Head-to-head record (wins, draws, goals) between two teams."
    :inputSchema
    {:type "object"
     :properties {:team_a (str-prop "First team.")
                  :team_b (str-prop "Second team.")}
     :required ["team_a" "team_b"]}}
   {:name "team_record"
    :description "Win/draw/loss record, goals and points for a team, optionally by competition/season/venue."
    :inputSchema
    {:type "object"
     :properties {:team (str-prop "Team name.")
                  :competition (str-prop "Optional competition filter.")
                  :season (int-prop "Optional season/year filter.")
                  :venue (str-prop "Optional \"home\" or \"away\" filter.")}
     :required ["team"]}}
   {:name "standings"
    :description "League table for a competition and season, calculated from match results."
    :inputSchema
    {:type "object"
     :properties {:competition (str-prop "Competition, e.g. Brasileirão.")
                  :season (int-prop "Season/year.")}
     :required ["competition" "season"]}}
   {:name "search_players"
    :description "Search FIFA players by name, nationality, club or position, sorted by overall rating."
    :inputSchema
    {:type "object"
     :properties {:name (str-prop "Substring of the player's name.")
                  :nationality (str-prop "Nationality, e.g. Brazil.")
                  :club (str-prop "Club name substring.")
                  :position (str-prop "Position code, e.g. ST, GK, LW.")
                  :limit (int-prop "Maximum number of players to return.")}}}
   {:name "statistics"
    :description "Aggregate statistics (avg goals, home win rate, biggest wins) over a competition/season."
    :inputSchema
    {:type "object"
     :properties {:competition (str-prop "Optional competition filter.")
                  :season (int-prop "Optional season/year filter.")}}}])

;; ---------------------------------------------------------------------------
;; Tool dispatch
;; ---------------------------------------------------------------------------

(defn- ->int [x]
  (cond (integer? x) x
        (string? x) (try (Long/parseLong (str/trim x)) (catch Exception _ nil))
        (number? x) (long x)
        :else nil))

(defn- venue-kw [v]
  (case (some-> v str str/lower-case)
    "home" :home
    "away" :away
    nil))

(defn- get-date [a k]
  (some-> (get a k) normalize/parse-date))

(defn- run-tool [db name args]
  (let [a args]
    (case name
      "find_matches"
      (fmt/matches
       (q/find-matches db {:team (get a "team")
                           :opponent (get a "opponent")
                           :competition (get a "competition")
                           :season (->int (get a "season"))
                           :venue (venue-kw (get a "venue"))
                           :from (get-date a "from")
                           :to (get-date a "to")
                           :limit (->int (get a "limit"))}))

      "head_to_head"
      (fmt/head-to-head (q/head-to-head db (get a "team_a") (get a "team_b")))

      "team_record"
      (fmt/team-record (q/team-record db (get a "team")
                                      {:competition (get a "competition")
                                       :season (->int (get a "season"))
                                       :venue (venue-kw (get a "venue"))}))

      "standings"
      (fmt/standings (get a "competition") (->int (get a "season"))
                     (q/standings db (get a "competition") (->int (get a "season"))))

      "search_players"
      (fmt/players (q/search-players db {:name (get a "name")
                                         :nationality (get a "nationality")
                                         :club (get a "club")
                                         :position (get a "position")
                                         :limit (->int (get a "limit"))}))

      "statistics"
      (let [competition (get a "competition")
            season (->int (get a "season"))
            ms (q/find-matches db (cond-> {}
                                    competition (assoc :competition competition)
                                    season (assoc :season season)))
            scope (->> [season competition "matches"] (remove nil?) (str/join " "))]
        (fmt/statistics {:scope (str "Statistics for " scope ":")
                         :total-matches (count ms)
                         :avg-goals (q/avg-goals-per-match ms)
                         :home-win-rate (q/home-win-rate ms)
                         :biggest (q/biggest-wins ms 3)}))

      (throw (ex-info (str "Unknown tool: " name) {:tool name})))))

;; ---------------------------------------------------------------------------
;; JSON-RPC handling
;; ---------------------------------------------------------------------------

(defn- result [id r] {:jsonrpc "2.0" :id id :result r})
(defn- error [id code message] {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn handle-request
  "Handle one parsed JSON-RPC request map. Returns a response map, or nil for
  notifications (requests without an :id)."
  [db {:keys [id method params]}]
  (cond
    (nil? id)
    nil ; notification — no response

    (= method "initialize")
    (result id {:protocolVersion protocol-version
                :capabilities {:tools {}}
                :serverInfo server-info})

    (= method "tools/list")
    (result id {:tools tools})

    (= method "tools/call")
    (let [tool-name (:name params)
          ;; Arguments are user-supplied JSON; accept either string- or
          ;; keyword-keyed maps and normalize to string keys internally.
          args (walk/stringify-keys (or (:arguments params) {}))]
      (try
        (result id {:content [{:type "text" :text (run-tool db tool-name args)}]})
        (catch Exception e
          (result id {:content [{:type "text"
                                 :text (str "Error: " (.getMessage e))}]
                      :isError true}))))

    :else
    (error id -32601 (str "Method not found: " method))))

;; ---------------------------------------------------------------------------
;; stdio loop
;; ---------------------------------------------------------------------------

(defn- write-response! [w resp]
  (when resp
    (.write w (json/write-str resp))
    (.write w "\n")
    (.flush w)))

(defn serve
  "Read newline-delimited JSON-RPC requests from `in` and write responses to
  `out` until EOF."
  [db in out]
  (let [r (io/reader in)
        w (io/writer out)]
    (loop []
      (when-let [line (.readLine r)]
        (when-not (str/blank? line)
          (let [resp (try
                       (handle-request db (json/read-str line :key-fn keyword))
                       (catch Exception e
                         (error nil -32700 (str "Parse error: " (.getMessage e)))))]
            (write-response! w resp)))
        (recur)))))

(defn -main
  "Entry point: load the datasets, then serve MCP over stdio."
  [& args]
  (let [dir (or (first args) (System/getenv "BR_SOCCER_DATA") "data/kaggle")
        db (data/load-db dir)]
    (binding [*out* *err*]
      (println (format "brazilian-soccer MCP server: loaded %d matches, %d players from %s"
                       (count (:matches db)) (count (:players db)) dir)))
    (serve db System/in System/out)))
