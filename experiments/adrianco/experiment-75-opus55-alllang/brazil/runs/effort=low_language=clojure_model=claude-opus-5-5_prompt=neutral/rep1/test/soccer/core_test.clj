(ns soccer.core-test
  "BDD-style scenarios (Given/When/Then) covering the specification."
  (:require [clojure.data.json :as json]
            [clojure.string :as str]
            [clojure.test :refer [deftest testing is]]
            [soccer.data :as d]
            [soccer.query :as q]
            [soccer.server :as s]))

(def db (d/db)) ; Given the match and player data is loaded

(defn tool [name args] (s/call-tool db name args))

(defmacro timed [ms & body]
  `(let [t# (System/nanoTime) r# (do ~@body)]
     (is (< (/ (- (System/nanoTime) t#) 1e6) ~ms) "query too slow")
     r#))

;; ------------------------------------------------------------ data loading

(deftest all-files-loadable
  (let [{:keys [brasileirao cup libertadores br-football historical]} (:sources db)]
    (is (= 4180 (count brasileirao)))
    (is (= 1337 (count cup)))
    (is (= 1255 (count libertadores)))
    (is (= 10296 (count br-football)))
    (is (= 6886 (count historical)))
    (is (= 18207 (count (:players db))))))

(deftest normalization
  (testing "team name variations map to the same key"
    (is (= "palmeiras" (d/team-key "Palmeiras-SP") (d/team-key "Palmeiras")
           (d/team-key "Sociedade Esportiva Palmeiras")))
    (is (= "sao paulo" (d/team-key "São Paulo") (d/team-key "Sao Paulo-SP")))
    (is (= "gremio" (d/team-key "Grêmio") (d/team-key "Gremio - RS")))
    (is (= "corinthians" (d/team-key "Sport Club Corinthians Paulista")))
    (is (= "atletico mineiro" (d/team-key "Atlético-MG") (d/team-key "Atletico Mineiro")))
    (is (not= (d/team-key "Atlético-MG") (d/team-key "Athletico-PR"))))
  (testing "date formats"
    (is (= "2003-03-29" (d/parse-date "29/03/2003")))
    (is (= "2012-05-19" (d/parse-date "2012-05-19 18:30:00")))
    (is (= "2023-09-24" (d/parse-date "2023-09-24"))))
  (testing "UTF-8 is preserved"
    (is (some #(= "Grêmio" (:home %)) (:matches db)))))

;; ------------------------------------------------------------ match queries

(deftest scenario-matches-between-two-teams
  (let [ms (timed 2000 (q/find-matches db {:team "Flamengo" :opponent "Fluminense"}))]
    (is (seq ms) "I should receive a list of matches")
    (is (every? #(and (:date %) (:home-goal %) (:away-goal %) (:competition %)) ms)
        "each match should have date, scores and competition")
    (is (every? #(= #{"flamengo" "fluminense"} #{(:home-key %) (:away-key %)}) ms))
    (is (= 1 (count (filter #(and (= "2023-11-11" (:date %))) ms))) "cross-file duplicates removed")))

(deftest scenario-team-season-matches
  (let [ms (q/find-matches db {:team "Palmeiras" :season 2023})]
    (is (seq ms))
    (is (every? #(= 2023 (:season %)) ms))
    (is (every? #(contains? #{(:home-key %) (:away-key %)} "palmeiras") ms))))

(deftest scenario-filters-by-competition-and-date
  (let [ms (q/find-matches db {:competition "Libertadores" :date-from "2018-01-01" :date-to "2018-12-31"})]
    (is (seq ms))
    (is (every? #(= "Copa Libertadores" (:competition %)) ms))
    (is (every? #(str/starts-with? (:date %) "2018") ms))))

(deftest scenario-last-meeting
  (let [m (first (q/find-matches db {:team "Flamengo" :opponent "Corinthians"}))]
    (is (some? m))
    (is (integer? (:home-goal m)))
    (is (re-find #"\d+-\d+" (q/format-match m)))))

(deftest scenario-cup-finals
  (let [fs (q/cup-finals db "Copa do Brasil")]
    (is (seq fs))
    (is (some #(and (= 2015 (:season %)) (= #{"palmeiras" "santos"} #{(:home-key %) (:away-key %)})) fs)))
  (is (seq (q/cup-finals db "Libertadores"))))

;; ------------------------------------------------------------ team queries

(deftest scenario-team-statistics
  (let [r (q/team-stats db {:team "Palmeiras" :season 2023})]
    (is (every? #(contains? r %) [:wins :losses :draws :goals-for :goals-against]))
    (is (= (:matches r) (+ (:wins r) (:draws r) (:losses r))))
    (is (pos? (:matches r)))))

(deftest scenario-home-record
  (let [r (q/team-stats db {:team "Corinthians" :season 2022 :competition "Brasileirão" :venue "home"})]
    (is (<= 17 (:matches r) 19))
    (is (str/includes? (tool "team_stats" {"team" "Corinthians" "season" 2022 "venue" "home"})
                       "Win rate:"))))

(deftest scenario-head-to-head
  (let [h (timed 2000 (q/head-to-head db "Palmeiras" "Santos"))]
    (is (= (count (filter :result (:matches h))) (+ (:a-wins h) (:b-wins h) (:draws h))))
    (is (str/includes? (q/format-h2h h) "Head-to-head in dataset: Palmeiras"))))

(deftest scenario-competitions-played
  (let [cs (set (map :competition (q/team-competitions db "Palmeiras")))]
    (is (every? cs ["Brasileirão" "Copa do Brasil" "Copa Libertadores"]))))

;; ------------------------------------------------------------ competition queries

(deftest scenario-champion-2019
  (let [c (timed 5000 (q/champion db 2019))]
    (is (= "flamengo" (:key c)))
    (is (= 90 (:points c)))
    (is (= [28 6 4] ((juxt :wins :draws :losses) c)))))

(deftest scenario-historical-champion
  (is (= "cruzeiro" (:key (q/champion db 2003))) "2003 comes from the historical file")
  (is (= "palmeiras" (:key (q/champion db 2022)))))

(deftest scenario-relegated
  (is (= 4 (count (q/relegated db 2020))))
  (is (= 20 (count (q/standings db 2020)))))

(deftest scenario-most-goals
  (let [top (first (q/top-scoring-teams db 2023))]
    (is (some? top))
    (is (str/includes? (tool "top_scoring_teams" {"season" 2023}) (:team top)))))

;; ------------------------------------------------------------ statistics

(deftest scenario-average-goals
  (let [s (timed 5000 (q/summary-stats (q/find-matches db {:competition "Brasileirão"})))]
    (is (< 2.0 (:avg-goals s) 3.0))
    (is (< 40 (:home-win-rate s) 60))))

(deftest scenario-biggest-wins
  (let [[a b] (q/biggest-wins (:matches db) 2)]
    (is (>= (Math/abs (- (:home-goal a) (:away-goal a)))
            (Math/abs (- (:home-goal b) (:away-goal b)))))))

(deftest scenario-best-away-record
  (let [rs (timed 5000 (q/best-records db {:venue "away" :competition "Brasileirão"}))]
    (is (seq rs))
    (is (apply >= (map :win-rate rs)))))

(deftest scenario-derbies
  (let [ds (q/derbies db {:season 2023})]
    (is (seq ds))
    (is (some #(= #{"flamengo" "fluminense"} #{(:home-key %) (:away-key %)}) ds))))

;; ------------------------------------------------------------ players

(deftest scenario-brazilian-players
  (let [ps (q/find-players db {:nationality "Brazil" :limit 5})]
    (is (= "Neymar Jr" (:name (first ps))))
    (is (every? #(= "Brazil" (:nationality %)) ps))
    (is (str/includes? (tool "search_players" {"nationality" "Brazil" "limit" 3})
                       "Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain"))))

(deftest scenario-players-by-club
  (let [ps (q/find-players db {:club "Grêmio"})]
    (is (seq ps))
    (is (every? #(= "Grêmio" (:club %)) ps)))
  (testing "Santos does not match Santos Laguna"
    (is (every? #(= "Santos" (:club %)) (q/find-players db {:club "Santos"}))))
  (testing "position groups"
    (is (every? #(#{"ST" "CF" "LF" "RF" "LW" "RW" "LS" "RS"} (:position %))
                (q/find-players db {:club "Santos" :position "forward"}))))
  (is (str/includes? (tool "brazilian_players_by_club" {}) "players (avg rating:")))

(deftest scenario-player-by-name
  (let [p (first (q/find-players db {:name "neymar"}))]
    (is (= "Paris Saint-Germain" (:club p)))))

(deftest scenario-cross-file-player-and-matches
  (let [{:keys [player club-record]} (q/player-team-profile db "Everton")]
    (is (some? player))
    (let [text (tool "player_profile" {"name" "Luan"})]
      (is (str/includes? text "record in match data")))))

;; ------------------------------------------------------------ MCP protocol

(deftest mcp-protocol
  (let [h #(s/handle (constantly db) (json/read-str (json/write-str %)))
        init (h {:jsonrpc "2.0" :id 1 :method "initialize" :params {:protocolVersion "2024-11-05"}})
        lst (h {:jsonrpc "2.0" :id 2 :method "tools/list"})
        call (h {:jsonrpc "2.0" :id 3 :method "tools/call"
                 :params {:name "head_to_head" :arguments {:team "Flamengo" :opponent "Fluminense"}}})]
    (is (= "brazilian-soccer" (get-in init [:result :serverInfo :name])))
    (is (<= 10 (count (get-in lst [:result :tools]))))
    (is (every? #(get-in % [:inputSchema :type]) (get-in lst [:result :tools])))
    (is (str/includes? (get-in call [:result :content 0 :text]) "Head-to-head"))
    (is (nil? (h {:jsonrpc "2.0" :method "notifications/initialized"})))
    (is (= -32601 (get-in (h {:jsonrpc "2.0" :id 4 :method "bogus"}) [:error :code])))
    (is (= -32602 (get-in (h {:jsonrpc "2.0" :id 5 :method "tools/call" :params {:name "nope"}})
                          [:error :code])))))

(deftest twenty-sample-questions
  (testing "every tool answers representative questions without error"
    (doseq [[t a] [["search_matches" {"team" "Flamengo" "opponent" "Fluminense"}]
                   ["search_matches" {"team" "Palmeiras" "season" 2023}]
                   ["search_matches" {"team" "Corinthians" "venue" "home" "season" 2022}]
                   ["search_matches" {"competition" "Copa do Brasil" "season" 2019}]
                   ["search_matches" {"date_from" "2023-04-01" "date_to" "2023-04-30"}]
                   ["head_to_head" {"team" "Palmeiras" "opponent" "Santos"}]
                   ["head_to_head" {"team" "Grêmio" "opponent" "Internacional"}]
                   ["team_stats" {"team" "Corinthians" "season" 2022 "venue" "home"}]
                   ["team_stats" {"team" "Flamengo" "competition" "Libertadores"}]
                   ["standings" {"season" 2019}]
                   ["standings" {"season" 2010}]
                   ["top_scoring_teams" {"season" 2023}]
                   ["competition_stats" {"competition" "Brasileirão"}]
                   ["competition_stats" {"season" 2018}]
                   ["best_records" {"venue" "home"}]
                   ["best_records" {"venue" "away"}]
                   ["team_competitions" {"team" "Palmeiras"}]
                   ["cup_finals" {"competition" "Copa do Brasil"}]
                   ["cup_finals" {"competition" "Libertadores"}]
                   ["derbies" {"season" 2023}]
                   ["search_players" {"nationality" "Brazil"}]
                   ["search_players" {"club" "Grêmio"}]
                   ["brazilian_players_by_club" {}]
                   ["player_profile" {"name" "Neymar"}]]]
      (let [out (timed 5000 (tool t a))]
        (is (and (string? out) (> (count out) 20)) (str t " " a))))))
