(ns brazilian-soccer.names-test
  (:require [brazilian-soccer.names :as names]
            [clojure.test :refer [deftest is testing]]))

(deftest team-variants-share-one-key
  (testing "state suffixes are dropped"
    (is (= "palmeiras" (names/team-key "Palmeiras-SP")))
    (is (= "palmeiras" (names/team-key "Palmeiras")))
    (is (= "flamengo" (names/team-key "Flamengo - RJ"))))
  (testing "accents and case are ignored"
    (is (= "sao paulo" (names/team-key "São Paulo")))
    (is (= (names/team-key "Sao Paulo") (names/team-key "SÃO PAULO"))))
  (testing "full official names map to the common name"
    (is (= "corinthians" (names/team-key "Sport Club Corinthians Paulista")))
    (is (= "gremio" (names/team-key "Grêmio Foot-Ball Porto Alegrense"))))
  (testing "parenthetical qualifiers are dropped"
    (is (= "nacional" (names/team-key "Nacional (URU)")))
    (is (= "boavista sport club"
           (names/team-key "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")))))

(deftest atletico-clubs-are-told-apart-by-state
  (is (= "atletico-mg" (names/team-key "Atletico-MG")))
  (is (= "atletico-mg" (names/team-key "Atlético - MG")))
  (is (= "atletico-mg" (names/team-key "Atletico Mineiro")))
  (is (= "atletico-go" (names/team-key "Atletico-GO")))
  (is (= "atletico-go" (names/team-key "Atletico Goianiense")))
  (testing "Athletico Paranaense has one key whatever the spelling or state"
    (is (= "athletico-pr" (names/team-key "Athletico-PR")))
    (is (= "athletico-pr" (names/team-key "Atlético Paranaense - PR")))
    (is (= "athletico-pr" (names/team-key "Athletico Paranaense")))
    (is (= "athletico-pr" (names/team-key "Athletico"))))
  (is (not= (names/team-key "Atletico-MG") (names/team-key "Atletico-GO"))))

(deftest blank-team-has-no-key
  (is (nil? (names/team-key "")))
  (is (nil? (names/team-key nil))))

(deftest base-name-keeps-display-form
  (is (= "Palmeiras" (names/base-name "Palmeiras-SP")))
  (is (= "Sport Club Corinthians Paulista" (names/base-name "Sport Club Corinthians Paulista"))))

(deftest competition-keys
  (is (= "brasileirao" (names/competition-key "Brasileirão")))
  (is (= "brasileirao" (names/competition-key "Serie A")))
  (is (= "libertadores" (names/competition-key "Copa Libertadores")))
  (is (= "copa do brasil" (names/competition-key "Copa do Brasil"))))
