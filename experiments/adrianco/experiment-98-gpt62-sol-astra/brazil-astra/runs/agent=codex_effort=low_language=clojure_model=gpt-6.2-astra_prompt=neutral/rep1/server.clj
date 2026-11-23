(ns server
  (:require [clojure.data.json :as json] [clojure.java.io :as io] [soccer :as soccer]))

(defn string-field [description] {:type "string" :description description})
(defn choices [& values] {:type "string" :enum (vec values)})
(def paging {:limit {:type "integer" :minimum 1 :maximum 100}
             :offset {:type "integer" :minimum 0}})
(def filters
  {:team_name (string-field "Team in either role unless venue is supplied")
   :opponent (string-field "Second team for head-to-head, requires team_name")
   :venue (choices "home" "away")
   :season {:type "integer"}
   :competition (string-field "Serie A (Brasileirão), Serie B, Serie C, Copa do Brasil or Libertadores")
   :source (apply choices soccer/files)
   :start {:type "string" :format "date" :description "Inclusive earliest match date"}
   :end {:type "string" :format "date" :description "Inclusive latest match date"}
   :stage (string-field "Stage such as final, semifinals, group stage, or numeric round as a string")
   :derby {:type "boolean" :description "Restrict to recognized traditional rivalries"}})

(defn tool [name description props & required]
  {:name name :description description
   :inputSchema {:type "object" :properties props :required (vec required) :additionalProperties false}})

(def catalog
  [(tool "matches" "Fixtures, scores, dates and original match details, newest first. Use limit 1 for latest."
               (merge filters paging))
         (tool "team_profile" "Team record, head-to-head, trends, competitions and FIFA roster. Venue is relative to team_name."
               (merge filters paging) "team_name")
         (tool "players" "FIFA snapshot sorted by overall rating, with original attributes. Nationality uses country names."
               (merge paging {:name (string-field "Partial player name") :nationality (string-field "Country, e.g. Brazil")
                              :club (string-field "Club name") :position (string-field "FIFA position or forward")}))
         (tool "standings" "Calculated table from played fixtures. Use competition and season for league standings. Venue restricts each team's record."
               (merge filters paging {:rank_by (choices "points" "goals" "win_rate")}))
         (tool "statistics" "Fixture counts, average total goals and home win rate, optionally grouped."
               (assoc filters :group_by (choices "competition" "season")))
         (tool "biggest_wins" "Completed matches ranked by absolute goal difference." (merge filters paging))])

(defn valid-value? [{:keys [type enum minimum maximum format]} value]
  (and (case type "string" (string? value) "integer" (integer? value) "boolean" (boolean? value))
       (or (nil? enum) (some #{value} enum))
       (or (nil? minimum) (<= minimum value))
       (or (nil? maximum) (<= value maximum))
       (or (nil? format) (try (java.time.LocalDate/parse value) true (catch Exception _ false)))))

(defn validate [schema args]
  (when-not (and (map? args)
                 (every? #(contains? args (keyword %)) (:required schema))
                 (every? (fn [[k v]] (when-let [field (get (:properties schema) k)] (valid-value? field v))) args)
                 (or (nil? (:opponent args)) (:team_name args))
                 (or (nil? (:start args)) (nil? (:end args)) (<= (compare (:start args) (:end args)) 0)))
    (throw (ex-info "Invalid tool arguments. Check the tool schema, date range and required team." {:code -32602}))))

(defn call-tool [db {:keys [name arguments] :or {arguments {}}}]
  (let [definition (first (filter #(= name (:name %)) catalog))]
    (when-not definition (throw (ex-info "Unknown tool" {:code -32602})))
    (validate (:inputSchema definition) arguments)
    {:content [{:type "text" :text (json/write-str (soccer/query db name arguments) :escape-unicode false)}]}))

(defn dispatch [db {:keys [id method params jsonrpc] :as request}]
  (try
    (when-not (and (= "2.0" jsonrpc) (string? method))
      (throw (ex-info "Invalid request" {:code -32600})))
    (when (contains? request :id)
      {:jsonrpc "2.0" :id id
       :result (case method
                 "initialize" {:protocolVersion (case (:protocolVersion params)
                                                  "2024-11-05" "2024-11-05"
                                                  "2025-03-26" "2025-03-26" "2025-06-18")
                               :capabilities {:tools {}}
                               :serverInfo {:name "brazilian-soccer" :version "1.0.0"}
                               :instructions "Answer from dataset coverage. Missing scores mean unknown. FIFA is a historical snapshot. Individual goal scorers are unavailable."}
                 "ping" {}
                 "tools/list" {:tools catalog}
                 "tools/call" (call-tool db params)
                 (throw (ex-info "Method not found" {:code -32601})))})
    (catch Exception e
      {:jsonrpc "2.0" :id id :error {:code (get (ex-data e) :code -32603) :message (.getMessage e)}})))

(defn -main [& [dir]]
  (let [db (soccer/load-db (or dir "data/kaggle"))]
    (with-open [reader (io/reader System/in :encoding "UTF-8")
                writer (io/writer System/out :encoding "UTF-8")]
      (doseq [line (line-seq reader)]
        (let [response (try (dispatch db (json/read-str line :key-fn keyword))
                            (catch Exception _ {:jsonrpc "2.0" :id nil :error {:code -32700 :message "Parse error"}}))]
          (when response
            (.write writer (str (json/write-str response) "\n"))
            (.flush writer)))))))
