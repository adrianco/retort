(ns brsoccer.data-test
  (:require [brsoccer.data :as data]
            [brsoccer.names :as names]
            [clojure.test :refer [deftest is testing]]))

(deftest parsing-helpers
  (is (= "2003-03-29" (data/iso-date "29/03/2003")))
  (is (= "2012-05-19" (data/iso-date "2012-05-19 18:30:00")))
  (is (nil? (data/iso-date "NA")))
  (is (= 1 (data/parse-int "1.0")))
  (is (= 3 (data/parse-int "3")))
  (is (nil? (data/parse-int "NA")))
  (is (nil? (data/parse-int "-")))
  (is (nil? (data/parse-int ""))))

(deftest merging-the-same-fixture-from-several-files
  (testing "Given one fixture reported by three files and a return leg"
    (let [base {:competition names/serie-a :home "flamengo" :away "santos"
                :home-goals 2 :away-goals 1}
          rows [(assoc base :source "BR-Football-Dataset.csv" :date "2015-06-01"
                       :season 2015 :stats {:home-corners 7})
                (assoc base :source "Brasileirao_Matches.csv" :date "2015-05-31"
                       :season 2015 :round 4)
                (assoc base :source "novo_campeonato_brasileiro.csv" :date "2015-05-31"
                       :season 2015 :round 4 :arena "Maracanã")
                (assoc base :source "Brasileirao_Matches.csv" :date "2016-05-31"
                       :season 2016 :round 5)
                (assoc base :source "Brasileirao_Matches.csv" :date "2015-09-20"
                       :season 2015 :round 23 :home "santos" :away "flamengo")]
          merged (sort-by :date (data/merge-duplicates rows))]
      (testing "When duplicates are merged"
        (testing "Then three distinct matches remain"
          (is (= ["2015-05-31" "2015-09-20" "2016-05-31"] (map :date merged))))
        (testing "Then the merged match keeps every file's extra fields"
          (let [m (first merged)]
            (is (= 4 (:round m)))
            (is (= "Maracanã" (:arena m)))
            (is (= {:home-corners 7} (:stats m)))
            (is (= 3 (count (:sources m))))))))))

(deftest all-six-files-load
  (testing "Given the Kaggle data directory"
    (let [db @data/db]
      (testing "Then every file is read in full"
        (is (= {"Brasileirao_Matches.csv" 4180
                "Brazilian_Cup_Matches.csv" 1337
                "Libertadores_Matches.csv" 1255
                "BR-Football-Dataset.csv" 10296
                "novo_campeonato_brasileiro.csv" 6886
                "fifa_data.csv" 18207}
               (:files db))))
      (testing "Then every match file contributes matches"
        (is (= #{"Brasileirao_Matches.csv" "Brazilian_Cup_Matches.csv"
                 "Libertadores_Matches.csv" "BR-Football-Dataset.csv"
                 "novo_campeonato_brasileiro.csv"}
               (into #{} (mapcat :sources) (:matches db)))))
      (testing "Then all players are present with parsed ratings"
        (is (= 18207 (count (:players db))))
        (is (= 94 (:overall (first (filter #(= "L. Messi" (:name %)) (:players db)))))))
      (testing "Then every match is complete and UTF-8 names survive"
        (is (every? #(and (:date %) (:home-name %) (:away-name %) (:competition %)
                          (integer? (:home-goals %)) (integer? (:away-goals %)))
                    (:matches db)))
        (is (not-any? #(= (:home %) (:away %)) (:matches db)))
        (is (contains? (set (vals (:teams db))) "Grêmio")))
      (testing "Then overlapping files do not double-count a league season"
        (doseq [season (range 2006 2023)
                :let [n (count (filter #(and (= names/serie-a (:competition %))
                                             (= season (:season %)))
                                       (:matches db)))]]
          (is (<= 379 n 381) (str "Série A " season)))))))
