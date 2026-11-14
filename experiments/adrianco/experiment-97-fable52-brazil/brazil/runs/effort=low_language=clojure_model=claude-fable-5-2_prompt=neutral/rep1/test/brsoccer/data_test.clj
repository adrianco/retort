(ns brsoccer.data-test
  "Feature: loading and normalising the six provided CSV files."
  (:require [brsoccer.data :as data]
            [brsoccer.queries :as q]
            [brsoccer.teams :as teams]
            [clojure.test :refer [deftest is testing]]))

(deftest date-formats
  (testing "Given dates in the three formats used by the datasets"
    (testing "Then each parses to ISO yyyy-MM-dd"
      (is (= "2023-09-24" (data/parse-date "2023-09-24")))
      (is (= "2003-03-29" (data/parse-date "29/03/2003")))
      (is (= "2012-05-19" (data/parse-date "2012-05-19 18:30:00"))))
    (testing "And garbage or impossible dates give nil"
      (is (nil? (data/parse-date "NA")))
      (is (nil? (data/parse-date "")))
      (is (nil? (data/parse-date "31/02/2020"))))))

(deftest goal-parsing
  (is (= 3 (data/parse-int "3")))
  (is (= 3 (data/parse-int "3.0")))
  (is (= 0 (data/parse-int "0")))
  (is (nil? (data/parse-int "NA")))
  (is (nil? (data/parse-int "-")))
  (is (nil? (data/parse-int ""))))

(deftest name-parsing
  (testing "state and country suffixes are peeled off in every notation"
    (is (= {:base "palmeiras" :state "SP"} (select-keys (teams/parse "Palmeiras-SP") [:base :state])))
    (is (= {:base "america" :state "MG"} (select-keys (teams/parse "América - MG") [:base :state])))
    (is (= {:base "botafogo" :state "RJ"} (select-keys (teams/parse "Botafogo RJ") [:base :state])))
    (is (= {:base "nacional" :state "URU"} (select-keys (teams/parse "Nacional (URU)") [:base :state])))
    (is (= {:base "barcelona" :state "EQU"} (select-keys (teams/parse "Barcelona-EQU") [:base :state]))))
  (testing "full names, acronyms and club-type tokens are normalised"
    (is (= "corinthians" (:base (teams/parse "Sport Club Corinthians Paulista"))))
    (is (= "crb" (:base (teams/parse "C. R. B. - AL"))))
    (is (= "sao paulo" (:base (teams/parse "São Paulo FC"))))
    (is (= "bahia" (:base (teams/parse "EC Bahia"))))
    (is (= ["athletico" "PR"] ((juxt :base :state) (teams/parse "Atlético - PR"))))
    (is (= ["atletico" "MG"] ((juxt :base :state) (teams/parse "Atletico Mineiro")))))
  (testing "a bad state hint never renames a well-known club"
    (is (nil? (:state (teams/parse "Bahia" "BH"))))
    (is (= "SP" (:state (teams/parse "Barueri" "SP")))))
  (testing "a hyphen inside a name is not mistaken for a suffix"
    (is (= "colo colo" (:base (teams/parse "Colo-Colo"))))
    (is (= ["ji parana" "RO"] ((juxt :base :state) (teams/parse "Ji-paraná - RO"))))))

