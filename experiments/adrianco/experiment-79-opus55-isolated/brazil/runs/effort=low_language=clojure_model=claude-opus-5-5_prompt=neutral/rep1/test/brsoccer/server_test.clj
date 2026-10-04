(ns brsoccer.server-test
  "The MCP protocol surface: JSON-RPC handling and every tool end to end."
  (:require [brsoccer.data :as data]
            [brsoccer.server :as server]
            [clojure.data.json :as json]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]])
  (:import (java.io ByteArrayInputStream ByteArrayOutputStream)))

(defn- rpc
  "Sends one JSON-RPC message through the line handler."
  [msg]
  (some-> (server/handle-line data/db (json/write-str msg))
          (json/read-str :key-fn keyword)))

(defn- call
  "Calls a tool and returns [text error?]."
  [tool args]
  (let [r (:result (rpc {:jsonrpc "2.0" :id 1 :method "tools/call"
                         :params {:name tool :arguments args}}))]
    [(get-in r [:content 0 :text]) (:isError r)]))

(defn- answer [tool args]
  (let [[text error?] (call tool args)]
    (is (false? error?) text)
    text))

(deftest protocol-handshake
  (testing "initialize negotiates a version and advertises tools"
    (let [r (rpc {:jsonrpc "2.0" :id 1 :method "initialize"
                  :params {:protocolVersion "2024-11-05" :capabilities {}
                           :clientInfo {:name "test" :version "0"}}})]
      (is (= 1 (:id r)))
      (is (= "2024-11-05" (get-in r [:result :protocolVersion])))
      (is (contains? (get-in r [:result :capabilities]) :tools))
      (is (= "brazilian-soccer-mcp" (get-in r [:result :serverInfo :name])))))
  (testing "an unsupported client version falls back to the server's"
    (is (= server/default-protocol
           (get-in (rpc {:jsonrpc "2.0" :id 1 :method "initialize"
                         :params {:protocolVersion "1999-01-01"}})
                   [:result :protocolVersion]))))
  (testing "notifications get no response"
    (is (nil? (rpc {:jsonrpc "2.0" :method "notifications/initialized"}))))
  (testing "ping"
    (is (= {:jsonrpc "2.0" :id "p" :result {}} (rpc {:jsonrpc "2.0" :id "p" :method "ping"})))))

(deftest tool-listing
  (let [tools (get-in (rpc {:jsonrpc "2.0" :id 2 :method "tools/list"}) [:result :tools])]
    (is (= (count server/tools) (count tools)))
    (is (every? #(and (string? (:name %)) (string? (:description %))
                      (= "object" (get-in % [:inputSchema :type])))
                tools))
    (is (not-any? :handler tools))
    (testing "required arguments are declared properties"
      (doseq [t tools, r (get-in t [:inputSchema :required])]
        (is (contains? (get-in t [:inputSchema :properties]) (keyword r)) (:name t))))))

(deftest protocol-errors
  (is (= -32700 (get-in (json/read-str (server/handle-line data/db "{not json") :key-fn keyword)
                        [:error :code])))
  (is (= -32600 (get-in (rpc [1 2 3]) [:error :code])))
  (is (= -32600 (get-in (rpc {:jsonrpc "2.0" :id 1}) [:error :code])))
  (is (= -32601 (get-in (rpc {:jsonrpc "2.0" :id 1 :method "resources/list"}) [:error :code])))
  (is (= -32602 (get-in (rpc {:jsonrpc "2.0" :id 1 :method "tools/call"
                              :params {:name "no_such_tool" :arguments {}}})
                        [:error :code])))
  (is (= -32602 (get-in (rpc {:jsonrpc "2.0" :id 1 :method "tools/call"
                              :params {:name "standings" :arguments [2019]}})
                        [:error :code]))))

(deftest bad-tool-arguments-are-reported-in-band
  (doseq [[tool args fragment]
          [["team_stats" {} "Missing required argument: team"]
           ["head_to_head" {:team_a "Flamengo"} "Missing required argument: team_b"]
           ["standings" {} "Missing required argument: season"]
           ["standings" {:season "twenty"} "season must be an integer"]
           ["team_stats" {:team "Nowhere United XYZ"} "No team matching"]
           ["search_matches" {:competition "Premier League"} "Unknown competition"]
           ["search_matches" {:date_from "yesterday"} "date_from must be a date"]
           ["search_matches" {:limit 0} "limit must be at least 1"]
           ["rank_teams" {:metric "vibes"} "metric must be one of"]]]
    (let [[text error?] (call tool args)]
      (is (true? error?) (str tool " " args))
      (is (str/includes? text fragment) text))))

