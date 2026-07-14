(ns brazilian-soccer.mcp-test
  (:require [clojure.test :refer [deftest testing is use-fixtures]]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.mcp :as mcp]))

(def ^:dynamic *db* nil)

(use-fixtures :once
  (fn [f]
    (binding [*db* (data/load-db "test/resources/kaggle")]
      (f))))

(defn- call-tool [name args]
  (mcp/handle-request *db* {:jsonrpc "2.0" :id 1 :method "tools/call"
                            :params {:name name :arguments args}}))

(defn- text [resp]
  (-> resp :result :content first :text))

(deftest initialize-test
  (testing "initialize echoes protocol version and advertises tools capability"
    (let [resp (mcp/handle-request *db* {:jsonrpc "2.0" :id 0 :method "initialize"
                                         :params {}})]
      (is (= "2.0" (:jsonrpc resp)))
      (is (= 0 (:id resp)))
      (is (get-in resp [:result :capabilities :tools]))
      (is (get-in resp [:result :serverInfo :name])))))

(deftest tools-list-test
  (testing "lists all tools, each with a name and input schema"
    (let [tools (get-in (mcp/handle-request *db* {:jsonrpc "2.0" :id 1
                                                  :method "tools/list" :params {}})
                        [:result :tools])
          names (set (map :name tools))]
      (is (contains? names "find_matches"))
      (is (contains? names "head_to_head"))
      (is (contains? names "team_record"))
      (is (contains? names "standings"))
      (is (contains? names "search_players"))
      (is (contains? names "statistics"))
      (is (every? #(get-in % [:inputSchema :type]) tools)))))

(deftest notification-returns-nil-test
  (testing "notifications (no id) produce no response"
    (is (nil? (mcp/handle-request *db* {:jsonrpc "2.0"
                                        :method "notifications/initialized"})))))

(deftest unknown-method-test
  (testing "unknown methods return a JSON-RPC error"
    (let [resp (mcp/handle-request *db* {:jsonrpc "2.0" :id 9 :method "bogus"})]
      (is (= -32601 (get-in resp [:error :code]))))))

(deftest tool-find-matches-test
  (testing "find_matches returns formatted match text"
    (let [t (text (call-tool "find_matches" {"team" "Flamengo"
                                             "competition" "Brasileirão"
                                             "season" 2019}))]
      (is (re-find #"3 matches found" t))
      (is (re-find #"Flamengo 5-0 Grêmio" t)))))

(deftest tool-head-to-head-test
  (testing "head_to_head returns the tally"
    (let [t (text (call-tool "head_to_head" {"team_a" "Flamengo" "team_b" "Santos"}))]
      (is (re-find #"head-to-head" t))
      (is (re-find #"Flamengo: 1 win" t)))))

(deftest tool-team-record-test
  (testing "team_record returns the record block"
    (let [t (text (call-tool "team_record" {"team" "Flamengo"
                                            "competition" "Brasileirão"
                                            "season" 2019}))]
      (is (re-find #"Wins: 2" t))
      (is (re-find #"Points: 7" t)))))

(deftest tool-standings-test
  (testing "standings returns the table"
    (let [t (text (call-tool "standings" {"competition" "Brasileirão" "season" 2019}))]
      (is (re-find #"1\. Flamengo - 7 pts" t)))))

(deftest tool-search-players-test
  (testing "search_players returns the player list"
    (let [t (text (call-tool "search_players" {"nationality" "Brazil"}))]
      (is (re-find #"Neymar Jr - Overall: 92" t)))))

(deftest tool-statistics-test
  (testing "statistics returns aggregates"
    (let [t (text (call-tool "statistics" {"competition" "Brasileirão" "season" 2019}))]
      (is (re-find #"Average goals per match" t))
      (is (re-find #"Home win rate" t)))))

(deftest tool-unknown-test
  (testing "calling an unknown tool reports an error in the result"
    (let [resp (call-tool "nope" {})]
      (is (true? (get-in resp [:result :isError]))))))

(deftest serve-stdio-roundtrip-test
  (testing "serve reads newline-delimited JSON-RPC and writes one response each"
    (let [requests (str "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}\n"
                        ;; a notification — must produce no response line
                        "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}\n"
                        "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\","
                        "\"params\":{\"name\":\"head_to_head\","
                        "\"arguments\":{\"team_a\":\"Flamengo\",\"team_b\":\"Santos\"}}}\n")
          in (java.io.ByteArrayInputStream. (.getBytes requests "UTF-8"))
          out (java.io.ByteArrayOutputStream.)]
      (mcp/serve *db* in out)
      (let [lines (->> (clojure.string/split-lines (str out))
                       (remove clojure.string/blank?)
                       (map #(clojure.data.json/read-str % :key-fn keyword)))]
        ;; two responses (the notification is silent)
        (is (= 2 (count lines)))
        (is (= [1 2] (map :id lines)))
        (is (re-find #"head-to-head"
                     (-> (second lines) :result :content first :text)))))))
