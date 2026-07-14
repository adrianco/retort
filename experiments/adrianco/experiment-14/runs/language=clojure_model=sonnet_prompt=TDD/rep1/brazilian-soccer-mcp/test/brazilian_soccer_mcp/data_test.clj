(ns brazilian-soccer-mcp.data-test
  (:require [clojure.test :refer :all]
            [brazilian-soccer-mcp.data :as data]))

(def test-data-dir
  (-> (java.io.File. "test/fixtures") .getAbsolutePath))

(deftest parse-brasileirao-row-test
  (testing "parses a Brasileirao row correctly"
    (let [row {"datetime" "2012-05-19 18:30:00"
               "home_team" "Palmeiras-SP"
               "home_team_state" "SP"
               "away_team" "Portuguesa-SP"
               "away_team_state" "SP"
               "home_goal" "1"
               "away_goal" "1"
               "season" "2012"
               "round" "1"}
          parsed (data/parse-brasileirao-row row)]
      (is (= "Palmeiras" (:home-team parsed)))
      (is (= "Portuguesa" (:away-team parsed)))
      (is (= 1 (:home-goal parsed)))
      (is (= 1 (:away-goal parsed)))
      (is (= 2012 (:season parsed)))
      (is (= 1 (:round parsed)))
      (is (= "brasileirao" (:competition parsed))))))

(deftest parse-cup-row-test
  (testing "parses a Copa do Brasil row"
    (let [row {"round" "1"
               "datetime" "2012-03-07 16:00:00"
               "home_team" "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
               "away_team" "América - MG"
               "home_goal" "0"
               "away_goal" "0"
               "season" "2012"}
          parsed (data/parse-cup-row row)]
      (is (= "copa-do-brasil" (:competition parsed)))
      (is (= 0 (:home-goal parsed)))
      (is (= 0 (:away-goal parsed)))
      (is (= 2012 (:season parsed))))))

(deftest parse-libertadores-row-test
  (testing "parses a Libertadores row"
    (let [row {"datetime" "2013-02-12 20:15:00"
               "home_team" "Nacional (URU)"
               "away_team" "Barcelona-EQU"
               "home_goal" "2"
               "away_goal" "2"
               "season" "2013"
               "stage" "group stage"}
          parsed (data/parse-libertadores-row row)]
      (is (= "libertadores" (:competition parsed)))
      (is (= "group stage" (:stage parsed)))
      (is (= 2 (:home-goal parsed))))))

(deftest parse-br-football-row-test
  (testing "parses a BR-Football-Dataset row"
    (let [row {"tournament" "Copa do Brasil"
               "home" "Sao Paulo"
               "away" "Flamengo"
               "home_goal" "1.0"
               "away_goal" "1.0"
               "home_corner" "2.0"
               "away_corner" "4.0"
               "home_shots" "8.0"
               "away_shots" "13.0"
               "time" "20:00:00"
               "date" "2023-09-24"
               "ht_result" "DRAW"
               "at_result" "DRAW"
               "total_corners" "6.0"}
          parsed (data/parse-br-football-row row)]
      (is (= "Copa do Brasil" (:tournament parsed)))
      (is (= "São Paulo" (:home-team parsed)))
      (is (= "Flamengo" (:away-team parsed)))
      (is (= 1 (:home-goal parsed)))
      (is (= 1 (:away-goal parsed)))
      (is (= 2023 (:season parsed))))))

(deftest parse-historico-row-test
  (testing "parses a historical Brasileirao row"
    (let [row {"ID" "2003.01.0001"
               "Data" "29/03/2003"
               "Ano" "2003"
               "Rodada" "1"
               "Equipe_mandante" "Guarani"
               "Equipe_visitante" "Vasco"
               "Gols_mandante" "4"
               "Gols_visitante" "2"
               "Mandante_UF" "SP"
               "Visitante_UF" "RJ"
               "Vencedor" "Mandante"
               "Arena" "Brinco de Ouro"
               "OBS" ""}
          parsed (data/parse-historico-row row)]
      (is (= "Guarani" (:home-team parsed)))
      (is (= "Vasco" (:away-team parsed)))
      (is (= 4 (:home-goal parsed)))
      (is (= 2 (:away-goal parsed)))
      (is (= 2003 (:season parsed)))
      (is (= "Brinco de Ouro" (:arena parsed)))
      (is (= "brasileirao-historico" (:competition parsed))))))

(deftest parse-fifa-row-test
  (testing "parses a FIFA player row"
    (let [row {"ID" "158023"
               "Name" "L. Messi"
               "Age" "31"
               "Nationality" "Argentina"
               "Overall" "94"
               "Potential" "94"
               "Club" "FC Barcelona"
               "Position" "RF"
               "Jersey Number" "10"
               "Height" "5'7"
               "Weight" "159lbs"}
          parsed (data/parse-fifa-row row)]
      (is (= "158023" (:id parsed)))
      (is (= "L. Messi" (:name parsed)))
      (is (= 31 (:age parsed)))
      (is (= "Argentina" (:nationality parsed)))
      (is (= 94 (:overall parsed)))
      (is (= "FC Barcelona" (:club parsed)))
      (is (= "RF" (:position parsed))))))

(deftest load-csv-test
  (testing "loads a CSV file from path"
    (let [rows (data/load-csv "test/fixtures/sample_brasileirao.csv")]
      (is (seq rows))
      (is (map? (first rows)))
      (is (contains? (first rows) "home_team")))))

(deftest normalize-competition-test
  (testing "maps Serie A to brasileirao"
    (is (= "brasileirao" (data/normalize-competition "Serie A")))
    (is (= "brasileirao" (data/normalize-competition "Série A"))))

  (testing "maps Copa do Brasil"
    (is (= "copa-do-brasil" (data/normalize-competition "Copa do Brasil"))))

  (testing "maps Libertadores"
    (is (= "libertadores" (data/normalize-competition "Copa Libertadores"))))

  (testing "leaves unknown competitions unchanged"
    (is (= "Serie B" (data/normalize-competition "Serie B")))
    (is (= "brasileirao" (data/normalize-competition "brasileirao")))))

(deftest parse-na-goals-test
  (testing "parses NA goals as nil"
    (let [row {"datetime" "2022-11-13 16:00:00"
               "home_team" "Goias-GO"
               "home_team_state" "GO"
               "away_team" "Sao Paulo-SP"
               "away_team_state" "SP"
               "home_goal" "NA"
               "away_goal" "NA"
               "season" "2022"
               "round" "38"}
          parsed (data/parse-brasileirao-row row)]
      (is (nil? (:home-goal parsed)))
      (is (nil? (:away-goal parsed)))
      (is (= 2022 (:season parsed))))))
