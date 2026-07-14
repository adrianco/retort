(ns soccer.test-helpers
  "Test support for the Brazilian Soccer MCP acceptance suite.

   Each acceptance scenario must start from a *running but empty system* that
   shares no data with any other scenario.  These helpers give every test its
   own private, on-disk dataset (a temp directory of CSV files in the exact
   formats the real datasets use) and a thin JSON-RPC client that talks to the
   server only through its public MCP protocol surface (`process-line`).

   No test reaches into server internals: it sends a JSON-RPC line in and reads
   a JSON-RPC line out, exactly as an external MCP client would."
  (:require [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [soccer.server :as server]))

;; ---------------------------------------------------------------------------
;; Isolated, on-disk fixture datasets
;; ---------------------------------------------------------------------------

(defn temp-dir
  "Create a fresh empty temp directory and return its absolute path."
  []
  (let [f (java.io.File/createTempFile "soccer-fixture" "")]
    (.delete f)
    (.mkdirs f)
    (.getAbsolutePath f)))

(defn spit-csv!
  "Write `rows` (a seq of seqs) as a CSV file `filename` inside `dir`."
  [dir filename header rows]
  (let [quote (fn [v]
                (let [s (str v)]
                  (if (re-find #"[\",\n]" s)
                    (str \" (str/replace s "\"" "\"\"") \")
                    s)))
        line  (fn [cells] (str/join "," (map quote cells)))
        text  (str/join "\n" (cons (line header) (map line rows)))]
    (spit (io/file dir filename) (str text "\n"))
    dir))

;; The 12-match Brasileirão 2019 fixture used by most scenarios.  Team names
;; carry state suffixes (e.g. "Flamengo-RJ") so tests also exercise name
;; normalization.  All expected numbers in the acceptance tests are derived by
;; hand from exactly these rows.
(def brasileirao-2019-rows
  [["2019-04-28 16:00:00" "Flamengo-RJ"    "RJ" "Corinthians-SP" "SP" 3 1 2019 1]
   ["2019-05-12 16:00:00" "Fluminense-RJ"  "RJ" "Flamengo-RJ"    "RJ" 1 2 2019 2]
   ["2019-06-02 16:00:00" "Flamengo-RJ"    "RJ" "Santos-SP"      "SP" 2 0 2019 3]
   ["2019-08-10 16:00:00" "Palmeiras-SP"   "SP" "Flamengo-RJ"    "RJ" 0 0 2019 4]
   ["2019-07-01 16:00:00" "Fluminense-RJ"  "RJ" "Santos-SP"      "SP" 2 1 2019 5]
   ["2019-09-03 16:00:00" "Flamengo-RJ"    "RJ" "Fluminense-RJ"  "RJ" 2 1 2019 6]
   ["2019-05-19 16:00:00" "Corinthians-SP" "SP" "Palmeiras-SP"   "SP" 2 1 2019 7]
   ["2019-06-16 16:00:00" "Corinthians-SP" "SP" "Santos-SP"      "SP" 0 0 2019 8]
   ["2019-07-21 16:00:00" "Corinthians-SP" "SP" "Fluminense-RJ"  "RJ" 1 0 2019 9]
   ["2019-08-25 16:00:00" "Santos-SP"      "SP" "Corinthians-SP" "SP" 3 2 2019 10]
   ["2019-09-15 16:00:00" "Palmeiras-SP"   "SP" "Santos-SP"      "SP" 3 0 2019 11]
   ["2019-10-06 16:00:00" "Santos-SP"      "SP" "Palmeiras-SP"   "SP" 1 1 2019 12]])

(def fifa-rows
  [[100 "Gabriel Barbosa" 22 "Brazil"    82 86 "Flamengo"            "ST" 9]
   [101 "Bruno Henrique"  28 "Brazil"    79 79 "Flamengo"            "LW" 27]
   [102 "Gerson"          21 "Brazil"    78 85 "Flamengo"            "CM" 8]
   [103 "Dudu"            27 "Brazil"    80 80 "Palmeiras"           "LW" 7]
   [104 "L. Messi"        31 "Argentina" 94 94 "FC Barcelona"        "RF" 10]
   [105 "Neymar Jr"       27 "Brazil"    92 92 "Paris Saint-Germain" "LW" 10]])

(defn make-fixture-dir!
  "Build a complete isolated dataset (matches + players) and return its dir."
  []
  (let [dir (temp-dir)]
    (spit-csv! dir "Brasileirao_Matches.csv"
               ["datetime" "home_team" "home_team_state" "away_team"
                "away_team_state" "home_goal" "away_goal" "season" "round"]
               brasileirao-2019-rows)
    ;; A Copa do Brasil match so competition filtering has something to exclude.
    (spit-csv! dir "Brazilian_Cup_Matches.csv"
               ["round" "datetime" "home_team" "away_team"
                "home_goal" "away_goal" "season"]
               [["final" "2019-09-18 21:30:00" "Internacional - RS"
                 "Athletico Paranaense - PR" 1 0 2019]])
    (spit-csv! dir "fifa_data.csv"
               ["ID" "Name" "Age" "Nationality" "Overall" "Potential"
                "Club" "Position" "Jersey Number"]
               fifa-rows)
    dir))

;; ---------------------------------------------------------------------------
;; JSON-RPC client over the public MCP protocol surface
;; ---------------------------------------------------------------------------

(defn new-server
  "Start a running MCP server backed by the dataset in `data-dir`."
  [data-dir]
  (server/create-server data-dir))

(defn rpc
  "Send one JSON-RPC request to the server and return the parsed response map."
  [srv method params]
  (let [req  (json/write-str {:jsonrpc "2.0" :id 1 :method method :params params})
        resp (server/process-line srv req)]
    (json/read-str resp :key-fn keyword)))

(defn list-tools
  "Return the seq of tool names advertised by the server."
  [srv]
  (->> (rpc srv "tools/list" {}) :result :tools (map :name) set))

(defn call-tool
  "Invoke an MCP tool and return its textual content (the domain answer)."
  [srv tool-name arguments]
  (let [resp (rpc srv "tools/call" {:name tool-name :arguments arguments})]
    (or (some-> resp :result :content first :text)
        (some-> resp :error :message)
        "")))

(defn call-tool-raw
  "Invoke an MCP tool and return the full parsed JSON-RPC response."
  [srv tool-name arguments]
  (rpc srv "tools/call" {:name tool-name :arguments arguments}))
