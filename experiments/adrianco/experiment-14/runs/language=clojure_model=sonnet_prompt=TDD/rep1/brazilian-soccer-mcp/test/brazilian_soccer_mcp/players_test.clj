(ns brazilian-soccer-mcp.players-test
  (:require [clojure.test :refer :all]
            [brazilian-soccer-mcp.players :as p]))

(def sample-players
  [{:id "1" :name "Neymar Jr" :nationality "Brazil" :overall 92 :position "LW" :club "Paris Saint-Germain" :age 31}
   {:id "2" :name "Alisson" :nationality "Brazil" :overall 89 :position "GK" :club "Liverpool" :age 30}
   {:id "3" :name "Casemiro" :nationality "Brazil" :overall 89 :position "CDM" :club "Real Madrid" :age 31}
   {:id "4" :name "Gabriel Barbosa" :nationality "Brazil" :overall 82 :position "ST" :club "Flamengo" :age 26}
   {:id "5" :name "Bruno Henrique" :nationality "Brazil" :overall 80 :position "LW" :club "Flamengo" :age 32}
   {:id "6" :name "L. Messi" :nationality "Argentina" :overall 94 :position "RF" :club "FC Barcelona" :age 31}
   {:id "7" :name "C. Ronaldo" :nationality "Portugal" :overall 93 :position "ST" :club "Juventus" :age 34}
   {:id "8" :name "Vinicius Jr" :nationality "Brazil" :overall 84 :position "LW" :club "Real Madrid" :age 22}])

(deftest find-players-by-name-test
  (testing "exact name search (case-insensitive)"
    (let [results (p/find-players sample-players {:name "Neymar Jr"})]
      (is (= 1 (count results)))
      (is (= "Neymar Jr" (:name (first results))))))

  (testing "partial name search"
    (let [results (p/find-players sample-players {:name "Gabriel"})]
      (is (= 1 (count results)))
      (is (= "Gabriel Barbosa" (:name (first results))))))

  (testing "case-insensitive search"
    (let [results (p/find-players sample-players {:name "neymar"})]
      (is (= 1 (count results)))))

  (testing "returns empty for unknown player"
    (let [results (p/find-players sample-players {:name "Unknown Player"})]
      (is (empty? results)))))

(deftest find-players-by-nationality-test
  (testing "finds all Brazilian players"
    (let [results (p/find-players sample-players {:nationality "Brazil"})]
      (is (= 6 (count results)))
      (is (every? #(= "Brazil" (:nationality %)) results))))

  (testing "case-insensitive nationality"
    (let [results (p/find-players sample-players {:nationality "brazil"})]
      (is (= 6 (count results))))))

(deftest find-players-by-club-test
  (testing "finds players at a specific club"
    (let [results (p/find-players sample-players {:club "Flamengo"})]
      (is (= 2 (count results)))
      (is (every? #(= "Flamengo" (:club %)) results))))

  (testing "partial club name match"
    (let [results (p/find-players sample-players {:club "Real"})]
      (is (= 2 (count results)))))

  (testing "returns empty for unknown club"
    (let [results (p/find-players sample-players {:club "Grêmio"})]
      (is (empty? results)))))

(deftest find-players-by-position-test
  (testing "finds players by position"
    (let [results (p/find-players sample-players {:position "LW"})]
      (is (= 3 (count results)))))

  (testing "finds goalkeepers"
    (let [results (p/find-players sample-players {:position "GK"})]
      (is (= 1 (count results)))))

  (testing "returns empty for unused position"
    (let [results (p/find-players sample-players {:position "CB"})]
      (is (empty? results)))))

(deftest find-players-combined-test
  (testing "finds Brazilian players at Flamengo"
    (let [results (p/find-players sample-players {:nationality "Brazil" :club "Flamengo"})]
      (is (= 2 (count results)))))

  (testing "finds top-rated by overall with limit"
    (let [results (p/find-players sample-players {:sort-by :overall :limit 3})]
      (is (= 3 (count results)))
      (is (= 94 (:overall (first results))))
      (is (= 93 (:overall (second results)))))))

(deftest top-players-by-club-test
  (testing "returns top players grouped by club"
    (let [grouped (p/top-players-by-club sample-players ["Flamengo" "Real Madrid"] 2)]
      (is (contains? grouped "Flamengo"))
      (is (contains? grouped "Real Madrid"))
      (is (<= (count (get grouped "Flamengo")) 2))
      (is (<= (count (get grouped "Real Madrid")) 2)))))
