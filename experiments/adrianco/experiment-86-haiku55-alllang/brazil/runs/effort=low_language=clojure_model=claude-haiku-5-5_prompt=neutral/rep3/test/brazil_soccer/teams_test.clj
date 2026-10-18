(ns brazil-soccer.teams-test
  (:require [clojure.test :refer [deftest is testing]]
            [brazil-soccer.teams :as teams]))

(deftest team-names-normalize-to-one-key
  (testing "Given a team written with a state suffix, when normalized, then the suffix is dropped"
    (is (= "palmeiras" (teams/team-key "Palmeiras-SP")))
    (is (= "palmeiras" (teams/team-key "Palmeiras"))))
  (testing "Given accented and unaccented spellings, when normalized, then they match"
    (is (= "sao paulo" (teams/team-key "São Paulo-SP")))
    (is (= "sao paulo" (teams/team-key "Sao Paulo")))
    (is (= "gremio" (teams/team-key "Grêmio")))
    (is (= "ceara" (teams/team-key "Ceará-CE"))))
  (testing "Given variant club names, when normalized, then they resolve to the canonical club"
    (is (= "athletico pr" (teams/team-key "Athletico Paranaense")))
    (is (= "athletico pr" (teams/team-key "Atlético-PR")))
    (is (= "atletico mg" (teams/team-key "Atlético-MG")))
    (is (= "atletico mg" (teams/team-key "Atlético Mineiro")))
    (is (= "sport" (teams/team-key "Sport Club do Recife")))
    (is (= "corinthians" (teams/team-key "Sport Club Corinthians Paulista")))
    (is (= "vasco da gama" (teams/team-key "Vasco Da Gama RJ")))
    (is (= "america mg" (teams/team-key "América FC (Minas Gerais)")))))

(deftest same_name_clubs_in_different_states_stay_apart
  (testing "Given America from Minas Gerais and from Rio Grande do Norte, then they differ"
    (is (not= (teams/team-key "America-MG") (teams/team-key "America-RN"))))
  (testing "Given Nacional from Uruguay and from Paraguay, then they differ"
    (is (= "nacional uru" (teams/team-key "Nacional (URU)")))
    (is (= "nacional par" (teams/team-key "Nacional (PAR)")))))

(deftest parenthetical_notes_are_ignored
  (testing "Given a cup name with an old-name note and a state suffix"
    (is (= "boavista sport club"
           (teams/team-key "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")))))

(deftest brazilian_clubs_are_recognised
  (testing "Given Brazilian clubs under their FIFA names, then they are Brazilian"
    (is (teams/brazilian-club? "Grêmio"))
    (is (teams/brazilian-club? "Atlético Paranaense"))
    (is (teams/brazilian-club? "Sport Club do Recife")))
  (testing "Given a Portuguese club with a Brazilian-sounding name, then it is not Brazilian"
    (is (not (teams/brazilian-club? "Vitória Guimarães")))
    (is (not (teams/brazilian-club? "Real Madrid")))))

(deftest competition_labels_resolve
  (testing "Given free-form competition labels, then they resolve to a competition"
    (is (= :serie-a (teams/competition-of "Serie A")))
    (is (= :serie-a (teams/competition-of "Brasileirão Série A")))
    (is (= :serie-b (teams/competition-of "Brasileirão Série B")))
    (is (= :copa-do-brasil (teams/competition-of "Copa do Brasil")))
    (is (= :libertadores (teams/competition-of "Copa Libertadores"))))
  (testing "Given an unknown label, then nothing resolves"
    (is (nil? (teams/competition-of "Premier League")))))

(deftest display_names_are_title_cased
  (is (= "Sao Paulo" (teams/display-name "sao paulo"))))
