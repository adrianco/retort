(ns brsoccer.names-test
  (:require [brsoccer.names :as names]
            [clojure.test :refer [deftest is testing are]]))

(deftest team-name-variations
  (testing "Given the spellings used by the different CSV files"
    (testing "Then state suffixes and accents do not matter"
      (are [raw] (= "palmeiras" (names/team-key raw))
        "Palmeiras" "Palmeiras-SP" "Palmeiras - SP" "palmeiras" " PALMEIRAS ")
      (are [raw] (= "sao paulo" (names/team-key raw))
        "São Paulo" "Sao Paulo" "Sao Paulo-SP" "São Paulo - SP" "São Paulo FC")
      (are [raw] (= "gremio" (names/team-key raw))
        "Grêmio" "Gremio-RS" "Grêmio - RS" "Gremio RS"))
    (testing "Then full names and abbreviations of the same club agree"
      (are [raw] (= "atletico-mg" (names/team-key raw))
        "Atlético-MG" "Atletico-MG" "Atlético - MG" "Atletico Mineiro" "Atlético Mineiro - MG")
      (are [raw] (= "athletico-pr" (names/team-key raw))
        "Athletico-PR" "Atletico-PR" "Atlético - PR" "Athletico Paranaense"
        "Athletico Paranaense - PR" "Atlético Paranaense" "Athletico")
      (are [raw] (= "vasco" (names/team-key raw))
        "Vasco" "Vasco da Gama-RJ" "Vasco da Gama - RJ" "Vasco Da Gama RJ")
      (are [raw] (= "sport" (names/team-key raw))
        "Sport" "Sport-PE" "Sport Recife" "Sport Club do Recife")
      (are [raw k] (= k (names/team-key raw))
        "EC Bahia" "bahia"
        "Fortaleza EC" "fortaleza"
        "Botafogo RJ" "botafogo"
        "America MG" "america-mg"
        "América FC (Minas Gerais)" "america-mg"
        "C.s.a. - AL" "csa"
        "Red Bull Bragantino-SP" "bragantino"))))

(deftest homonymous-clubs-stay-apart
  (testing "Given clubs from different states that share a name"
    (is (= "flamengo" (names/team-key "Flamengo - RJ")))
    (is (= "flamengo-pi" (names/team-key "Flamengo - PI")))
    (is (= "botafogo-sp" (names/team-key "Botafogo SP")))
    (is (= "atletico-go" (names/team-key "Atlético-GO")))
    (is (not= (names/team-key "América-MG") (names/team-key "América-RN")))
    (is (= "nacional uru" (names/team-key "Nacional (URU)") (names/team-key "Nacional-URU")))))

(deftest display-names
  (is (= "Palmeiras" (names/display-name "Palmeiras-SP" "palmeiras")))
  (is (= "Flamengo-PI" (names/display-name "Flamengo - PI" "flamengo-pi")))
  (is (= "Botafogo-SP" (names/display-name "Botafogo SP" "botafogo-sp")))
  (is (= "Atlético-MG" (names/display-name "Atletico Mineiro" "atletico-mg"))))

(deftest competition-names
  (are [q c] (= c (names/competition q))
    "Brasileirão" names/serie-a
    "brasileirao" names/serie-a
    "Serie A" names/serie-a
    "Série B" names/serie-b
    "Serie C" names/serie-c
    "Copa do Brasil" names/copa-do-brasil
    "Brazilian Cup" names/copa-do-brasil
    "Copa Libertadores" names/libertadores
    "Campeonato Brasileiro" names/serie-a
    "libertadores" names/libertadores)
  (testing "unrelated competitions are not guessed at"
    (is (nil? (names/competition "Premier League")))
    (is (nil? (names/competition "World Cup")))))

(deftest derby-lookup
  (is (= "Fla-Flu" (names/derby-name "fluminense" "flamengo")))
  (is (nil? (names/derby-name "flamengo" "palmeiras"))))
