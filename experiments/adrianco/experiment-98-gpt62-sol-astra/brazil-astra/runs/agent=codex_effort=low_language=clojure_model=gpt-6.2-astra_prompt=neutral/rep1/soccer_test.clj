(ns soccer-test
  (:require [clojure.test :refer :all] [clojure.data.json :as json]
            [soccer :as s] [server :as srv]))

(def db (delay (s/load-db "data/kaggle")))
(defn ask [tool args] (s/query @db tool args))
(def league {:competition "Brasileirão" :season 2019})

(deftest source-coverage
  (testing "Given the bundled files, each original row remains queryable"
    (is (= [4180 1337 1255 6886 10296]
           (mapv #(:total (ask "matches" {:source %})) s/files)))
    (is (= 18207 (:total (ask "players" {}))))
    (is (= "2003-03-29" (:date (first (:results (ask "matches" {:end "2003-03-29"}))))))
    (is (contains? (:details (first (:results (ask "matches" {:source (last s/files)})))) :home_corner))))

(deftest match-questions
  (testing "When asking for a rivalry, both orientations and original scores are returned"
    (let [a {:team_name "Flamengo-RJ" :opponent "Fluminense"} r (ask "matches" a)]
      (is (> (:total r) 20))
      (is (every? #(and (:date %) (:competition %) (contains? % :away_goal)
                        (= #{"flamengo" "fluminense"} (set ((juxt :home-id :away-id) %)))) (:results r)))
      (is (= (second (:results r)) (first (:results (ask "matches" (assoc a :offset 1 :limit 1))))))))
  (testing "When asking for competitions, dates, finals, schedules and derbies"
    (is (pos? (:total (ask "matches" {:team_name "Palmeiras" :season 2023}))))
    (is (= 2 (:total (ask "matches" {:competition "Copa do Brasil" :season 2012 :stage "final"}))))
    (is (= 8 (:total (ask "matches" {:competition "Libertadores" :season 2018 :stage "quarterfinals"}))))
    (is (pos? (:total (ask "matches" {:derby true :season 2023}))))
    (is (zero? (:total (ask "matches" {:start "2099-01-01"}))))
    (is (= (s/team "Sport Club Corinthians Paulista") (s/team "Corinthians-SP")))
    (is (= (s/team "São Paulo FC") (s/team "Sao Paulo-SP")))
    (is (not= (s/team "Atlético-MG") (s/team "Atlético-PR")))))

(deftest league-questions
  (testing "When ranking a complete season, each fixture contributes exactly once"
    (let [table (:results (ask "standings" league)) winner (first table)]
      (is (= 20 (count table)))
      (is (= ["flamengo" 90 28 6 4 86 37]
             ((juxt :team :points :wins :draws :losses :goals_for :goals_against) winner)))
      (is (every? #(= 38 (:matches %)) table))
      (is (= 4 (count (:results (ask "standings" (assoc league :season 2020 :offset 16))))))
      (is (= "flamengo" (:team (first (:results (ask "standings" (assoc league :rank_by "goals")))))))))
  (testing "When comparing venues, seasons and score margins"
    (doseq [v ["home" "away"]]
      (let [table (:results (ask "standings" (assoc league :venue v :rank_by "win_rate")))]
        (is (= 19 (:matches (first table))))
        (is (apply >= (map :win_rate table)))))
    (let [stats (ask "statistics" {:competition "Serie A" :group_by "season"})]
      (is (= [380 380] (mapv #(get-in stats [% :played]) ["2018" "2019"])))
      (is (= (/ 876.0 380) (get-in stats ["2019" :average_goals]))))
    (let [margin #(abs (- (:home_goal %) (:away_goal %)))]
      (is (apply >= (map margin (:results (ask "biggest_wins" league))))))))

(deftest relationship-questions
  (testing "When querying a club, matches and the FIFA snapshot share a team identity"
    (let [profile (ask "team_profile" {:team_name "Grêmio-RS" :season 2019})]
      (is (= 20 (get-in profile [:players :total])))
      (is (contains? (:by_competition profile) "Libertadores"))
      (is (= (:record profile) (get-in profile [:by_season "2019"]))))
    (let [a {:team_name "Palmeiras" :opponent "Santos" :competition "Serie A" :season 2019}]
      (is (= 2 (get-in (ask "team_profile" a) [:record :matches])))
      (is (= 1 (get-in (ask "team_profile" (assoc a :venue "home")) [:record :matches])))))
  (testing "When searching player names, nationalities, clubs and positions"
    (is (= "Neymar Jr" (:name (first (:results (ask "players" {:nationality "Brazil"}))))))
    (is (= "L. Messi" (:name (first (:results (ask "players" {:name "messi"}))))))
    (is (pos? (:total (ask "players" {:club "Santos" :position "forward"}))))
    (is (empty? (:results (ask "players" {:club "Flamengo"}))))
    (is (contains? (:attributes (first (:results (ask "players" {:name "messi"})))) :Finishing))))

(deftest protocol
  (let [request (fn [method params] (srv/dispatch @db {:jsonrpc "2.0" :id 7 :method method :params params}))
        call #(request "tools/call" {:name %1 :arguments %2})]
    (is (= "2025-06-18" (get-in (request "initialize" {}) [:result :protocolVersion])))
    (is (= 6 (count (get-in (request "tools/list" {}) [:result :tools]))))
    (is (nil? (srv/dispatch @db {:jsonrpc "2.0" :method "notifications/initialized"})))
    (is (= -32602 (get-in (call "matches" {:limit -1}) [:error :code])))
    (is (= -32602 (get-in (call "team_profile" {}) [:error :code])))
    (is (= -32601 (get-in (request "missing" {}) [:error :code])))
    (is (= 380 (get (json/read-str (get-in (call "matches" (assoc league :limit 1))
                                          [:result :content 0 :text])) "total")))))

(defn -main [& _]
  (let [{:keys [fail error]} (run-tests 'soccer-test)]
    (when (pos? (+ fail error)) (System/exit 1))))
