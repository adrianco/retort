;; =============================================================================
;; Tests for brsoccer.query.
;;
;; Two layers:
;;   * Deterministic logic tests against a small hand-built synthetic graph
;;     (standings, head-to-head, records, stats) -- exact expected numbers.
;;   * Smoke/coverage tests against the real bundled datasets (loaded once)
;;     proving every CSV is queryable and cross-file queries work.
;; =============================================================================
(ns brsoccer.query-test
  (:require [clojure.test :refer [deftest is testing use-fixtures]]
            [brsoccer.data :as data]
            [brsoccer.normalize :as n]
            [brsoccer.query :as q]))

;; ---------------------------------------------------------------------------
;; Synthetic graph: a tiny 3-team single round-robin we can verify by hand.
;; ---------------------------------------------------------------------------

(def ^:private date-counter (atom 0))
(defn- mk [home away hg ag]
  {:competition "Test League" :season 2020
   :date (format "2020-01-%02d" (swap! date-counter inc))
   :home home :away away :home-key (n/team-key home)
   :away-key (n/team-key away)
   :home-goal hg :away-goal ag
   :result (cond (> hg ag) :home (< hg ag) :away :else :draw)})

(def synthetic
  (let [ms [(mk "Alpha" "Beta" 2 0)    ; Alpha W, Beta L
            (mk "Beta" "Gamma" 1 1)    ; draw
            (mk "Gamma" "Alpha" 0 3)   ; Alpha W, Gamma L
            (mk "Alpha" "Gamma" 1 1)]  ; draw  (Alpha vs Gamma twice)
        teams (#'brsoccer.data/build-teams ms)
        by-team (reduce (fn [a m]
                          (-> a (update (:home-key m) (fnil conj []) m)
                                (update (:away-key m) (fnil conj []) m)))
                        {} ms)]
    {:matches ms :teams teams :by-team by-team :players []}))

(deftest standings-are-correct
  (let [rows (q/standings synthetic {:competition "Test" :season 2020})
        by-team (into {} (map (juxt :team identity) rows))]
    (testing "Alpha: 2W 1D 0L => 7 pts, leads the table"
      (is (= 1 (:position (by-team "Alpha"))))
      (is (= 7 (:points (by-team "Alpha"))))
      (is (= 2 (:wins (by-team "Alpha"))))
      (is (= 1 (:draws (by-team "Alpha"))))
      (is (= 6 (:goals-for (by-team "Alpha"))))
      (is (= 1 (:goals-against (by-team "Alpha")))))
    (testing "Beta: 0W 1D 1L => 1 pt"
      (is (= 1 (:points (by-team "Beta")))))
    (testing "Gamma: 0W 2D 1L => 2 pts"
      (is (= 2 (:points (by-team "Gamma")))))))

(deftest team-record-and-venue
  (let [all  (q/team-record synthetic {:team "Alpha"})
        home (q/team-record synthetic {:team "Alpha" :venue :home})]
    (is (= 3 (:matches all)))
    (is (= 2 (:wins all)))
    (is (= 7 (:points all)))
    (is (= 66.7 (:win-rate all)))
    (testing "venue filter keeps only Alpha's home games"
      (is (= 2 (:matches home))))))   ; Alpha was home vs Beta and vs Gamma

(deftest head-to-head-counts
  (let [h (q/head-to-head synthetic {:team-a "Alpha" :team-b "Gamma"})]
    (is (= 2 (:total h)))
    (is (= 1 (:a-wins h)))    ; Gamma 0-3 Alpha
    (is (= 0 (:b-wins h)))
    (is (= 1 (:draws h)))     ; Alpha 1-1 Gamma
    (is (= 4 (:a-goals h)))
    (is (= 1 (:b-goals h)))))

(deftest summary-stats-math
  (let [s (q/summary-stats synthetic {})]
    (is (= 4 (:matches s)))
    ;; 2-0, 1-1, 0-3, 1-1 => 9 goals across 4 matches
    (is (= 9 (:total-goals s)))
    (is (= 2.25 (:avg-goals s)))
    (is (= 1 (:home-wins s)))  ; only Alpha 2-0 Beta is a home win
    (is (= 2 (:draws s)))))

;; ---------------------------------------------------------------------------
;; Real-dataset coverage. Loaded once via fixture; cached in brsoccer.data.
;; ---------------------------------------------------------------------------

(use-fixtures :once (fn [t] (data/reset-cache!) (t)))

(deftest all-csvs-loaded
  (let [g (data/graph)
        sources (set (map :source (:matches g)))]
    (testing "every match dataset contributes rows"
      (is (contains? sources "Brasileirao_Matches"))
      (is (contains? sources "Brazilian_Cup_Matches"))
      (is (contains? sources "Libertadores_Matches"))
      (is (contains? sources "BR-Football-Dataset"))
      (is (contains? sources "novo_campeonato")))
    (testing "players dataset loaded"
      (is (> (count (:players g)) 18000)))
    (testing "graph has a healthy number of matches and teams"
      (is (> (count (:matches g)) 15000))
      (is (> (count (:teams g)) 100)))))

(deftest name-variation-matching-real-data
  (let [g (data/graph)]
    (testing "team resolves regardless of suffix/accents"
      (is (= (q/resolve-team g "Palmeiras") (q/resolve-team g "Palmeiras-SP")))
      (is (some? (q/resolve-team g "São Paulo")))
      (is (some? (q/resolve-team g "Flamengo"))))))

(deftest find-matches-real-data
  (let [g (data/graph)
        flamengo (q/find-matches g {:team "Flamengo" :limit 5})
        derby    (q/find-matches g {:team "Flamengo" :opponent "Fluminense"})]
    (is (= 5 (count flamengo)))
    (testing "results sorted most-recent first"
      (is (>= 0 (compare (:date (second flamengo)) (:date (first flamengo))))))
    (testing "Fla-Flu derby produces only matches between the two clubs"
      (is (pos? (count derby)))
      (let [fk (q/resolve-team g "Flamengo") uk (q/resolve-team g "Fluminense")]
        (is (every? (fn [m] (= #{fk uk} #{(:home-key m) (:away-key m)})) derby))))))

(deftest player-queries-real-data
  (let [g (data/graph)
        brazilians (q/search-players g {:nationality "Brazil"})
        top (q/search-players g {:nationality "Brazil" :limit 3})]
    (is (> (count brazilians) 500))
    (testing "sorted by overall descending"
      (is (apply >= (map :overall top))))
    (testing "every Brazilian result is actually Brazilian"
      (is (every? #(= "Brazil" (:nationality %)) brazilians)))))

(deftest brasileirao-2019-matches-history
  (testing "deduped, name-normalized 2019 Série A reproduces the real table"
    (let [g (data/graph)
          table (q/standings g {:competition "Brasileirão Série A" :season 2019})
          season (q/find-matches g {:competition "Brasileirão Série A" :season 2019})
          champ (first table)]
      (is (= 380 (count season)))                ; 20-team double round-robin
      (is (= 20 (count table)))
      (is (= "Flamengo" (:team champ)))           ; 2019 champions
      (is (= 90 (:points champ)))                 ; with 90 points
      (is (= 28 (:wins champ))))))

(deftest cross-file-query
  (testing "competition standings (match files) + player roster (FIFA file) both answerable"
    (let [g (data/graph)
          table (q/standings g {:competition "Brasileirão Série A" :season 2019})
          champ (:team (first table))
          roster (q/search-players g {:club champ})]
      (is (seq table))
      (is (some? champ))
      ;; roster may be empty if the FIFA snapshot predates the club name, but the
      ;; query must run without error and return a (possibly empty) sequence.
      (is (sequential? roster)))))