(deftest all-files-load
  (testing "Given the data directory"
    (let [db (data/db)]
      (testing "Then all six CSV files are read in full"
        (is (= {"Brasileirao_Matches.csv" 4180
                "Brazilian_Cup_Matches.csv" 1337
                "Libertadores_Matches.csv" 1255
                "BR-Football-Dataset.csv" 10296
                "novo_campeonato_brasileiro.csv" 6886
                "fifa_data.csv" 18207}
               (:row-counts db))))
      (testing "And every file contributes matches"
        (is (= (set (butlast data/files)) (set (mapcat :sources (:matches db))))))
      (testing "And every match has teams, a score, a competition and a date"
        (is (every? #(and (:home %) (:away %) (:home-name %) (:away-name %)
                          (nat-int? (:hg %)) (nat-int? (:ag %))
                          (data/competitions (:competition %))
                          (re-matches #"\d{4}-\d{2}-\d{2}" (:date %))
                          (integer? (:season %)))
                    (:matches db))))
      (testing "And all players are loaded with accents intact"
        (is (= 18207 (count (:players db))))
        (is (some #(= "Grêmio" (:club %)) (:players db)))))))

(deftest duplicates-are-merged
  (testing "Given Série A seasons that appear in up to three files"
    (let [db (data/db)]
      (doseq [season (range 2006 2023)]
        (testing (str "Then season " season " has one copy of each fixture: 38 matches per club")
          (let [ms     (q/find-matches db {:competition :serie-a :season season})
                counts (frequencies (mapcat (juxt :home :away) ms))]
            ;; BR-Football-Dataset.csv labels one 2016 Brasília v Taguatinga
            ;; game as "Serie A"; those two clubs are the only tolerated extras.
            (is (= 20 (count (filter #(= 38 (val %)) counts))))
            (is (every? #(= 1 (val %)) (remove #(= 38 (val %)) counts)))
            (is (<= 380 (count ms) 381)))))
      (testing "And extended statistics survive the merge"
        (let [m (first (q/find-matches db {:competition :serie-a :season 2019
                                           :team "flamengo" :opponent "gremio" :venue :home}))]
          (is (= [3 1] [(:hg m) (:ag m)]))
          (is (= "Maracanã" (:arena m)))
          (is (some? (get-in m [:stats :home-shots])))
          (is (< 1 (count (:sources m)))))))))

(deftest season-straddling-new-year
  (testing "Given a file with dates but no season column"
    (let [db   (data/db)
          b20  (q/find-matches db {:competition :serie-b :season 2020})
          b21  (q/find-matches db {:competition :serie-b :season 2021})]
      (testing "Then 2020-season matches played in January 2021 stay in 2020"
        (is (some #(= "2021-01" (subs (:date %) 0 7)) b20))
        (is (= 20 (count (distinct (mapcat (juxt :home :away) b20))))))
      (testing "And the 2021 season only starts with its own first round"
        (is (every? #(pos? (compare (:date %) "2021-05-01")) b21))
        (is (= 20 (count (distinct (mapcat (juxt :home :away) b21))))))
      (testing "And the 2020 Copa do Brasil final (played in March 2021) is a 2020 match"
        (is (= ["2021-03-07" "2021-02-28"]
               (map :date (q/find-matches db {:competition :copa-do-brasil :season 2020 :stage "final"}))))))))

(deftest team-name-variations
  (testing "Given the different spellings used across files and by users"
    (let [db (data/db)]
      (doseq [[expected spellings]
              {"palmeiras"   ["Palmeiras" "Palmeiras-SP" "Palmeiras - SP" "palmeiras" "SE Palmeiras"]
               "sao paulo"   ["São Paulo" "Sao Paulo" "Sao Paulo-SP" "São Paulo FC" "São Paulo - SP"]
               "gremio"      ["Grêmio" "Gremio" "Gremio-RS" "Gremio RS"]
               "atletico-mg" ["Atlético Mineiro" "Atletico-MG" "Atlético - MG" "Atletico Mineiro" "atletico mg"]
               "athletico"   ["Athletico-PR" "Atlético - PR" "Athletico Paranaense" "Atletico Paranaense" "Athletico"]
               "vasco"       ["Vasco" "Vasco da Gama - RJ" "Vasco Da Gama RJ"]
               "sport"       ["Sport" "Sport-PE" "Sport Recife" "Sport Club do Recife"]
               "america-mg"  ["América-MG" "America MG" "América - MG" "América FC (Minas Gerais)"]
               "corinthians" ["Corinthians" "Sport Club Corinthians Paulista" "Corinthians-SP"]
               "flamengo"    ["Flamengo" "Flamengo-RJ" "Flamengo - RJ" "FLAMENGO"]}
              s spellings]
        (testing (str "Then \"" s "\" resolves to " expected)
          (is (= expected (q/resolve-team db s)))))
      (testing "And namesakes from other states stay separate clubs"
        (is (= "flamengo-pi" (q/resolve-team db "Flamengo - PI")))
        (is (= "botafogo-pb" (q/resolve-team db "Botafogo PB")))
        (is (not= (q/resolve-team db "Atlético-GO") (q/resolve-team db "Atlético-MG"))))
      (testing "And display names keep Portuguese accents"
        (is (= "São Paulo" (q/team-name db "sao paulo")))
        (is (= "Grêmio" (q/team-name db "gremio")))
        (is (= "Avaí" (q/team-name db "avai"))))
      (testing "And unknown names resolve to nothing"
        (is (nil? (q/resolve-team db "Xyzzy United")))
        (is (nil? (q/resolve-team db "")))))))

(deftest fifa-clubs-link-to-match-teams
  (testing "Given FIFA club names"
    (let [db (data/db)
          key-of (fn [club] (:club-key (first (filter #(= club (:club %)) (:players db)))))]
      (testing "Then Brazilian clubs link to their match-data team"
        (is (= "atletico-mg" (key-of "Atlético Mineiro")))
        (is (= "sport" (key-of "Sport Club do Recife")))
        (is (= "santos" (key-of "Santos"))))
      (testing "And foreign namesakes are not linked"
        (is (nil? (key-of "Boavista FC")))
        (is (nil? (key-of "Santos Laguna")))
        (is (nil? (key-of "FC Barcelona")))))))
