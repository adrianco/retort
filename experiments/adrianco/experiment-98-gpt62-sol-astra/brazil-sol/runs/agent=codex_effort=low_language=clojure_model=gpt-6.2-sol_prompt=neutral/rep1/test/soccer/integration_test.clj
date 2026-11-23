(ns soccer.integration-test
  (:require [clojure.data.json :as json]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [soccer.data :as data]
            [soccer.server :as server]))

(def db (delay (data/load-data)))

(defn request [method params]
  (->> {:jsonrpc "2.0" :id 1 :method method :params params}
       json/write-str (server/process-line @db)))

(defn ask [tool args]
  (let [response (request "tools/call" {:name tool :arguments args})
        result (:result response)]
    (is (false? (:isError result)) (pr-str response))
    (:structuredContent result)))

(deftest given-all-six-files
  (testing "Every file is loaded and its rows can be retrieved"
    (let [coverage (ask "data_coverage" {})]
      (is (= (zipmap data/files [4180 1337 1255 6886 10296 18207]) (:sources coverage)))
      (is (false? (:individual-goalscorers-available coverage)))
      (doseq [source (butlast data/files)]
        (let [page (ask "find_matches" {:source source :limit 1})]
          (is (= (get-in coverage [:sources source]) (:total page)))
          (is (= [source] (get-in page [:results 0 :sources])))))
      (is (= 18207 (:total (ask "find_players" {:limit 1})))))))

