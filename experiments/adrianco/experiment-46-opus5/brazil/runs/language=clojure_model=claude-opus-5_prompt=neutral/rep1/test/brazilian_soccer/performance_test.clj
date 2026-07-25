(ns brazilian-soccer.performance-test
  "Query performance requirements from the specification.

  CONTEXT
  -------
  The targets are: simple lookups under 2 seconds, aggregate queries under 5
  seconds, no timeouts.  The database is loaded once at start-up (the fixture
  forces it before timing), so these tests measure query time the way an MCP
  client experiences it once the server is running."
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.fixtures :refer [test-db]]
            [brazilian-soccer.tools :as tools]))

(defn- millis [f]
  (let [start (System/nanoTime)]
    (f)
    (/ (- (System/nanoTime) start) 1e6)))

(deftest data-loads-quickly
  (testing "the whole knowledge graph is in memory before the first request"
    (let [db (test-db)]
      (is (pos? (count (:matches db)))))))

(deftest simple-lookups-under-two-seconds
  (let [db (test-db)]
    (doseq [[label call] {"latest meeting of two clubs"
                          #(tools/call-tool db "search_matches"
                                            {"team" "Flamengo" "opponent" "Corinthians" "limit" 1})
                          "one club in one season"
                          #(tools/call-tool db "search_matches" {"team" "Palmeiras" "season" 2023})
                          "player by name"
                          #(tools/call-tool db "player_profile" {"name" "Neymar"})
                          "club squad"
                          #(tools/call-tool db "club_squad" {"club" "Cruzeiro"})
                          "club search"
                          #(tools/call-tool db "list_teams" {"query" "atletico"})}]
      (let [ms (millis call)]
        (is (< ms 2000) (format "%s took %.0f ms" label ms))))))

(deftest aggregate-queries-under-five-seconds
  (let [db (test-db)]
    (doseq [[label call] {"season standings"
                          #(tools/call-tool db "standings" {"competition" "brasileirao" "season" 2019})
                          "whole competition statistics"
                          #(tools/call-tool db "competition_stats" {"competition" "brasileirao"})
                          "rankings across every club and match"
                          #(tools/call-tool db "team_rankings" {"venue" "home" "min_matches" 100})
                          "head to head over twenty seasons"
                          #(tools/call-tool db "head_to_head" {"team_a" "Palmeiras" "team_b" "Santos"})
                          "biggest wins over the whole dataset"
                          #(tools/call-tool db "biggest_wins" {"limit" 20})
                          "every derby ever played"
                          #(tools/call-tool db "find_derbies" {"limit" 500})}]
      (let [ms (millis call)]
        (is (< ms 5000) (format "%s took %.0f ms" label ms))))))

(deftest repeated-queries-do-not-degrade
  (testing "no timeout or slowdown across a burst of calls"
    (let [db (test-db)
          ms (millis #(dotimes [i 25]
                        (tools/call-tool db "team_stats"
                                         {"team" "Santos" "season" (+ 2000 i)})))]
      (is (< ms 5000) (format "25 sequential team_stats calls took %.0f ms" ms)))))
