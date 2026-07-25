(ns brazilian-soccer.data-test
  "Data loading, date parsing and de-duplication.

  CONTEXT
  -------
  The heart of this suite: the three Série A files overlap heavily, so a
  fixture that is counted twice silently corrupts every table and average.  The
  strongest available check is that a de-duplicated season is exactly a double
  round-robin, and that the resulting tables reproduce published Brasileirão
  results (Flamengo's 90 points in 2019, Palmeiras' 80 in 2018)."
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.fixtures :refer [test-db]]
            [brazilian-soccer.query :as q]))

(deftest date-formats
  (testing "all three formats found in the CSV files"
    (is (= ["2012-05-19" "18:30"] (data/parse-date "2012-05-19 18:30:00")))
    (is (= ["2023-09-24" nil]     (data/parse-date "2023-09-24")))
    (is (= ["2003-03-29" nil]     (data/parse-date "29/03/2003")))
    (is (= ["2003-01-09" nil]     (data/parse-date "9/1/2003")))
    (is (nil? (data/parse-date "NA")))
    (is (nil? (data/parse-date "")))))

(deftest numeric-parsing
  (is (= 2 (data/->int "2")))
  (is (= 2 (data/->int "2.0")) "BR-Football-Dataset stores goals as floats")
  (is (nil? (data/->int "-")) "the Libertadores file marks an unplayed match with a dash")
  (is (nil? (data/->int ""))))

(deftest br-football-season-inference
  (testing "the file has no season column and the COVID seasons ran into the next year"
    (is (= 2023 (data/br-football-season "2023-05-01" :serie-a)))
    (is (= 2020 (data/br-football-season "2021-02-25" :serie-a)))
    (is (= 2021 (data/br-football-season "2022-02-01" :serie-a)))
    (is (= 2023 (data/br-football-season "2023-02-28" :copa-do-brasil))
        "the cup does start in February, so cup dates are never shifted")))

(deftest all-six-files-are-loaded
  (let [db (test-db)
        rows (get-in db [:stats :rows-by-source])]
    (is (= 4180  (:brasileirao rows)))
    (is (= 1337  (:cup rows)))
    (is (= 1255  (:libertadores rows)))
    (is (= 10296 (:br-football rows)))
    (is (= 6886  (:novo rows)))
    (is (= 18207 (count (:players db))))
    (is (<= 1 (get-in db [:stats :dropped-rows]) 2)
        "only the placeholder Libertadores row without a season is discarded")))

(deftest seasons-are-complete-round-robins
  (testing "de-duplication leaves exactly one record per fixture"
    (let [db (test-db)
          count-of (fn [season] (count (q/find-matches db {:competition :serie-a :season season})))]
      ;; 20 teams playing everyone home and away = 380 matches
      (doseq [season (range 2006 2023)]
        (is (= 380 (count-of season)) (str "Série A " season " should be a 20 team double round-robin")))
      ;; 24 teams in 2003-2004, 22 in 2005
      (is (= 552 (count-of 2003)))
      (is (= 552 (count-of 2004)))
      (is (= 462 (count-of 2005))))))

(deftest overlapping-files-are-merged-not-duplicated
  (let [db (test-db)
        m (first (q/find-matches db {:competition :serie-a :season 2019
                                     :team-id "flamengo|rj" :venue :home :round 27}))]
    (is (some? m))
    (is (= "2019-10-20" (:date m)))
    (is (= ["br-football" "brasileirao" "novo"] (:sources m))
        "this fixture is present in three files and must appear once")
    (is (= "Maracanã" (:venue m)) "the stadium only exists in novo_campeonato_brasileiro.csv")
    (is (= 27 (:round m)) "the round comes from Brasileirao_Matches.csv")
    (is (pos? (get-in m [:stats :home-shots])) "shots only exist in BR-Football-Dataset.csv")))

(deftest scores-missing-from-one-file-are-filled-from-another
  (testing "Brasileirao_Matches.csv was scraped mid-2022 and has 82 fixtures without a score"
    (let [db (test-db)
          late-2022 (q/find-matches db {:competition :serie-a :season 2022
                                        :date-from "2022-10-01"})]
      (is (seq late-2022))
      (is (every? :played? late-2022))
      (is (every? :round late-2022) "the round survives the merge"))))

(deftest team-index
  (let [db (test-db)]
    (testing "canonical clubs carry their display name, state and spellings"
      (let [t (get-in db [:teams "atletico|pr"])]
        (is (= "Athletico Paranaense" (:display t)))
        (is (= "PR" (:state t)))
        (is (some #{"Athletico"} (:variants t)))
        (is (some #{"Atletico-PR"} (:variants t)))
        (is (some #{"Atlético Paranaense - PR"} (:variants t)))))
    (testing "clubs sharing a base name are displayed unambiguously"
      (is (not= (get-in db [:teams "america|mg" :display])
                (get-in db [:teams "america|rn" :display]))))))

(deftest fifa-clubs-link-to-the-match-graph
  (let [db (test-db)]
    (is (= "gremio|rs" (get-in db [:club->team-id "Grêmio"])))
    (is (= "sport|pe" (get-in db [:club->team-id "Sport Club do Recife"])))
    (is (= "america|mg" (get-in db [:club->team-id "América FC (Minas Gerais)"])))
    (testing "European clubs are not linked to same-named South American clubs"
      (is (nil? (get-in db [:club->team-id "FC Barcelona"])))
      (is (nil? (get-in db [:club->team-id "Santos Laguna"])))
      (is (nil? (get-in db [:club->team-id "Atlético Madrid"]))))))

(deftest standings-reproduce-published-tables
  (let [db (test-db)
        champion (fn [season]
                   (let [row (first (:table (q/standings db :serie-a season)))]
                     [(:team row) (:points row)]))]
    (is (= ["Flamengo" 90]   (champion 2019)))
    (is (= ["Palmeiras" 80]  (champion 2018)))
    (is (= ["Corinthians" 72] (champion 2017)))
    (is (= ["Palmeiras" 81]  (champion 2022)))
    (is (= ["Cruzeiro" 100]  (champion 2003)))
    (testing "the bottom of the 2020 table matches the clubs that were relegated"
      (let [table (:table (q/standings db :serie-a 2020))
            bottom (set (map :team (take-last 4 table)))]
        (is (= #{"Vasco da Gama" "Goiás" "Coritiba" "Botafogo"} bottom))))))
