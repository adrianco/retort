(ns brsoccer.query-test
  "BDD-style scenarios against the real CSV data."
  (:require [brsoccer.data :as data]
            [brsoccer.names :as names]
            [brsoccer.query :as q]
            [clojure.test :refer [deftest is testing]]))

(defn- db [] @data/db)

(defn- invalid? [f]
  (try (f) false
       (catch clojure.lang.ExceptionInfo e
         (= :invalid-argument (:type (ex-data e))))))

;; Feature: Match queries

(deftest find-matches-between-two-teams
  (testing "Given the match data is loaded"
    (testing "When I search for matches between Flamengo and Fluminense"
      (let [found (q/find-matches (db) {:team "Flamengo" :opponent "Fluminense"})]
        (testing "Then I receive a list of matches"
          (is (> (count found) 30)))
        (testing "And each match has date, scores and competition"
          (is (every? #(and (re-matches #"\d{4}-\d{2}-\d{2}" (:date %))
                            (integer? (:home-goals %)) (integer? (:away-goals %))
                            (string? (:competition %)))
                      found)))
        (testing "And only those two teams are involved"
          (is (every? #(= #{"flamengo" "fluminense"} (set [(:home %) (:away %)])) found)))
        (testing "And the most recent match comes first"
          (is (= (reverse (sort (map :date found))) (map :date found))))))))

(deftest find-matches-by-criteria
  (testing "Given the match data is loaded"
    (testing "When I filter by team and season"
      (let [found (q/find-matches (db) {:team "Palmeiras" :season 2019 :competition "Brasileirão"})]
        (is (= 38 (count found)))))
    (testing "When I filter by venue"
      (let [home (q/find-matches (db) {:team "Palmeiras" :season 2019 :competition "Serie A" :venue "home"})
            away (q/find-matches (db) {:team "Palmeiras" :season 2019 :competition "Serie A" :venue "away"})]
        (is (= 19 (count home) (count away)))
        (is (every? #(= "palmeiras" (:home %)) home))
        (is (every? #(= "palmeiras" (:away %)) away))))
    (testing "When I filter by date range"
      (let [found (q/find-matches (db) {:date-from "2019-11-01" :date-to "2019-11-30"})]
        (is (seq found))
        (is (every? #(<= (compare "2019-11-01" (:date %)) 0 (compare "2019-11-30" (:date %))) found))))
    (testing "When I filter by competition"
      (is (every? #(= names/libertadores (:competition %))
                  (q/find-matches (db) {:competition "Libertadores" :season 2018}))))
    (testing "When I ask for Copa do Brasil finals"
      (let [finals (q/find-matches (db) {:competition "Copa do Brasil" :stage "final"})]
        (is (= #{["athletico-pr" "internacional"]}
               (set (map (comp vec sort (juxt :home :away))
                         (filter #(= 2019 (:season %)) finals)))))
        (is (every? #(= 2 (val %)) (frequencies (map :season finals))))))
    (testing "When I ask for a Libertadores stage"
      (is (= 4 (count (q/find-matches (db) {:competition "Libertadores" :season 2018
                                           :stage "semifinals"}))))
      (is (= 4 (count (q/find-matches (db) {:competition "Libertadores" :season 2018
                                           :stage "Semi-final"})))))
    (testing "When the team or competition is unknown Then the query is rejected"
      (is (invalid? #(q/find-matches (db) {:team "Nowhere United XYZ"})))
      (is (invalid? #(q/find-matches (db) {:competition "Premier League"})))
      (is (invalid? #(q/find-matches (db) {:team "Santos" :venue "sideways"}))))
    (testing "When nothing matches Then the result is empty"
      (is (= [] (q/find-matches (db) {:team "Flamengo" :season 1950}))))))

(deftest team-name-variations-give-the-same-answer
  (testing "Given the different spellings of a club"
    (let [n #(count (q/find-matches (db) {:team %}))]
      (is (= (n "São Paulo") (n "Sao Paulo") (n "sao paulo-sp") (n "São Paulo FC")))
      (is (= (n "Atlético Mineiro") (n "Atletico-MG") (n "Atlético - MG")))
      (is (= (n "Athletico Paranaense") (n "Atletico-PR")))
      (is (pos? (n "São Paulo"))))))

(deftest last-meeting
  (testing "When did Flamengo last play Corinthians?"
    (let [[latest & older] (q/find-matches (db) {:team "Flamengo" :opponent "Corinthians"})]
      (is (every? #(>= (compare (:date latest) (:date %)) 0) older))
      (is (integer? (:home-goals latest))))))

;; Feature: Team queries

(deftest team-statistics
  (testing "Given the match data is loaded"
    (testing "When I request statistics for Flamengo in the 2019 Brasileirão"
      (let [s (:overall (q/team-stats (db) {:team "Flamengo" :season 2019 :competition "Brasileirão"}))]
        (testing "Then I receive wins, losses, draws and goals"
          (is (= {:played 38 :wins 28 :draws 6 :losses 4 :points 90}
                 (select-keys s [:played :wins :draws :losses :points])))
          (is (= 86 (:goals-for s)))
          (is (= 37 (:goals-against s))))))
    (testing "When I request Corinthians' home record in 2022"
      (let [s (q/team-stats (db) {:team "Corinthians" :season 2022 :competition "Brasileirão"
                                  :venue "home"})
            r (:overall s)]
        (is (= 19 (:played r)))
        (is (= (:played r) (+ (:wins r) (:draws r) (:losses r))))
        (is (= r (:home s)))
        (is (< 0 (:win-rate r) 100))))
    (testing "When no season is given Then home plus away equals overall"
      (let [s (q/team-stats (db) {:team "Santos"})]
        (is (= (:played (:overall s)) (+ (:played (:home s)) (:played (:away s)))))
        (is (= (:played (:overall s)) (reduce + (map :played (:by-competition s)))))))))

(deftest head-to-head-comparison
  (testing "When I compare Palmeiras and Santos"
    (let [h (q/head-to-head (db) {:team-a "Palmeiras" :team-b "Santos"})
          rev (q/head-to-head (db) {:team-a "Santos" :team-b "Palmeiras"})]
      (testing "Then wins and draws add up to the matches played"
        (is (pos? (:played h)))
        (is (= (:played h) (+ (:a-wins h) (:b-wins h) (:draws h))))
        (is (= (:played h) (count (:matches h)))))
      (testing "Then the comparison is symmetric"
        (is (= (:a-wins h) (:b-wins rev)))
        (is (= (:a-goals h) (:b-goals rev))))
      (testing "Then the derby is named"
        (is (= "Clássico da Saudade" (:derby h)))))))

(deftest competitions-of-a-team
  (testing "What competitions has Palmeiras played in?"
    (let [c (q/team-competitions (db) {:team "Palmeiras"})]
      (is (= #{names/serie-a names/copa-do-brasil names/libertadores}
             (set (map :competition (:competitions c))))))))

;; Feature: Competition queries

(deftest league-standings
  (testing "Who won the 2019 Brasileirão?"
    (let [s (q/standings (db) {:season 2019})]
      (is (:complete? s))
      (is (= "Flamengo" (:champion s)))
      (is (= 20 (count (:rows s))))
      (is (= [["Flamengo" 90] ["Santos" 74] ["Palmeiras" 74]]
             (map (juxt :name :points) (take 3 (:rows s)))))
      (is (= #{"Cruzeiro" "CSA" "Chapecoense" "Avaí"} (set (:relegated s))))))
  (testing "Champions of other seasons"
    (is (= "Cruzeiro" (:champion (q/standings (db) {:season 2003}))))
    (is (= "Corinthians" (:champion (q/standings (db) {:season 2015}))))
    (is (= "Palmeiras" (:champion (q/standings (db) {:season 2016}))))
    (is (= "Flamengo" (:champion (q/standings (db) {:season 2020})))))
  (testing "Which teams were relegated in 2020?"
    (is (= #{"Vasco da Gama" "Goiás" "Coritiba" "Botafogo"}
           (set (:relegated (q/standings (db) {:season 2020}))))))
  (testing "An incomplete season names no champion"
    (let [s (q/standings (db) {:season 2023})]
      (is (not (:complete? s)))
      (is (nil? (:champion s)))
      (is (empty? (:relegated s)))))
  (testing "A season outside the data is empty, and season is required"
    (is (empty? (:rows (q/standings (db) {:season 1999}))))
    (is (invalid? #(q/standings (db) {})))))

;; Feature: Statistical analysis

(deftest aggregate-statistics
  (testing "What's the average goals per match in the Brasileirão?"
    (let [s (q/competition-stats (db) {:competition "Brasileirão"})]
      (is (< 2.0 (:goals-per-match s) 3.2))
      (is (< 40 (:home-win-rate s) 60))
      (is (< 99.9 (+ (:home-win-rate s) (:away-win-rate s) (:draw-rate s)) 100.1))))
  (testing "Show me the biggest wins"
    (let [wins (q/biggest-wins (db) {:limit 5})
          margin #(abs (- (:home-goals %) (:away-goals %)))]
      (is (= 5 (count wins)))
      (is (apply >= (map margin wins)))
      (is (= (margin (first wins))
             (apply max (map margin (:matches (db))))))))
  (testing "Which team has the best away record?"
    (let [r (q/rank-teams (db) {:venue "away" :metric "win_rate" :competition "Serie A"
                                :season 2019 :limit 3})]
      (is (= "Flamengo" (:name (first (:rows r)))))
      (is (= 19 (:played (first (:rows r)))))))
  (testing "Which team scored the most goals in Serie A 2019?"
    (let [r (q/rank-teams (db) {:metric "goals_for" :competition "Serie A" :season 2019 :limit 1})]
      (is (= ["Flamengo" 86] ((juxt :name :goals-for) (first (:rows r)))))))
  (testing "An unknown metric is rejected"
    (is (invalid? #(q/rank-teams (db) {:metric "vibes"})))))

(deftest derby-matches
  (testing "Show me all derbies in 2019"
    (let [found (q/derbies (db) {:season 2019})]
      (is (seq found))
      (is (every? :derby found))
      (is (every? #(= 2019 (:season %)) found))
      (is (some #(= "Grenal" (:derby %)) found)))))

;; Feature: Player queries

(deftest player-search
  (testing "Given the player data is loaded"
    (testing "When I search by name"
      (let [{:keys [players]} (q/search-players (db) {:name "neymar"})]
        (is (= "Neymar Jr" (:name (first players))))
        (is (= "Paris Saint-Germain" (:club (first players))))))
    (testing "When I ask for Brazilian players"
      (let [{:keys [total players]} (q/search-players (db) {:nationality "Brazil" :limit 10})]
        (is (= 827 total))
        (is (= 10 (count players)))
        (is (= "Neymar Jr" (:name (first players))))
        (is (apply >= (map :overall players)))
        (is (every? #(= "Brazil" (:nationality %)) players))
        (is (= total (:total (q/search-players (db) {:nationality "brazilian"}))))))
    (testing "When I ask for a club's players"
      (let [{:keys [total players]} (q/search-players (db) {:club "Santos"})]
        (is (pos? total))
        (is (every? #(= "Santos" (:club %)) players)))
      (is (= (:total (q/search-players (db) {:club "Grêmio"}))
             (:total (q/search-players (db) {:club "gremio"}))))
      (is (= (:total (q/search-players (db) {:club "Atlético Mineiro"}))
             (:total (q/search-players (db) {:club "Atletico-MG"})))))
    (testing "When I ask for the forwards of a club"
      (let [{:keys [total players]} (q/search-players (db) {:club "Santos" :position "forwards"})]
        (is (pos? total))
        (is (every? (q/position-groups "forward") (map :position players)))))
    (testing "When I filter by position code and rating"
      (let [{:keys [players]} (q/search-players (db) {:position "gk" :min-overall 89})]
        (is (seq players))
        (is (every? #(and (= "GK" (:position %)) (>= (:overall %) 89)) players))))
    (testing "When nobody matches Then the result is empty"
      (is (zero? (:total (q/search-players (db) {:name "zzzqqq"})))))))

(deftest cross-file-queries
  (testing "Given match and player data are both loaded"
    (testing "When I list squads of Brazilian clubs"
      (let [squads (q/brazilian-club-squads (db) {:nationality "Brazil"})
            clubs (set (map :club squads))]
        (is (contains? clubs "Grêmio"))
        (is (contains? clubs "Santos"))
        (is (not (contains? clubs "Paris Saint-Germain")))
        (is (not (contains? clubs "Santos Laguna")))))
    (testing "When I ask for a club profile"
      (let [p (q/team-profile (db) {:team "Gremio"})]
        (is (pos? (:played (:overall p))))
        (is (pos? (:squad-size p)))
        (is (every? #(= "Grêmio" (:club %)) (:squad p)))
        (is (= 5 (count (:recent p))))))))

(deftest query-performance
  (testing "Simple lookups answer in under 2 seconds, aggregates in under 5"
    (let [d (db)
          ms (fn [f] (let [t (System/nanoTime)] (f) (/ (- (System/nanoTime) t) 1e6)))]
      (is (< (ms #(q/find-matches d {:team "Flamengo" :opponent "Corinthians"})) 2000))
      (is (< (ms #(q/search-players d {:name "Gabriel"})) 2000))
      (is (< (ms #(q/standings d {:season 2019})) 5000))
      (is (< (ms #(q/rank-teams d {:venue "away"})) 5000))
      (is (< (ms #(q/competition-stats d {})) 5000)))))