(deftest match-questions
  (testing "Show all Fla-Flu derbies and get the latest Flamengo–Corinthians score"
    (let [page (ask "find_matches" {:team "Flamengo-RJ" :opponent "Fluminense" :limit 2})
          latest (first (:results (ask "find_matches" {:team "Flamengo" :opponent "Corinthians"
                                                      :completed true :limit 1})))]
      (is (> (:total page) 2))
      (is (= 2 (:next-offset page)))
      (is (every? #(and (:date %) (:competition %) (number? (:home-goals %))) (:results page)))
      (is (= #{"flamengo" "corinthians"} (set ((juxt :home-id :away-id) latest))))
      (is (every? number? ((juxt :home-goals :away-goals) latest)))
      (is (= 2 (:offset (ask "find_matches" {:team "Flamengo" :opponent "Fluminense" :offset 2}))))))
  (testing "What matches did Palmeiras play in 2023, and who played at home?"
    (let [args {:team "Sociedade Esportiva Palmeiras" :season 2023 :competition "Brasileirão"}
          home (ask "find_matches" (assoc args :venue "home"))
          away (ask "find_matches" (assoc args :venue "away"))]
      (is (= 18 (:total home)))
      (is (= "palmeiras" (get-in home [:results 0 :home-id])))
      (is (= "palmeiras" (get-in away [:results 0 :away-id])))))
  (testing "Find Copa do Brasil finals and select an inclusive date range"
    (let [args {:competition "Copa do Brasil" :stage "final"}
          finals (ask "find_matches" args)
          day (ask "find_matches" (assoc args :from "24/09/2023" :to "2023-09-24"))]
      (is (= 24 (:total finals)))
      (is (= 1 (:total day)))
      (is (= [1 1] ((juxt :home-goals :away-goals) (first (:results day)))))))
  (testing "Find historical fixtures and traditional rivals in 2023"
    (is (= 2 (:total (ask "find_matches" {:team "Grêmio" :opponent "Internacional" :season 2023
                                         :competition "Serie A" :derby true}))))
    (is (= "Brinco de Ouro"
           (get-in (ask "find_matches" {:team "Guarani-SP" :season 2003
                                        :from "29/03/2003" :to "29/03/2003"})
                   [:results 0 :stadium])))))

(deftest team-and-competition-questions
  (testing "Corinthians' 2022 home record uses completed scores from overlapping sources"
    (let [result (ask "team_stats" {:team "Sport Club Corinthians Paulista" :season 2022
                                    :competition "Serie A" :venue "home"})]
      (is (= [19 12 4 3 24 11] ((juxt :played :wins :draws :losses :goals-for :goals-against) (:record result))))
      (is (= 0 (get-in result [:away :played])))))
  (testing "Compare Palmeiras and Santos, and list Palmeiras competitions"
    (let [{:keys [team-record opponent-record matches]}
          (ask "head_to_head" {:team "Palmeiras" :opponent "Santos FC"})]
      (is (pos? (:total matches)))
      (is (= (:wins team-record) (:losses opponent-record)))
      (is (= (:goals-for team-record) (:goals-against opponent-record))))
    (is (= #{"Brasileirão Série A" "Copa do Brasil" "Copa Libertadores"}
           (set (map :group (:by-competition (ask "team_stats" {:team "Palmeiras"})))))))
  (testing "Who won 2019 and which teams were relegated in 2020?"
    (let [table (ask "standings" {:season 2019})
          relegation (:relegation-zone (ask "standings" {:season 2020}))]
      (is (:complete table))
      (is (= 380 (:fixtures table)))
      (is (= ["flamengo" 90 28 6 4] ((juxt :team-id :points :wins :draws :losses) (:leader table))))
      (is (= #{"vasco" "goias" "coritiba" "botafogo"} (set (map :team-id relegation))))
      (is (false? (:complete (ask "standings" {:season 2023}))))
    (let [fixture (get-in (ask "find_matches" {:competition "Serie A" :season 2019
                                               :team "CSA" :opponent "São Paulo"
                                               :venue "home"}) [:results 0])]
      (is (= "Rei Pelé" (:stadium fixture)))
      (is (= 3 (count (:sources fixture))))
      (is (contains? (:extended-statistics fixture) "total_corners")))))
  (testing "Show the 2018 Libertadores bracket"
    (let [bracket (ask "knockout_bracket" {:competition "Libertadores" :season 2018})]
      (is (= [["round of 16" 16] ["quarterfinals" 8] ["semifinals" 4] ["final" 2]]
             (mapv (juxt :stage (comp count :matches)) (:stages bracket))))))
  (testing "Compare seasons and rank teams by goals, home record and away record"
    (let [seasons (:by-season (ask "match_statistics" {:competition "Serie A"
                                                      :from "01/01/2018" :to "31/12/2019" :limit 1}))]
      (is (= [[2018 380] [2019 380]] (mapv (juxt :season :played) seasons))))
    (is (pos? (get-in (ask "team_leaders" {:season 2023 :competition "Serie A" :metric "goals-for"})
                     [:results 0 :goals-for])))
    (doseq [venue ["home" "away"]]
      (let [ranking (:results (ask "team_leaders" {:venue venue :season 2019 :min-played 14}))]
        (is (apply >= (map :win-rate ranking)))
        (is (every? #(>= (:played %) 14) ranking)))))
  (testing "Calculate average goals and find biggest victories"
    (let [result (ask "match_statistics" {:competition "Serie A" :season 2019 :limit 2})
          [first-win second-win] (get-in result [:biggest-wins :results])]
      (is (== (/ (double (:goals result)) 380) (:goals-per-match result)))
      (is (= 380 (+ (:home-wins result) (:away-wins result) (:draws result))))
      (is (>= (:margin first-win) (:margin second-win) 1)))))

(deftest player-and-cross-file-questions
  (testing "Find Brazilian players, their highest ratings and attributes"
    (let [result (ask "find_players" {:nationality "Brazilian" :limit 3 :include-attributes true})]
      (is (> (:total result) 500))
      (is (= "Neymar Jr" (get-in result [:results 0 :name])))
      (is (apply >= (map :overall (:results result))))
      (is (number? (get-in result [:results 0 :attributes "Dribbling"]))))
    (is (= "Neymar Jr" (get-in (ask "find_players" {:name "néymar"}) [:results 0 :name]))))
  (testing "Find forwards at a club and handle affiliations absent from the snapshot"
    (let [result (ask "find_players" {:club "Santos FC" :position "forwards"})]
      (is (pos? (:total result)))
      (is (every? #(= "Santos" (:club %)) (:results result))))
    (is (zero? (:total (ask "find_players" {:club "Flamengo"}))))
    (is (zero? (:total (ask "find_players" {:name "Gabriel Barbosa"})))))
  (testing "Join Santos match history and FIFA data, and aggregate Brazilian players by club"
    (let [result (ask "club_profile" {:team "Santos-SP" :season 2019 :competition "Serie A"})]
      (is (= 38 (get-in result [:team :record :played])))
      (is (pos? (get-in result [:players :total]))))
    (let [result (ask "club_player_summary" {:nationality "Brazil" :domestic-only true})]
      (is (pos? (:total result)))
      (is (some #(= "santos" (:club-id %)) (:results result)))
      (is (every? #(number? (:average-overall %)) (:results result))))))

(deftest mcp-stdio-lifecycle
  (let [messages [{:jsonrpc "2.0" :id 1 :method "initialize" :params {:protocolVersion "2025-06-18"}}
                  {:jsonrpc "2.0" :method "notifications/initialized"}
                  {:jsonrpc "2.0" :id "check" :method "ping"}
                  {:jsonrpc "2.0" :id 2 :method "tools/list"}
                  {:jsonrpc "2.0" :id 3 :method "tools/call"
                   :params {:name "team_stats" :arguments {:team "Grêmio" :season 2019}}}]
        input (str (str/join "\n" (map json/write-str messages)) "\n")
        output (java.io.StringWriter.)]
    (with-open [reader (io/reader (java.io.StringReader. input))]
      (server/serve @db reader output))
    (let [[initialize ping listing call :as responses]
          (mapv #(json/read-str % :key-fn keyword) (str/split-lines (str output)))]
      (is (= [1 "check" 2 3] (mapv :id responses)))
      (is (= "2025-06-18" (get-in initialize [:result :protocolVersion])))
      (is (= {} (:result ping)))
      (is (= (set (map :name server/tools)) (set (map :name (get-in listing [:result :tools])))))
      (is (= "Grêmio" (get-in call [:result :structuredContent :team])))
      (is (= (get-in call [:result :structuredContent])
             (json/read-str (get-in call [:result :content 0 :text]) :key-fn keyword)))))
  (testing "Malformed requests and invalid inputs return errors"
    (is (= -32700 (get-in (server/process-line @db "{") [:error :code])))
    (is (= -32602 (get-in (request "tools/call" {:name "unknown"}) [:error :code])))
    (doseq [args [{:limit 0} {:from "31/02/2023"} {:opponent "Santos"}]]
      (is (true? (get-in (request "tools/call" {:name "find_matches" :arguments args})
                         [:result :isError]))))))
