(ns brazilian-soccer-mcp.mcp-test
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [brazilian-soccer-mcp.data :as data]
            [brazilian-soccer-mcp.mcp :as mcp]
            [brazilian-soccer-mcp.tools :as tools])
  (:import (java.io StringReader StringWriter)))

(def ^:private db (delay (data/load-dataset "data/kaggle")))

(defn- rpc
  "Sends newline-delimited requests through the server and returns the parsed responses."
  [& lines]
  (let [out (StringWriter.)]
    (mcp/serve @db (StringReader. (str/join "\n" lines)) out)
    (->> (str/split-lines (str out))
         (remove str/blank?)
         (map #(json/read-str % :key-fn keyword)))))

(defn- request [id method params]
  (json/write-str (cond-> {:jsonrpc "2.0" :id id :method method}
                    params (assoc :params params))))

(deftest initialize-advertises-tools
  (let [[resp] (rpc (request 1 "initialize" {:protocolVersion "2024-11-05"}))]
    (is (= 1 (:id resp)))
    (is (= "2024-11-05" (get-in resp [:result :protocolVersion])))
    (is (contains? (get-in resp [:result :capabilities]) :tools))))

(deftest notifications-get-no-reply
  (is (empty? (rpc (json/write-str {:jsonrpc "2.0" :method "notifications/initialized"})))))

(deftest tools-list-names-every-tool
  (let [[resp] (rpc (request 2 "tools/list" {}))
        names (set (map :name (get-in resp [:result :tools])))]
    (is (= #{"search_matches" "team_record" "head_to_head" "standings" "match_stats" "search_players"}
           names))))

(deftest tools-call-returns-text-content
  (let [[resp] (rpc (request 3 "tools/call" {:name "team_record"
                                             :arguments {:team "Corinthians" :season 2022 :venue "home"}}))
        result (:result resp)]
    (is (false? (:isError result)))
    (is (str/starts-with? (get-in result [:content 0 :text]) "Corinthians (2022, home):"))))

(deftest tool-errors-are-reported-not-thrown
  (testing "missing required argument"
    (let [[resp] (rpc (request 4 "tools/call" {:name "head_to_head" :arguments {:team_a "Flamengo"}}))]
      (is (true? (get-in resp [:result :isError])))
      (is (= "Missing required argument: team_b" (get-in resp [:result :content 0 :text])))))
  (testing "bad competition name"
    (let [[resp] (rpc (request 5 "tools/call" {:name "standings" :arguments {:competition "Premier League" :season 2019}}))]
      (is (true? (get-in resp [:result :isError])))))
  (testing "unknown tool"
    (let [[resp] (rpc (request 6 "tools/call" {:name "nope" :arguments {}}))]
      (is (true? (get-in resp [:result :isError]))))))

(deftest unknown-method-and-bad-json-produce-errors
  (let [[bad unknown] (rpc "{not json" (request 7 "resources/list" {}))]
    (is (= -32700 (get-in bad [:error :code])))
    (is (= -32601 (get-in unknown [:error :code])))
    (is (= 7 (:id unknown)))))

(deftest standings-tool-renders-table
  (let [text (get-in (tools/call @db "standings" {:competition "brasileirao" :season 2019})
                     [:content 0 :text])]
    (is (str/includes? text "2019 Brasileirão standings"))
    (is (str/includes? text "1. Flamengo - 90 pts (28W, 6D, 4L)"))))

(deftest search-players-tool-renders-players
  (let [text (get-in (tools/call @db "search_players" {:name "L. Messi"}) [:content 0 :text])]
    (is (str/includes? text "1. L. Messi - Overall: 94"))))

(deftest head-to-head-tool-lists-recent-matches
  (let [text (get-in (tools/call @db "head_to_head" {:team_a "Palmeiras" :team_b "Santos" :limit 2})
                     [:content 0 :text])
        lines (str/split-lines text)]
    (is (str/starts-with? text "Palmeiras vs Santos head-to-head"))
    (is (re-matches #"- \d{4}-\d{2}-\d{2}: .+ \d+-\d+ .+ \(.+\)" (nth lines 4)))))

(deftest players-tool-reports-empty-club-honestly
  (is (= "No players found for those filters."
         (get-in (tools/call @db "search_players" {:club "Flamengo" :nationality "Brazil"})
                 [:content 0 :text]))))
