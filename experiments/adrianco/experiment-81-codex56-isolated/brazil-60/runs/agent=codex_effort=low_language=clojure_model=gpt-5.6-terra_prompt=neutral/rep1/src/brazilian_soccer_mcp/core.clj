(ns brazilian-soccer-mcp.core
  "A small, dependency-free MCP server for the CSV files supplied with this project."
  (:require [clojure.java.io :as io]
            [clojure.string :as str]))

(def data-directory "data/kaggle")

(defn- csv-row [line]
  (loop [chars (seq (or line "")), value "", row [], quoted? false]
    (if-let [c (first chars)]
      (cond
        (= c \") (if (and quoted? (= (second chars) \"))
                   (recur (nnext chars) (str value c) row quoted?)
                   (recur (next chars) value row (not quoted?)))
        (and (= c \,) (not quoted?)) (recur (next chars) "" (conj row value) false)
        :else (recur (next chars) (str value c) row quoted?))
      (conj row value))))

(defn- read-csv [file]
  (let [[header & rows] (with-open [r (io/reader file :encoding "UTF-8")]
                         (doall (line-seq r)))
        keys (mapv #(str/replace % "\uFEFF" "") (csv-row header))]
    (mapv #(zipmap keys (csv-row %)) rows)))

(defn normalize-name [name]
  ;; Most files append a state, while a few use a long club name.  Do not
  ;; blindly remove a state from Atletico: MG, PR and GO are different clubs.
  (let [n (-> (or name "") str/lower-case
              (java.text.Normalizer/normalize java.text.Normalizer$Form/NFD)
              (str/replace #"\p{M}" "")
              (str/replace #"[^a-z0-9]+" " ")
              (str/replace #"\s+" " ") str/trim)
        n (get {"athletico paranaense" "atletico pr"
                "atletico paranaense" "atletico pr"
                "atletico mineiro" "atletico mg"
                "atletico goianiense" "atletico go"
                "sport club corinthians paulista" "corinthians"} n n)]
    (cond
      (re-matches #"atletico (mg|pr|go)" n) n
      ;; Space-separated state forms occur in the extended data set.
      (re-find #" (ac|al|am|ap|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to)$" n)
      (str/replace n #" (ac|al|am|ap|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to)$" "")
      :else n)))

(defn- number-value [x]
  (try (when-not (str/blank? (str x)) (Double/parseDouble (str x)))
       (catch Exception _ nil)))
(defn- integer-value [x] (some-> (number-value x) int))

(defn- iso-date [date]
  (let [s (str/trim (or date ""))]
    (cond
      (re-matches #"\d{2}/\d{2}/\d{4}" s)
      (let [[d m y] (str/split s #"/")] (str y "-" m "-" d))
      (re-find #"^\d{4}-\d{2}-\d{2}" s) (subs s 0 10)
      :else s)))

(defn- extended-competition [tournament]
  (let [t (normalize-name tournament)]
    (cond (str/includes? t "libertadores") :libertadores
          (str/includes? t "copa do brasil") :copa-do-brasil
          (or (str/includes? t "brasile") (str/includes? t "serie a")) :brasileirao
          :else :extended)))

(defn- competition-key [competition]
  (when competition
    (let [c (normalize-name (name competition))]
      (cond (or (= c "brasileirao") (str/includes? c "brasile")) "brasileirao"
            (str/includes? c "copa do brasil") "copa-do-brasil"
            (str/includes? c "libertadores") "libertadores"
            (= c "extended") "extended"
            :else c))))

(defn- standard-match [competition row]
  (let [[home away hg ag date season round stage]
        (case competition
          :brasileirao [(row "home_team") (row "away_team") (row "home_goal") (row "away_goal") (row "datetime") (row "season") (row "round") nil]
          :copa-do-brasil [(row "home_team") (row "away_team") (row "home_goal") (row "away_goal") (row "datetime") (row "season") (row "round") nil]
          :libertadores [(row "home_team") (row "away_team") (row "home_goal") (row "away_goal") (row "datetime") (row "season") nil (row "stage")]
          :extended [(row "home") (row "away") (row "home_goal") (row "away_goal") (row "date") nil nil nil]
          :historical [(row "Equipe_mandante") (row "Equipe_visitante") (row "Gols_mandante") (row "Gols_visitante") (row "Data") (row "Ano") (row "Rodada") nil])]
    (let [source competition
          competition (cond (= competition :extended) (extended-competition (row "tournament"))
                            (= competition :historical) :brasileirao
                            :else competition)
          normalized-date (iso-date date)]
      {:competition (name competition) :source (name source)
       :date normalized-date :season (or (integer-value season)
                                         (some-> (re-find #"(?:19|20)\d{2}" normalized-date) integer-value))
     :round round :stage stage :home-team home :away-team away
     :home-key (normalize-name home) :away-key (normalize-name away)
     :home-goals (integer-value hg) :away-goals (integer-value ag)})))

(def match-files [[:brasileirao "Brasileirao_Matches.csv"] [:copa-do-brasil "Brazilian_Cup_Matches.csv"]
                  [:libertadores "Libertadores_Matches.csv"] [:extended "BR-Football-Dataset.csv"]
                  [:historical "novo_campeonato_brasileiro.csv"]])

(defn load-data
  ([] (load-data data-directory))
  ([directory]
   {:matches (vec (mapcat (fn [[competition file]]
                            (map #(standard-match competition %) (read-csv (io/file directory file)))) match-files))
    :players (read-csv (io/file directory "fifa_data.csv"))}))

(defonce database (delay (load-data)))
(defn data [] @database)

(def ^:private source-rank {"brasileirao" 0 "copa-do-brasil" 0 "libertadores" 0
                            "historical" 1 "extended" 2})
(defn- day-number [date]
  (try (.toEpochDay (java.time.LocalDate/parse date)) (catch Exception _ nil)))
(defn- duplicate? [a b]
  (and (= [(:competition a) (:home-key a) (:away-key a) (:home-goals a) (:away-goals a)]
          [(:competition b) (:home-key b) (:away-key b) (:home-goals b) (:away-goals b)])
       (let [da (day-number (:date a)) db (day-number (:date b))]
         (and da db (<= (Math/abs (long (- da db))) 1)))))
(defn- dedupe-matches [matches]
  ;; Sources record the same match under dates which can differ by a UTC day.
  ;; Keep the dedicated competition file when there is a collision.
  (->> matches
       (group-by #(select-keys % [:competition :home-key :away-key :home-goals :away-goals]))
       vals
       (mapcat (fn [same-fixture]
                 (reduce (fn [kept m]
                           (let [old (peek kept)]
                             (if (and old (duplicate? old m))
                               (if (< (get source-rank (:source m) 9)
                                      (get source-rank (:source old) 9))
                                 (conj (pop kept) m)
                                 kept)
                               (conj kept m)))) []
                         (sort-by (juxt :date #(get source-rank (:source %) 9)) same-fixture))))
       vec))

(defn find-matches
  "Returns matches matching optional :team, :home-team, :away-team, :opponent,
   :competition, :season, :from and :to. Date comparisons work for ISO dates."
  ([criteria] (find-matches (:matches (data)) criteria))
  ([matches {:keys [team home-team away-team opponent competition season from to]}]
   (let [team (normalize-name team) home (normalize-name home-team) away (normalize-name away-team)
         opponent (normalize-name opponent) comp (competition-key competition)]
     (->> matches
          (filter #(or (str/blank? team) (= team (:home-key %)) (= team (:away-key %))))
          (filter #(or (str/blank? home) (= home (:home-key %))))
          (filter #(or (str/blank? away) (= away (:away-key %))))
          (filter #(or (str/blank? opponent) (= opponent (:home-key %)) (= opponent (:away-key %))))
          (filter #(or (nil? comp) (= comp (:competition %))))
          (filter #(or (nil? season) (= (integer-value season) (:season %))))
          (filter #(or (nil? from) (not (neg? (compare (str (:date %)) (str from))))))
          (filter #(or (nil? to) (not (pos? (compare (str (:date %)) (str to))))))
          dedupe-matches
          (sort-by :date #(compare %2 %1)) vec))))

(defn team-statistics
  ([team criteria] (team-statistics (:matches (data)) team criteria))
  ([matches team criteria]
   (let [key (normalize-name team) games (find-matches matches (assoc criteria :team team))
         values (reduce (fn [s m]
                          (let [home? (= key (:home-key m)) gf (if home? (:home-goals m) (:away-goals m))
                                ga (if home? (:away-goals m) (:home-goals m))]
                            (if (and gf ga)
                              (-> s (update :played inc) (update :goals-for + gf) (update :goals-against + ga)
                                  (update (cond (> gf ga) :wins (= gf ga) :draws :else :losses) inc))
                              s)))
                        {:team team :played 0 :wins 0 :draws 0 :losses 0 :goals-for 0 :goals-against 0} games)
         pts (+ (* 3 (:wins values)) (:draws values))]
     (assoc values :points pts :win-rate (if (pos? (:played values)) (* 100.0 (/ (:wins values) (:played values))) 0.0)))))

(defn head-to-head [team-a team-b]
  (let [games (filter #(and (#{(normalize-name team-a) (normalize-name team-b)} (:home-key %))
                            (#{(normalize-name team-a) (normalize-name team-b)} (:away-key %))) (:matches (data)))
        a (normalize-name team-a)]
    (reduce (fn [r m] (let [a-home? (= a (:home-key m)) ag (if a-home? (:home-goals m) (:away-goals m)) bg (if a-home? (:away-goals m) (:home-goals m))]
                        (cond-> (update r :matches conj m) (and ag bg (> ag bg)) (update :team-a-wins inc)
                                (and ag bg (< ag bg)) (update :team-b-wins inc) (and ag bg (= ag bg)) (update :draws inc))))
            {:team-a team-a :team-b team-b :matches [] :team-a-wins 0 :team-b-wins 0 :draws 0} games)))

(defn aggregate-statistics
  "Computes dataset-derived match statistics. Criteria are the same as
   `find-matches`, so callers can ask for a league, season, or date period."
  ([] (aggregate-statistics {}))
  ([criteria]
   (let [games (filter #(and (some? (:home-goals %)) (some? (:away-goals %)))
                       (find-matches criteria))
         played (count games)
         home-wins (count (filter #(> (:home-goals %) (:away-goals %)) games))
         away-wins (count (filter #(< (:home-goals %) (:away-goals %)) games))
         draws (- played home-wins away-wins)
         total-goals (reduce + 0 (map #(+ (:home-goals %) (:away-goals %)) games))
         biggest (->> games
                      (sort-by (juxt #(Math/abs (long (- (:home-goals %) (:away-goals %))))
                                     #(+ (:home-goals %) (:away-goals %)))
                               #(compare %2 %1))
                      (take 10) vec)]
     {:matches played
      :total-goals total-goals
      :average-goals-per-match (if (pos? played) (/ (double total-goals) played) 0.0)
      :home-wins home-wins :away-wins away-wins :draws draws
      :home-win-rate (if (pos? played) (* 100.0 (/ home-wins played)) 0.0)
      :biggest-wins biggest})))

(defn search-players
  ([] (search-players {}))
  ([{:keys [name nationality club position limit] :or {limit 50}}]
   (let [contains-ci #(str/includes? (normalize-name %1) (normalize-name %2))]
     (->> (:players (data))
          (filter #(and (or (nil? name) (contains-ci (% "Name") name)) (or (nil? nationality) (contains-ci (% "Nationality") nationality))
                        (or (nil? club) (contains-ci (% "Club") club)) (or (nil? position) (= (normalize-name (% "Position")) (normalize-name position)))))
          (sort-by #(or (integer-value (% "Overall")) 0) >) (take limit)
          (map #(select-keys % ["ID" "Name" "Age" "Nationality" "Overall" "Potential" "Club" "Position" "Jersey Number"])) vec))))

(defn standings
  "Returns the complete Série A table.  Dedicated Série A rows are canonical;
   historical/extended rows are only used when that season is absent there."
  ([] (standings nil))
  ([season]
   (let [all (:matches (data))
         available (keep :season (filter #(= "brasileirao" (:competition %)) all))
         season (or (integer-value season) (apply max available))
         primary (filter #(and (= "brasileirao" (:competition %))
                               (= season (:season %))
                               (= "brasileirao" (:source %))) all)
         games (if (seq primary) (vec primary)
                   (find-matches all {:competition :brasileirao :season season}))
         ;; Use canonical keys, otherwise Flamengo-RJ and Flamengo become rows.
         teams (sort (set (map :home-key games)))]
     (->> teams
          (map #(team-statistics games % {}))
          (sort-by (juxt (comp - :points) (comp - :goals-for) :team))
          (map-indexed #(assoc %2 :position (inc %1) :season season)) vec))))

;; Minimal JSON codec, sufficient for JSON-RPC/MCP messages and intentionally dependency-free.
(declare parse-json)
(defn- json-string [s]
  (str (char 34)
       (str/escape (str s) {(char 92) (str (char 92) (char 92))
                             (char 34) (str (char 92) (char 34))
                             \newline (str (char 92) "n")
                             \return (str (char 92) "r")
                             \tab (str (char 92) "t")})
       (char 34)))
(defn to-json [x]
  (cond (nil? x) "null" (string? x) (json-string x) (keyword? x) (to-json (name x))
        (number? x) (str x) (true? x) "true" (false? x) "false"
        (map? x) (str "{" (str/join "," (map (fn [[k v]] (str (to-json (name k)) ":" (to-json v))) x)) "}")
        (sequential? x) (str "[" (str/join "," (map to-json x)) "]") :else (json-string x)))
(defn- json-read [s]
  (let [p (atom 0) n (count s)
        whitespace? #{(char 32) (char 10) (char 13) (char 9)}]
    (letfn [(skip! [] (while (and (< @p n) (whitespace? (.charAt s @p))) (swap! p inc)))
            (readv [] (skip!) (let [c (.charAt s @p)]
                                (cond (= c (char 123)) (obj) (= c (char 91)) (arr)
                                      (= c (char 34)) (strv) :else (atomv))))
            (strv []
              (swap! p inc)
              (loop [out ""]
                (let [c (.charAt s @p)]
                  (swap! p inc)
                  (cond (= c (char 34)) out
                        (= c (char 92)) (let [e (.charAt s @p)]
                                          (swap! p inc)
                                          (recur (str out (cond (= e \n) \newline (= e \r) \return (= e \t) \tab
                                                               (= e (char 34)) (char 34) (= e (char 92)) (char 92) :else e))))
                        :else (recur (str out c))))))
            (atomv []
              (let [start @p]
                (while (and (< @p n) (not (or (whitespace? (.charAt s @p)) (= (.charAt s @p) (char 44)) (= (.charAt s @p) (char 93)) (= (.charAt s @p) (char 125))))) (swap! p inc))
                (let [v (subs s start @p)] (case v "null" nil "true" true "false" false (try (Double/parseDouble v) (catch Exception _ v))))))
            (arr []
              (swap! p inc) (loop [xs []] (skip!)
                                   (if (= (.charAt s @p) (char 93)) (do (swap! p inc) xs)
                                       (let [x (readv)] (skip!) (when (= (.charAt s @p) (char 44)) (swap! p inc)) (recur (conj xs x))))))
            (obj []
              (swap! p inc) (loop [m {}] (skip!)
                                   (if (= (.charAt s @p) (char 125)) (do (swap! p inc) m)
                                       (let [k (strv)] (skip!) (swap! p inc) (let [v (readv)] (skip!) (when (= (.charAt s @p) (char 44)) (swap! p inc)) (recur (assoc m k v)))))))]
      (readv))))

(defn- content [value] [{:type "text" :text (pr-str value)}])
(defn handle-request [request]
  (let [id (get request "id") method (get request "method") args (get-in request ["params" "arguments"] {})
        result (case method
                 "initialize" {:protocolVersion "2024-11-05" :serverInfo {:name "brazilian-soccer-mcp" :version "1.0.0"} :capabilities {:tools {} :resources {}}}
                 "resources/list" {:resources [{:uri "brazilian-soccer://datasets" :name "Brazilian soccer datasets" :mimeType "application/json" :description "Counts and descriptions of loaded match and player data."}]}
                 "resources/read" (if (= "brazilian-soccer://datasets" (get-in request ["params" "uri"]))
                                    {:contents [{:uri "brazilian-soccer://datasets" :mimeType "application/json"
                                                 :text (to-json {:matches (count (:matches (data))) :players (count (:players (data))) :sources (mapv second match-files)})}]}
                                    {:error {:code -32602 :message "Unknown resource URI"}})
                 "tools/list" {:tools [{:name "find_matches" :description "Search matches by team, date, season, and competition." :inputSchema {:type "object" :properties {:team {:type "string"} :home-team {:type "string"} :away-team {:type "string"} :competition {:type "string"} :season {:type "integer"} :from {:type "string"} :to {:type "string"}}}}
                                        {:name "team_statistics" :description "Calculate a team's wins, draws, losses and goals." :inputSchema {:type "object" :properties {:team {:type "string"} :competition {:type "string"} :season {:type "integer"}} :required ["team"]}}
                                        {:name "head_to_head" :description "Compare two teams head to head." :inputSchema {:type "object" :properties {:team_a {:type "string"} :team_b {:type "string"}} :required ["team_a" "team_b"]}}
                                        {:name "search_players" :description "Search FIFA players by name, nationality, club, or position." :inputSchema {:type "object" :properties {:name {:type "string"} :nationality {:type "string"} :club {:type "string"} :position {:type "string"}}}}
                                        {:name "standings" :description "Calculate the complete Brasileirao table for a season." :inputSchema {:type "object" :properties {:season {:type "integer"}}}}
                                        {:name "aggregate_statistics" :description "Calculate goals, home/away outcomes, and biggest wins." :inputSchema {:type "object" :properties {:competition {:type "string"} :season {:type "integer"} :from {:type "string"} :to {:type "string"}}}}]}
                 "tools/call"
                 (let [tool (get-in request ["params" "name"])
                       keyword-args (into {} (map (fn [[k v]] [(keyword k) v]) args))
                       value (case tool
                               "find_matches" (find-matches keyword-args)
                               "team_statistics" (team-statistics (get args "team") (dissoc keyword-args :team))
                               "head_to_head" (head-to-head (get args "team_a") (get args "team_b"))
                               "search_players" (search-players keyword-args)
                               "standings" (standings (get args "season"))
                               "aggregate_statistics" (aggregate-statistics keyword-args)
                               {:error "Unknown tool"})]
                   {:content (content value)})
                 {:error {:code -32601 :message "Method not found"}})]
    (when id {:jsonrpc "2.0" :id id :result result})))

(defn -main [& _]
  (doseq [line (line-seq (io/reader System/in))]
    (when-let [response (handle-request (json-read line))]
      (println (to-json response)) (flush))))
