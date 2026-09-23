(ns soccer.server
  "MCP (Model Context Protocol) server over stdio, JSON-RPC 2.0, newline-delimited."
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [soccer.data :as d]
            [soccer.query :as q])
  (:gen-class))

(defn- prop [type desc] {:type type :description desc})

(def match-filter-props
  {:team (prop "string" "Team name (any variation, e.g. 'Flamengo', 'Palmeiras-SP')")
   :opponent (prop "string" "Opponent team name")
   :competition (prop "string" "Brasileirão | Copa do Brasil | Copa Libertadores | Serie B | Serie C")
   :season (prop "integer" "Season year")
   :date_from (prop "string" "ISO date lower bound (yyyy-mm-dd)")
   :date_to (prop "string" "ISO date upper bound (yyyy-mm-dd)")
   :venue (prop "string" "home | away (optional)")
   :limit (prop "integer" "Maximum rows to list")})

(defn- lim [a default] (or (:limit a) default))

(defn- pct [x] (format "%.1f%%" (double x)))

(def tools
  [{:name "search_matches"
    :description "Find matches by team, opponent, competition, season or date range across all match files."
    :props match-filter-props
    :handler (fn [db a]
               (let [ms (q/find-matches db (assoc a :date-from (:date_from a) :date-to (:date_to a)
                                                  :home-only (= "home" (:venue a))
                                                  :away-only (= "away" (:venue a))))
                     n (lim a 25)]
                 (str "Found " (count ms) " matches:\n"
                      (str/join "\n" (map #(str "- " (q/format-match %)) (take n ms)))
                      (when (> (count ms) n) (str "\n- ... (" (- (count ms) n) " more)")))))}
   {:name "head_to_head"
    :description "Head-to-head record and match list between two teams."
    :props (select-keys match-filter-props [:team :opponent :competition :season :limit])
    :required ["team" "opponent"]
    :handler (fn [db a]
               (q/format-h2h (q/head-to-head db (:team a) (:opponent a)
                                             (select-keys a [:competition :season]))
                             (lim a 20)))}
   {:name "team_stats"
    :description "Win/draw/loss record and goals for a team, optionally by season, competition and venue."
    :props (select-keys match-filter-props [:team :competition :season :venue])
    :required ["team"]
    :handler (fn [db a]
               (q/format-record (str (:team a) " " (or (:venue a) "overall") " record"
                                     (when (or (:season a) (:competition a))
                                       (str " (" (str/join " " (remove nil? [(:season a) (:competition a)])) ")")))
                                (q/team-stats db a)))}
   {:name "standings"
    :description "Brasileirão league table for a season, calculated from match results (champion and relegated teams marked)."
    :props {:season (prop "integer" "Season year (2003-2023)")}
    :required ["season"]
    :handler (fn [db a] (q/format-standings (:season a) (q/standings db (:season a))))}
   {:name "top_scoring_teams"
    :description "Teams ranked by goals scored in a Brasileirão season."
    :props {:season (prop "integer" "Season year") :limit (prop "integer" "Rows")}
    :required ["season"]
    :handler (fn [db a]
               (str "Most goals scored, " (:season a) " Brasileirão:\n"
                    (str/join "\n" (map-indexed #(str (inc %1) ". " (:team %2) " - " (:goals-for %2) " goals")
                                                (take (lim a 10) (q/top-scoring-teams db (:season a)))))))}
   {:name "competition_stats"
    :description "Aggregate stats (avg goals per match, home/away/draw rates) for a competition and/or season, plus biggest wins."
    :props (select-keys match-filter-props [:competition :season :team :limit])
    :handler (fn [db a]
               (let [ms (q/find-matches db a) s (q/summary-stats ms)]
                 (str "Statistics" (when (:competition a) (str " for " (:competition a)))
                      (when (:season a) (str " " (:season a))) ":\n"
                      "- Matches: " (:matches s) "\n- Goals: " (:goals s)
                      (format "\n- Average goals per match: %.2f" (:avg-goals s))
                      "\n- Home win rate: " (pct (:home-win-rate s))
                      "\n- Away win rate: " (pct (:away-win-rate s))
                      "\n- Draw rate: " (pct (:draw-rate s))
                      "\n\nBiggest victories:\n"
                      (str/join "\n" (map-indexed #(str (inc %1) ". " (q/format-match %2))
                                                  (q/biggest-wins ms (lim a 10)))))))}
   {:name "best_records"
    :description "Rank teams by win rate (overall, home or away)."
    :props (assoc (select-keys match-filter-props [:competition :season :venue :limit])
                  :min_matches (prop "integer" "Minimum matches to qualify (default 20)"))
    :handler (fn [db a]
               (str "Best " (or (:venue a) "overall") " records:\n"
                    (str/join "\n" (map-indexed
                                    #(format "%d. %s - %.1f%% (%dW %dD %dL in %d)" (inc %1) (:team %2)
                                             (double (:win-rate %2)) (:wins %2) (:draws %2) (:losses %2) (:matches %2))
                                    (take (lim a 10) (q/best-records db (assoc a :min-matches (or (:min_matches a) 20))))))))}
   {:name "team_competitions"
    :description "Which competitions a team has played in (across all match files)."
    :props (select-keys match-filter-props [:team])
    :required ["team"]
    :handler (fn [db a]
               (str (:team a) " competitions in dataset:\n"
                    (str/join "\n" (map #(str "- " (:competition %) ": " (:matches %) " matches, seasons "
                                              (first (:seasons %)) "-" (last (:seasons %)))
                                        (q/team-competitions db (:team a))))))}
   {:name "cup_finals"
    :description "Finals of Copa do Brasil or Copa Libertadores."
    :props (select-keys match-filter-props [:competition])
    :handler (fn [db a]
               (str "Finals:\n" (str/join "\n" (map #(str "- " (q/format-match %))
                                                    (q/cup-finals db (:competition a))))))}
   {:name "derbies"
    :description "Traditional rivalry (derby) matches, e.g. Fla-Flu, Grenal, Derby Paulista."
    :props (select-keys match-filter-props [:season :competition :team :limit])
    :handler (fn [db a]
               (let [ms (q/derbies db a)]
                 (str "Derbies found: " (count ms) "\n"
                      (str/join "\n" (map #(str "- " (q/format-match %)) (take (lim a 30) ms))))))}
   {:name "search_players"
    :description "Search FIFA player data by name, nationality, club and position (e.g. 'forward', 'GK')."
    :props {:name (prop "string" "Player name substring")
            :nationality (prop "string" "e.g. Brazil")
            :club (prop "string" "Club name")
            :position (prop "string" "Position code or forward/midfielder/defender/goalkeeper")
            :limit (prop "integer" "Max results (default 20)")}
    :handler (fn [db a]
               (q/format-players "Players (sorted by overall rating):"
                                 (q/find-players db (assoc a :limit (lim a 20)))))}
   {:name "brazilian_players_by_club"
    :description "Brazilian players grouped by club with average rating (Brazilian clubs only by default)."
    :props {:all_clubs (prop "boolean" "Include non-Brazilian clubs")}
    :handler (fn [db a]
               (str "Brazilian players by club:\n"
                    (str/join "\n" (map #(format "- %s: %d players (avg rating: %.0f)" (:club %) (:players %) (:avg-rating %))
                                        (q/players-by-club-summary
                                         db {:nationality "Brazil" :clubs (when-not (:all_clubs a) q/brazilian-clubs)})))))}
   {:name "player_profile"
    :description "Player details plus their club's record in the match data (cross-file query)."
    :props {:name (prop "string" "Player name")}
    :required ["name"]
    :handler (fn [db a]
               (if-let [{:keys [player club-record]} (q/player-team-profile db (:name a))]
                 (str (q/format-players "Player:" [player])
                      "\nPotential: " (:potential player) ", Height: " (:height player)
                      ", Weight: " (:weight player) ", Value: " (:value player)
                      "\nSkills: " (str/join ", " (map (fn [[k v]] (str k " " v)) (:skills player)))
                      (when (and club-record (pos? (:matches club-record)))
                        (str "\n\n" (q/format-record (str (:club player) " record in match data") club-record))))
                 (str "No player found matching " (:name a))))}])

(def tools-by-name (into {} (map (juxt :name identity)) tools))

(defn tool-descriptor [{:keys [name description props required]}]
  {:name name :description description
   :inputSchema (cond-> {:type "object" :properties props} required (assoc :required required))})

(defn call-tool [db name args]
  (if-let [t (tools-by-name name)]
    ((:handler t) db (into {} (map (fn [[k v]] [(keyword k) v])) args))
    (throw (ex-info (str "Unknown tool: " name) {:code -32602}))))

(defn handle
  "Handle one JSON-RPC request map; returns a response map or nil for notifications."
  [db {:strs [id method params] :as _req}]
  (let [ok (fn [r] {:jsonrpc "2.0" :id id :result r})]
    (try
      (case method
        "initialize" (ok {:protocolVersion (or (get params "protocolVersion") "2024-11-05")
                          :capabilities {:tools {}}
                          :serverInfo {:name "brazilian-soccer" :version "1.0.0"}})
        "ping" (ok {})
        "tools/list" (ok {:tools (mapv tool-descriptor tools)})
        "tools/call" (ok {:content [{:type "text"
                                     :text (call-tool (db) (get params "name") (get params "arguments" {}))}]})
        (if (nil? id) nil
            {:jsonrpc "2.0" :id id :error {:code -32601 :message (str "Method not found: " method)}}))
      (catch Exception e
        (if (= -32602 (:code (ex-data e)))
          {:jsonrpc "2.0" :id id :error {:code -32602 :message (.getMessage e)}}
          (ok {:content [{:type "text" :text (str "Error: " (.getMessage e))}] :isError true}))))))

(defn -main [& _]
  (let [db (memoize d/db)]
    (future (db))                      ; warm the cache while the client initializes
    (doseq [line (line-seq (java.io.BufferedReader. *in*))
            :when (seq (str/trim line))]
      (let [resp (try (handle db (json/read-str line))
                      (catch Exception _ {:jsonrpc "2.0" :id nil :error {:code -32700 :message "Parse error"}}))]
        (when resp
          (println (json/write-str resp))
          (flush))))))
