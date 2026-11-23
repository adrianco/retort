(ns soccer.server
  (:require [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [soccer.data :as data]
            [soccer.query :as query]))

(defn text-field [description]
  {:type "string" :minLength 1 :description description})

(defn integer-field [description minimum]
  {:type "integer" :minimum minimum :description description})

(defn choices [description values]
  (assoc (text-field description) :enum values))

(def paging-fields
  {:limit (assoc (integer-field "Page size. Defaults to 20." 1) :maximum 200)
   :offset (integer-field "Zero-based offset. Use next-offset to continue." 0)})

(def match-fields
  {:team (text-field "Team name or recognized alias.")
   :opponent (text-field "Opponent name for head-to-head fixtures. Requires team.")
   :venue (choices "Side on which team played, or side used for ranking." ["home" "away" "either"])
   :competition (text-field "Competition name. Examples include Serie A, Copa do Brasil and Libertadores.")
   :season (integer-field "Competition season year." 1900)
   :from (text-field "Inclusive start date, YYYY-MM-DD or DD/MM/YYYY.")
   :to (text-field "Inclusive end date, YYYY-MM-DD or DD/MM/YYYY.")
   :round (integer-field "Recorded round number." 1)
   :stage (choices "Recorded tournament stage."
                   ["group stage" "round of 16" "quarterfinals" "semifinals" "final"])
   :source (choices "Optional CSV filename to query its original rows." (vec (butlast data/files)))
   :derby {:type "boolean" :description "True selects fixtures between recognized traditional rivals."}
   :completed {:type "boolean" :description "True selects scored matches. False selects fixtures missing scores."}})

(def player-fields
  {:name (text-field "Player name or part of the name.")
   :nationality (text-field "FIFA nationality, such as Brazil.")
   :club (text-field "Club name in the FIFA snapshot.")
   :position (text-field "FIFA position code or forwards.")
   :domestic-only {:type "boolean" :description "True selects clubs found in Brazilian domestic match files."}})

(def attributes-field
  {:include-attributes {:type "boolean" :description "Include all recorded FIFA attributes, including skill ratings."}})

(defn tool [name description required fields handler]
  {:name name :description description
   :inputSchema {:type "object" :properties fields :required required :additionalProperties false}
   :annotations {:readOnlyHint true :openWorldHint false}
   :handler handler})

(def tools
  (let [match-page (merge match-fields paging-fields)
        player-page (merge player-fields paging-fields)]
    [(tool "find_matches" "Find dates, schedules and scores across all match CSVs. Latest dated fixtures appear first. Use stage final for cup finals and derby true for traditional rivalries." []
           match-page query/find-matches)
     (tool "team_stats" "Calculate a team's record, goals and win rate, with season, competition, home and away breakdowns. Win rates are fractions." [:team]
           match-fields query/team-stats)
     (tool "head_to_head" "Compare two teams' wins, draws, losses and goals. Includes a page of fixtures and scores." [:team :opponent]
           match-page query/head-to-head)
     (tool "find_players" "Search the historical FIFA player snapshot, highest overall ratings first. Use include-attributes for skill ratings and biographical attributes." []
           (merge player-page attributes-field) query/find-players)
     (tool "club_player_summary" "Count matching FIFA players and calculate their average overall rating by club. Use nationality Brazil and domestic-only true for Brazilian players at Brazilian clubs." []
           player-page query/club-player-summary)
     (tool "club_profile" "Join a club's match records and statistics with players listed for the same club in the FIFA snapshot. Match filters apply to the team history." [:team]
           (merge match-page (dissoc player-fields :club) attributes-field) query/club-profile)
     (tool "standings" "Calculate league tables and show the leader. A complete modern Série A season includes its bottom four. Defaults to Série A." [:season]
           (select-keys match-fields [:competition :season :source]) query/standings)
     (tool "knockout_bracket" "Show cup knockout fixtures and scores by stage or round for a season. Penalty scores are unavailable." [:competition :season]
           (select-keys match-fields [:competition :season :source :stage]) query/knockout-bracket)
     (tool "match_statistics" "Calculate goals per match, home win rate, season comparisons and biggest victories. Win rates are fractions." []
           match-page query/match-statistics)
     (tool "team_leaders" "Rank teams by goals scored, win rate, wins, points or goal difference. Use venue for home or away rankings." []
           (assoc match-page
                  :metric (choices "Ranking metric. Defaults to win-rate."
                                   ["goals-for" "win-rate" "wins" "points" "goal-difference"])
                  :min-played (integer-field "Minimum scored matches for a team." 1))
           query/team-leaders)
     (tool "data_coverage" "List supplied CSVs and their row counts, and explain availability of individual match goalscorers." []
           {} (fn [db _]
                {:sources (assoc (update-vals (:sources db) count) (last data/files) (count (:players db)))
                 :combined-fixtures (count (:matches db))
                 :individual-goalscorers-available false
                 :note "The match CSVs record team scores. The FIFA CSV records player ratings and attributes."}))]))

(def tool-by-name (into {} (map (juxt :name identity)) tools))

(defn valid-value? [{:keys [type enum minimum maximum]} value]
  (and (case type
         "string" (and (string? value) (not (str/blank? value)))
         "integer" (and (integer? value) (<= minimum value (or maximum Long/MAX_VALUE)))
         "boolean" (boolean? value))
       (or (nil? enum) (some #{value} enum))))

(defn validate [{:keys [properties required]} args]
  (when-not (map? args)
    (throw (ex-info "Tool arguments must be an object." {})))
  (doseq [field required]
    (when-not (contains? args field)
      (throw (ex-info (str "Missing required argument: " (name field)) {}))))
  (doseq [[field value] args]
    (when-not (and (contains? properties field) (valid-value? (properties field) value))
      (throw (ex-info (str "Invalid argument: " (name field)) {}))))
  (when (and (contains? args :opponent) (not (contains? args :team)))
    (throw (ex-info "The opponent argument requires a team." {}))))

(defn call-tool [db tool args]
  (try
    (validate (:inputSchema tool) args)
    (let [result ((:handler tool) db args)]
      {:structuredContent result
       :content [{:type "text" :text (json/write-str result :escape-unicode false)}]
       :isError false})
    (catch clojure.lang.ExceptionInfo e
      {:content [{:type "text" :text (.getMessage e)}] :isError true})))

(def protocol-versions #{"2024-11-05" "2025-03-26" "2025-06-18"})

(defn error [id code message]
  {:jsonrpc "2.0" :id id :error {:code code :message message}})

(defn handle [db {:keys [id jsonrpc method params] :as message}]
  (cond
    (not (and (map? message) (= "2.0" jsonrpc) (string? method)
              (or (nil? id) (integer? id) (string? id))))
    (error nil -32600 "Invalid Request")

    (not (contains? message :id)) nil

    :else
    (let [reply #(hash-map :jsonrpc "2.0" :id id :result %)]
      (case method
        "initialize" (reply {:protocolVersion (get protocol-versions (:protocolVersion params) "2025-06-18")
                             :capabilities {:tools {}}
                             :serverInfo {:name "brazilian-soccer" :version "1.0.0"}
                             :instructions "Use tool filters to translate soccer questions. Use earlier tool results for follow-ups about the same fixture."})
        "ping" (reply {})
        "tools/list" (reply {:tools (mapv #(dissoc % :handler) tools)})
        "tools/call" (if-let [tool (tool-by-name (:name params))]
                       (reply (call-tool db tool (get params :arguments {})))
                       (error id -32602 "Unknown tool"))
        (error id -32601 "Method not found")))))

(defn process-line [db line]
  (let [message (try
                  (json/read-str line :key-fn keyword)
                  (catch Exception _ ::invalid-json))]
    (if (= message ::invalid-json)
      (error nil -32700 "Parse error")
      (try
        (handle db message)
        (catch Exception _
          (error (when (map? message) (:id message)) -32603 "Internal error"))))))

(defn serve [db reader writer]
  (doseq [line (line-seq reader)]
    (when-let [response (process-line db line)]
      (.write writer (str (json/write-str response :escape-unicode false) "\n"))
      (.flush writer))))

(defn -main [& [directory]]
  (let [db (data/load-data (or directory "data/kaggle"))]
    (with-open [reader (io/reader System/in :encoding "UTF-8")
                writer (io/writer System/out :encoding "UTF-8")]
      (serve db reader writer))))