(deftest sample-questions
  (testing "Show me all Flamengo vs Fluminense matches"
    (let [text (answer "head_to_head" {:team_a "Flamengo" :team_b "Fluminense" :limit 2})]
      (is (str/starts-with? text "Flamengo vs Fluminense (Fla-Flu):"))
      (is (re-find #"- \d{4}-\d{2}-\d{2}: \S.* \d+-\d+ \S.* \(.+\)" text))
      (is (re-find #"\(\d+ more matches in dataset\)" text))
      (is (re-find #"Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws" text))))
  (testing "What matches did Palmeiras play in 2023?"
    (is (re-find #"^\d+ matches found" (answer "search_matches" {:team "Palmeiras" :season 2023}))))
  (testing "Find all Copa do Brasil finals"
    (is (str/includes? (answer "search_matches" {:competition "Copa do Brasil" :stage "final" :limit 50})
                       "2019-09-18: Internacional 1-2 Athletico-PR (Copa do Brasil 2019, final)")))
  (testing "When did Flamengo last play Corinthians?"
    (is (re-find #"- \d{4}-\d{2}-\d{2}: "
                 (answer "search_matches" {:team "Flamengo" :opponent "Corinthians" :limit 1}))))
  (testing "What is Corinthians' home record in 2022?"
    (let [text (answer "team_stats" {:team "Corinthians" :season 2022 :venue "home"
                                     :competition "Brasileirão"})]
      (is (str/includes? text "Corinthians record (2022, Brasileirão Série A, home):"))
      (is (str/includes? text "- Matches: 19"))
      (is (re-find #"Win rate: \d+\.\d%" text))))
  (testing "Which team scored the most goals in Serie A 2019?"
    (is (str/includes? (answer "rank_teams" {:metric "goals_for" :competition "Serie A" :season 2019})
                       "1. Flamengo - 86 goals scored")))
  (testing "Compare Palmeiras and Santos head-to-head"
    (is (str/includes? (answer "head_to_head" {:team_a "Palmeiras" :team_b "Santos"})
                       "Head-to-head in dataset")))
  (testing "Who won the 2019 Brasileirão? (season given as a string)"
    (let [text (answer "standings" {:season "2019"})]
      (is (str/includes? text "1. Flamengo - 90 pts (28W, 6D, 4L)"))
      (is (str/includes? text "- Champion"))
      (is (str/includes? text "Avaí - 20 pts") "accents survive JSON encoding")
      (is (str/includes? text "- Relegated"))))
  (testing "Show the 2018 Copa Libertadores knockout matches"
    (is (str/includes? (answer "search_matches" {:competition "Libertadores" :season 2018 :stage "final"})
                       "Copa Libertadores 2018, final")))
  (testing "What's the average goals per match in the Brasileirão?"
    (let [text (answer "competition_stats" {:competition "Brasileirão"})]
      (is (re-find #"Average goals per match: \d\.\d\d" text))
      (is (re-find #"Home win rate: \d+\.\d%" text))))
  (testing "Which team has the best away record?"
    (is (str/includes? (answer "rank_teams" {:venue "away" :metric "win_rate"})
                       "Teams ranked by win_rate (away):")))
  (testing "Show me the biggest wins in the dataset"
    (is (str/starts-with? (answer "biggest_wins" {:limit 3}) "Biggest victories")))
  (testing "Show me all derbies in 2023"
    (is (str/includes? (answer "derbies" {:season 2023}) "[Fla-Flu]")))
  (testing "What competitions has Palmeiras played in?"
    (let [text (answer "team_competitions" {:team "Palmeiras"})]
      (is (str/includes? text "Copa Libertadores"))
      (is (str/includes? text "Copa do Brasil"))))
  (testing "Find all Brazilian players in the dataset"
    (let [text (answer "search_players" {:nationality "Brazil" :limit 3})]
      (is (str/includes? text "827 players found"))
      (is (str/includes? text "1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain"))))
  (testing "Who are the highest-rated players at Grêmio?"
    (is (str/includes? (answer "search_players" {:club "Gremio" :limit 5}) "Club: Grêmio")))
  (testing "Show me all forwards from Santos"
    (is (re-find #"Position: (ST|LS|RS|CF|LF|RF|LW|RW)"
                 (answer "search_players" {:club "Santos" :position "forward"}))))
  (testing "Who is Neymar?"
    (let [text (answer "player_details" {:name "Neymar"})]
      (is (str/includes? text "Neymar Jr"))
      (is (str/includes? text "Overall: 92, Potential: 93"))))
  (testing "Brazilian players at Brazilian clubs"
    (is (re-find #"- Grêmio: \d+ players \(avg rating: \d+"
                 (answer "brazilian_club_squads" {:nationality "Brazil"}))))
  (testing "Club profile across match and player files"
    (let [text (answer "team_profile" {:team "Santos"})]
      (is (str/includes? text "Most recent matches:"))
      (is (str/includes? text "FIFA squad ("))))
  (testing "A club missing from the FIFA file says so"
    (is (str/includes? (answer "team_profile" {:team "Flamengo"})
                       "not in the FIFA player dataset")))
  (testing "What data is available?"
    (let [text (answer "list_competitions" {})]
      (is (str/includes? text "fifa_data.csv: 18207"))
      (is (str/includes? text "Copa Libertadores"))))
  (testing "Queries with no result answer plainly instead of failing"
    (is (str/includes? (answer "search_matches" {:team "Flamengo" :season 1950}) "No matches found"))
    (is (str/includes? (answer "search_players" {:name "zzzqqq"}) "No players found"))
    (is (str/includes? (answer "standings" {:season 1999}) "No Brasileirão Série A matches"))))

(deftest stdio-transport
  (testing "newline-delimited messages in, one response line per request out"
    (let [input (str (json/write-str {:jsonrpc "2.0" :id 1 :method "initialize" :params {}}) "\n"
                     (json/write-str {:jsonrpc "2.0" :method "notifications/initialized"}) "\n"
                     "\n"
                     (json/write-str {:jsonrpc "2.0" :id 2 :method "tools/call"
                                      :params {:name "standings" :arguments {:season 2019}}})
                     "\n")
          out (ByteArrayOutputStream.)]
      (server/serve data/db (ByteArrayInputStream. (.getBytes input "UTF-8")) out)
      (let [lines (str/split-lines (.toString out "UTF-8"))
            [init table] (map #(json/read-str % :key-fn keyword) lines)]
        (is (= 2 (count lines)))
        (is (= 1 (:id init)))
        (is (= 2 (:id table)))
        (is (str/includes? (get-in table [:result :content 0 :text]) "Grêmio"))))))
