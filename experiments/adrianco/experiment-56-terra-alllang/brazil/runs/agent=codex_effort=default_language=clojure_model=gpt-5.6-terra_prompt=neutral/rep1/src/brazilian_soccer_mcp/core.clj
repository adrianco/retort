(ns brazilian-soccer-mcp.core
  (:require [clojure.java.io :as io] [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]))

(def dataset-files
  [{:file "Brasileirao_Matches.csv" :competition "Brasileirão" :kind :standard}
   {:file "Brazilian_Cup_Matches.csv" :competition "Copa do Brasil" :kind :standard}
   {:file "Libertadores_Matches.csv" :competition "Copa Libertadores" :kind :standard}
   {:file "BR-Football-Dataset.csv" :kind :extended}
   {:file "novo_campeonato_brasileiro.csv" :competition "Brasileirão" :kind :historical}])

(defn canonical-name [value]
  (-> (or value "") str str/trim
      (str/replace #"(?i)-\s*[A-Z]{2}$" "")
      (str/replace #"(?i)\b(esporte clube|sport club|football club|futebol clube|fc)\b" "")
      (Normalizer/normalize Normalizer$Form/NFD)
      (str/replace #"\p{M}" "") str/lower-case
      (str/replace #"[^a-z0-9]+" " ") str/trim))

(defn parse-int [value]
  (when (and value (not (str/blank? (str value))))
    (try (int (Math/round (Double/parseDouble (str value)))) (catch Exception _ nil))))

(defn normalize-date [value]
  (let [v (str/trim (or value ""))]
    (cond (re-matches #"\d{4}-\d{2}-\d{2}.*" v) (subs v 0 10)
          (re-matches #"\d{2}/\d{2}/\d{4}" v) (let [[d m y] (str/split v #"/")] (str y "-" m "-" d))
          :else v)))

(defn parse-csv-line [line]
  (loop [chars (seq line) fields [] field (StringBuilder.) quoted? false]
    (if-let [c (first chars)]
      (cond (= c \") (if (and quoted? (= (second chars) \"))
                       (do (.append field c) (recur (nnext chars) fields field quoted?))
                       (recur (next chars) fields field (not quoted?)))
            (and (= c \,) (not quoted?)) (recur (next chars) (conj fields (str field)) (StringBuilder.) false)
            :else (do (.append field c) (recur (next chars) fields field quoted?)))
      (conj fields (str field)))))

(defn read-csv [path]
  (with-open [r (io/reader path)]
    (let [lines (doall (line-seq r))
          headers (mapv #(str/replace % #"^\uFEFF" "") (parse-csv-line (first lines)))]
      (mapv #(zipmap headers (parse-csv-line %)) (rest lines)))))

(defn standard-match [{:strs [datetime home_team away_team home_goal away_goal season round stage]} competition source]
  {:date (normalize-date datetime) :season (parse-int season) :round (or round stage)
   :competition competition :home-team home_team :away-team away_team
   :home-key (canonical-name home_team) :away-key (canonical-name away_team)
   :home-goals (parse-int home_goal) :away-goals (parse-int away_goal) :source source})

(defn extended-match [{:strs [tournament home away home_goal away_goal date time] :as row} source]
  (assoc (standard-match {"datetime" (str date " " time) "home_team" home "away_team" away
                          "home_goal" home_goal "away_goal" away_goal "season" (subs (normalize-date date) 0 4)}
                         tournament source)
         :statistics (select-keys row ["home_corner" "away_corner" "home_attack" "away_attack" "home_shots" "away_shots" "total_corners"])))

(defn historical-match [{:strs [Data Ano Rodada Equipe_mandante Equipe_visitante Gols_mandante Gols_visitante Arena]} source]
  (assoc (standard-match {"datetime" Data "home_team" Equipe_mandante "away_team" Equipe_visitante
                          "home_goal" Gols_mandante "away_goal" Gols_visitante "season" Ano "round" Rodada}
                         "Brasileirão" source) :stadium Arena))

(defn load-matches
  ([] (load-matches "data/kaggle"))
  ([directory]
   (vec (mapcat (fn [{:keys [file competition kind]}]
     (let [source file rows (read-csv (io/file directory file))]
       (map #(case kind :extended (extended-match % source) :historical (historical-match % source)
                       (standard-match % competition source)) rows))) dataset-files))))

(defn load-players
  ([] (load-players "data/kaggle"))
  ([directory] (mapv (fn [row]
    {:id (get row "ID") :name (get row "Name") :age (parse-int (get row "Age"))
     :nationality (get row "Nationality") :overall (parse-int (get row "Overall"))
     :potential (parse-int (get row "Potential")) :club (get row "Club") :position (get row "Position")
     :jersey-number (parse-int (get row "Jersey Number"))})
    (read-csv (io/file directory "fifa_data.csv")))))
(defn load-data ([] (load-data "data/kaggle")) ([directory] {:matches (load-matches directory) :players (load-players directory)}))
(defn contains-name? [candidate query] (str/includes? (canonical-name candidate) (canonical-name query)))
(defn between? [date from to] (and (or (nil? from) (not (neg? (compare date from)))) (or (nil? to) (not (pos? (compare date to))))))

(defn search-matches [matches {:keys [team home-team away-team opponent competition season from-date to-date round limit] :or {limit 100}}]
  (let [season (parse-int season) wanted (some-> competition canonical-name)]
    (->> matches
      (filter #(and (or (nil? team) (or (contains-name? (:home-team %) team) (contains-name? (:away-team %) team)))
                    (or (nil? home-team) (contains-name? (:home-team %) home-team))
                    (or (nil? away-team) (contains-name? (:away-team %) away-team))
                    (or (nil? opponent) (or (contains-name? (:home-team %) opponent) (contains-name? (:away-team %) opponent)))
                    (or (nil? wanted) (contains-name? (:competition %) wanted))
                    (or (nil? season) (= season (:season %))) (between? (:date %) from-date to-date)
                    (or (nil? round) (= (str round) (str (:round %))))))
      (sort-by :date #(compare %2 %1)) (take (min 1000 (max 1 (or (parse-int limit) 100)))) vec)))

(defn record-for [matches team {:keys [season competition venue]}]
  (let [key (canonical-name team)
        relevant (filter #(and (or (nil? season) (= (parse-int season) (:season %)))
                               (or (nil? competition) (contains-name? (:competition %) competition))
                               (case venue "home" (= key (:home-key %)) "away" (= key (:away-key %))
                                     (or (= key (:home-key %)) (= key (:away-key %))))) matches)]
    (reduce (fn [r m] (let [home? (= key (:home-key m)) gf (if home? (:home-goals m) (:away-goals m)) ga (if home? (:away-goals m) (:home-goals m))]
      (cond-> (update r :matches inc) (some? gf) (-> (update :goals-for + gf) (update :goals-against + ga)
        (update (cond (> gf ga) :wins (= gf ga) :draws :else :losses) inc)))))
      {:team team :matches 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0} relevant)))
(defn team-statistics [matches team filters]
  (let [r (record-for matches team filters)] (assoc r :points (+ (* 3 (:wins r)) (:draws r)) :win-rate (if (pos? (:matches r)) (* 100.0 (/ (:wins r) (:matches r))) 0.0))))

(defn head-to-head [matches team-a team-b filters]
  (let [games (search-matches matches (merge filters {:team team-a :opponent team-b :limit 1000})) a (canonical-name team-a)]
    (assoc (reduce (fn [r m] (let [a-home? (= a (:home-key m)) ag (if a-home? (:home-goals m) (:away-goals m)) bg (if a-home? (:away-goals m) (:home-goals m))]
      (update r (cond (> ag bg) :team-a-wins (= ag bg) :draws :else :team-b-wins) inc)))
      {:team-a team-a :team-b team-b :matches (count games) :team-a-wins 0 :team-b-wins 0 :draws 0} games)
      :matches-list games)))

(defn standings [matches {:keys [season competition]}]
  (let [games (search-matches matches {:season season :competition (or competition "Brasileirão") :limit 1000})]
    (let [table (reduce
                 (fn [table m]
                   (-> table
                       (update (:home-team m)
                               #(merge-with + (or % {:team (:home-team m) :matches 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0})
                                            (record-for [m] (:home-team m) {:venue "home"})))
                       (update (:away-team m)
                               #(merge-with + (or % {:team (:away-team m) :matches 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0})
                                            (record-for [m] (:away-team m) {:venue "away"})))))
                 {} games)]
      (->> table vals
           (map #(assoc % :points (+ (* 3 (:wins %)) (:draws %))
                         :goal-difference (- (:goals-for %) (:goals-against %))))
           (sort-by (juxt :points :goal-difference :goals-for) #(compare %2 %1))
           vec))))

(defn competition-statistics [matches {:keys [competition season]}]
  (let [games (search-matches matches {:competition competition :season season :limit 1000}) n (count games)
        total (reduce + 0 (map #(+ (or (:home-goals %) 0) (or (:away-goals %) 0)) games))]
    {:matches n :total-goals total :average-goals-per-match (if (pos? n) (/ (double total) n) 0.0)
     :home-wins (count (filter #(> (or (:home-goals %) -1) (or (:away-goals %) -1)) games))
     :draws (count (filter #(= (:home-goals %) (:away-goals %)) games))
     :away-wins (count (filter #(< (or (:home-goals %) -1) (or (:away-goals %) -1)) games))}))
(defn search-players [players {:keys [name nationality club position min-overall limit] :or {limit 100}}]
  (->> players (filter #(and (or (nil? name) (contains-name? (:name %) name)) (or (nil? nationality) (contains-name? (:nationality %) nationality))
    (or (nil? club) (contains-name? (:club %) club)) (or (nil? position) (contains-name? (:position %) position))
    (or (nil? min-overall) (>= (or (:overall %) 0) (parse-int min-overall)))))
    (sort-by :overall #(compare %2 %1)) (take (min 1000 (max 1 (or (parse-int limit) 100)))) vec))

(def any-object-schema {:type "object" :additionalProperties true})
(def tool-definitions [{:name "search_matches" :description "Find matches by team, opponent, competition, season, date range, or round." :inputSchema any-object-schema}
 {:name "team_statistics" :description "Calculate a team's wins, draws, losses and goals." :inputSchema any-object-schema}
 {:name "head_to_head" :description "Compare two teams' results in the dataset." :inputSchema any-object-schema}
 {:name "standings" :description "Calculate standings for a competition and season." :inputSchema any-object-schema}
 {:name "search_players" :description "Search FIFA players by name, nationality, club, position, and rating." :inputSchema any-object-schema}
 {:name "competition_statistics" :description "Calculate goals and result averages for a competition." :inputSchema any-object-schema}])

;; The small JSON codec keeps the server self-contained; MCP requests are JSON-RPC.
(declare parse-json)
(defn json-value [s i] (let [i (loop [j i] (if (and (< j (count s)) (Character/isWhitespace (.charAt s j))) (recur (inc j)) j))
                             c (.charAt s i)]
  (cond (= c \{) (loop [j (inc i) m {}] (let [j (loop [x j] (if (and (< x (count s)) (Character/isWhitespace (.charAt s x))) (recur (inc x)) x))]
    (if (= (.charAt s j) \}) [m (inc j)] (let [[k j] (json-value s j) [v j] (json-value s (inc j)) j (if (and (< j (count s)) (= (.charAt s j) \,)) (inc j) j)] (recur j (assoc m (keyword k) v))))))
        (= c \[) (loop [j (inc i) xs []] (if (= (.charAt s j) \]) [xs (inc j)] (let [[v j] (json-value s j) j (if (= (.charAt s j) \,) (inc j) j)] (recur j (conj xs v)))))
        (= c \") (let [end (.indexOf s "\"" (inc i))] [(subs s (inc i) end) (inc end)])
        :else (let [end (or (some #(when (#{\, \} \] \space \newline \return \tab} (.charAt s %)) %) (range i (count s))) (count s)) token (subs s i end)] [(cond (= token "null") nil (= token "true") true (= token "false") false :else (or (parse-int token) token)) end]))))
(defn parse-json [s] (first (json-value (str/trim s) 0)))
(defn json [x] (cond (nil? x) "null" (string? x) (str "\"" (str/escape x {\\ "\\\\" \" "\\\"" \newline "\\n"}) "\"") (keyword? x) (json (name x)) (number? x) (str x) (boolean? x) (str x) (map? x) (str "{" (str/join "," (map (fn [[k v]] (str (json (name k)) ":" (json v))) x)) "}") (sequential? x) (str "[" (str/join "," (map json x)) "]") :else (json (str x))))
(defn call-tool [data name args] (case name "search_matches" (search-matches (:matches data) args) "team_statistics" (team-statistics (:matches data) (:team args) args) "head_to_head" (head-to-head (:matches data) (:team-a args) (:team-b args) args) "standings" (standings (:matches data) args) "search_players" (search-players (:players data) args) "competition_statistics" (competition-statistics (:matches data) args) (throw (ex-info "Unknown tool" {:tool name}))))
(defn response [id result] {:jsonrpc "2.0" :id id :result result})
(defn handle-request [data request] (try (case (:method request)
  "initialize" (response (:id request) {:protocolVersion "2024-11-05" :capabilities {:tools {}} :serverInfo {:name "brazilian-soccer-mcp" :version "1.0.0"}})
  "tools/list" (response (:id request) {:tools tool-definitions})
  "tools/call" (let [value (call-tool data (get-in request [:params :name]) (or (get-in request [:params :arguments]) {}))] (response (:id request) {:content [{:type "text" :text (pr-str value)}] :structuredContent value}))
  nil) (catch Exception e (response (:id request) {:content [{:type "text" :text (.getMessage e)}] :isError true}))))
(defn -main [& _] (let [data (load-data)] (doseq [line (line-seq (io/reader System/in)) :when (not (str/blank? line))] (when-let [result (handle-request data (parse-json line))] (println (json result)) (flush)))))
