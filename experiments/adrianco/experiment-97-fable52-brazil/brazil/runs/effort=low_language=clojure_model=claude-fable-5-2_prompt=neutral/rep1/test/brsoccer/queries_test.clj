(ns brsoccer.queries-test
  "Feature scenarios from the specification, exercised through the MCP tool handlers."
  (:require [brsoccer.data :as data]
            [brsoccer.queries :as q]
            [brsoccer.tools :as tools]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]))

(defn- run [tool args]
  (tools/call (data/db) tool args))

(defn- ok [tool args]
  (let [{:keys [text error?]} (run tool args)]
    (is (not error?) (str tool " " args " -> " text))
    text))

;; ---------------------------------------------------------------- Match queries

(deftest find-matches-between-two-teams
  (testing "Given the match data is loaded"
    (let [db (data/db)]
      (testing "When I search for matches between \"Flamengo\" and \"Fluminense\""
        (let [ms (q/find-matches db {:team (q/team! db "Flamengo") :opponent (q/team! db "Fluminense")})]
          (testing "Then I should receive a list of matches"
            (is (< 30 (count ms))))
          (testing "And each match should have date, scores, and competition"
            (is (every? #(and (:date %) (integer? (:hg %)) (integer? (:ag %)) (:competition %)) ms)))
          (testing "And every match involves exactly those two clubs"
            (is (every? #(= #{"flamengo" "fluminense"} (hash-set (:home %) (:away %))) ms)))
          (testing "And they are ordered newest first"
            (is (= (map :date ms) (reverse (sort (map :date ms))))))))
      (testing "When I ask the tool the same question"
        (let [text (ok "search_matches" {"team" "Flamengo" "opponent" "Fluminense" "limit" 5})]
          (testing "Then the answer is formatted with a derby title, match lines and a tally"
            (is (str/includes? text "Flamengo vs Fluminense (Fla-Flu derby)"))
            (is (re-find #"- \d{4}-\d{2}-\d{2}: \S+ \d+-\d+ \S+ \(" text))
            (is (re-find #"more matches in dataset" text))
            (is (re-find #"Head-to-head in dataset: Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws" text))))))))

(deftest match-filters
  (let [db (data/db)]
    (testing "When I filter by team and season"
      (let [ms (q/find-matches db {:team "palmeiras" :season 2023})]
        (is (seq ms))
        (is (every? #(= 2023 (:season %)) ms))))
    (testing "When I filter by venue"
      (is (every? #(= "palmeiras" (:home %)) (q/find-matches db {:team "palmeiras" :venue :home})))
      (is (every? #(= "palmeiras" (:away %)) (q/find-matches db {:team "palmeiras" :venue :away}))))
    (testing "When I filter by date range (bounds inclusive)"
      (let [ms (q/find-matches db {:from "2019-11-23" :to "2019-11-23"})]
        (is (seq ms))
        (is (every? #(= "2019-11-23" (:date %)) ms))))
    (testing "When I filter by competition"
      (doseq [c (keys data/competitions)]
        (is (seq (q/find-matches db {:competition c})) (str c))))
    (testing "When I ask for Copa do Brasil finals"
      (let [ms (q/find-matches db {:competition :copa-do-brasil :stage "final"})]
        (is (= 18 (count ms)))
        (is (= (set (range 2012 2021)) (set (map :season ms))))))
    (testing "When Brazilian-format dates are given to the tool"
      (is (str/includes? (ok "search_matches" {"date_from" "23/11/2019" "date_to" "23/11/2019"
                                               "competition" "Libertadores"})
                         "2019-11-23: Flamengo 2-1 River Plate")))))

;; ----------------------------------------------------------------- Team queries

(deftest team-statistics
  (testing "Given the match data is loaded"
    (testing "When I request statistics for \"Palmeiras\" in season \"2023\""
      (let [db (data/db)
            r  (q/record (q/find-matches db {:team "palmeiras" :season 2023}) "palmeiras" :all)
            text (ok "team_stats" {"team" "Palmeiras" "season" "2023"})]
        (testing "Then I should receive wins, losses, draws, and goals"
          (is (pos? (:p r)))
          (is (= (:p r) (+ (:w r) (:d r) (:l r))))
          (is (str/includes? text (str "Wins: " (:w r) ", Draws: " (:d r) ", Losses: " (:l r))))
          (is (str/includes? text (str "Goals For: " (:gf r) ", Goals Against: " (:ga r))))
          (is (str/includes? text "Win rate: ")))))
    (testing "When I ask for Corinthians' home record in the 2022 Brasileirão"
      (let [text (ok "team_stats" {"team" "Corinthians" "season" 2022 "venue" "home"
                                   "competition" "Brasileirão"})]
        (is (str/starts-with? text "Corinthians home record (2022 Brasileirão Série A):"))
        (is (str/includes? text "- Matches: 19"))))
    (testing "home and away records add up to the overall record"
      (let [db (data/db)
            ms (q/find-matches db {:team "santos" :competition :serie-a})
            [a h w] (map #(q/record ms "santos" %) [:all :home :away])]
        (doseq [k [:p :w :d :l :gf :ga :pts]]
          (is (= (k a) (+ (k h) (k w))) (str k)))))))

(deftest head-to-head-comparison
  (testing "When I compare Palmeiras and Santos"
    (let [db (data/db)
          {:keys [matches a-wins b-wins draws a-goals b-goals]} (q/head-to-head db "palmeiras" "santos" {})
          rev (q/head-to-head db "santos" "palmeiras" {})]
      (testing "Then wins, draws and losses account for every match"
        (is (= (count matches) (+ a-wins b-wins draws))))
      (testing "And the comparison is symmetric"
        (is (= [a-wins b-wins draws a-goals b-goals]
               [(:b-wins rev) (:a-wins rev) (:draws rev) (:b-goals rev) (:a-goals rev)])))
      (testing "And the tool reports it"
        (let [text (ok "head_to_head" {"team_a" "Palmeiras" "team_b" "Santos"})]
          (is (str/includes? text (str "- Palmeiras wins: " a-wins)))
          (is (str/includes? text (str "- Santos wins: " b-wins)))
          (is (str/includes? text "Most recent:")))))))

;; ---------------------------------------------------------- Competition queries

(deftest standings-are-calculated-from-results
  (testing "When I ask who won the 2019 Brasileirão"
    (let [db   (data/db)
          rows (q/standings db :serie-a 2019)
          text (ok "standings" {"competition" "Brasileirão" "season" 2019})]
      (testing "Then Flamengo are champions with 90 points"
        (is (= 20 (count rows)))
        (is (= {:team "flamengo" :pts 90 :w 28 :d 6 :l 4}
               (select-keys (first rows) [:team :pts :w :d :l])))
        (is (str/includes? text "1. Flamengo - 90 pts (28W, 6D, 4L)"))
        (is (re-find #"1\. Flamengo.* - Champion" text)))
      (testing "And equal points are split on wins (Santos above Palmeiras)"
        (is (= ["santos" "palmeiras"] (map :team (subvec rows 1 3))))
        (is (= [74 74] (map :pts (subvec rows 1 3)))))
      (testing "And the bottom four are relegated"
        (is (= #{"cruzeiro" "csa" "chapecoense" "avai"} (set (map :team (subvec rows 16)))))
        (is (= 4 (count (re-seq #"Relegated" text)))))))
  (testing "When I ask which teams were relegated in 2020"
    (let [text (ok "standings" {"season" 2020})]
      (doseq [t ["Vasco da Gama" "Goiás" "Coritiba" "Botafogo"]]
        (is (re-find (re-pattern (str t ".* - Relegated")) text) t))))
  (testing "points in a table always equal 3*wins + draws and goals balance"
    (let [rows (q/standings (data/db) :serie-a 2015)]
      (is (every? #(= (:pts %) (+ (* 3 (:w %)) (:d %))) rows))
      (is (= (reduce + (map :gf rows)) (reduce + (map :ga rows))))))
  (testing "an incomplete season gets no champion label"
    (is (not (str/includes? (ok "standings" {"season" 2023}) "Champion"))))
  (testing "a cup is refused with a pointer to the right tool"
    (is (:error? (run "standings" {"competition" "Libertadores" "season" 2019})))))

(deftest knockout-brackets
  (testing "When I ask for the 2018 Copa Libertadores bracket"
    (let [text (ok "competition_bracket" {"competition" "Copa Libertadores" "season" 2018})]
      (doseq [s ["Round of 16:" "Quarterfinals:" "Semifinals:" "Final:"]]
        (is (str/includes? text s)))
      (is (str/includes? text "Champion: River Plate"))))
  (testing "the 2019 Libertadores and 2020 Copa do Brasil champions are derived"
    (is (str/includes? (ok "competition_bracket" {"competition" "libertadores" "season" 2019})
                       "Champion: Flamengo"))
    (is (str/includes? (ok "competition_bracket" {"competition" "Copa do Brasil" "season" "2020"})
                       "Champion: Palmeiras"))))

;; --------------------------------------------------------------- Player queries

(deftest player-search
  (let [db (data/db)]
    (testing "When I search for Brazilian players"
      (let [{:keys [players]} (q/find-players db {:nationality "Brazil"})]
        (testing "Then all 827 are found, best first"
          (is (= 827 (count players)))
          (is (every? #(= "Brazil" (:nationality %)) players))
          (is (= "Neymar Jr" (:name (first players))))
          (is (apply >= (map :overall players))))))
    (testing "When I search by name, ignoring accents and case"
      (is (= "Neymar Jr" (:name (first (:players (q/find-players db {:name "neymar"}))))))
      (is (some #(= "Grêmio" (:club %)) (:players (q/find-players db {:club "gremio"})))))
    (testing "When I filter by club using the match-data spelling"
      (let [{:keys [players]} (q/find-players db {:club "Atlético-MG"})]
        (is (seq players))
        (is (every? #(= "Atlético Mineiro" (:club %)) players))))
    (testing "When I filter by position group and club"
      (let [{:keys [players]} (q/find-players db {:club "Santos" :position "forwards"})]
        (is (seq players))
        (is (every? #(= "Santos" (:club %)) players))
        (is (every? (q/position-groups "forward") (map :position players)))))
    (testing "When I filter by rating and sort by age"
      (let [{:keys [players]} (q/find-players db {:nationality "Brazil" :min-overall 85 :sort "age"})]
        (is (every? #(>= (:overall %) 85) players))
        (is (apply <= (map :age players)))))
    (testing "When nothing matches every word, partial matches are flagged as approximate"
      (let [{:keys [players approximate?]} (q/find-players db {:name "Gabriel Barbosa"})]
        (is approximate?)
        (is (seq players))))
    (testing "the tool output follows the specified format"
      (is (str/includes? (ok "search_players" {"nationality" "Brazil" "limit" 3})
                         "1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain")))
    (testing "a club missing from the FIFA file is explained, not an error"
      (is (str/includes? (ok "search_players" {"club" "Flamengo"}) "No players found")))
    (testing "an unknown position is an error"
      (is (:error? (run "search_players" {"position" "wizard"}))))))

(deftest brazilian-clubs-in-fifa-data
  (let [rows (q/club-summary (data/db) "Brazil")]
    (is (= 15 (count rows)))
    (is (some #(= "Santos" (:club %)) rows))
    (is (apply >= (map :avg rows)))))

;; ---------------------------------------------------------- Statistical analysis

(deftest aggregate-statistics
  (let [db (data/db)]
    (testing "When I ask for the average goals per match in the Brasileirão"
      (let [s (q/summary (q/find-matches db {:competition :serie-a}))]
        (is (< 2.0 (:avg-goals s) 3.0))
        (is (= (:matches s) (+ (:home-wins s) (:draws s) (:away-wins s))))
        (is (> (:home-win-rate s) (:away-win-rate s)))
        (is (str/includes? (ok "match_statistics" {"competition" "Brasileirão"})
                           (format "Average goals per match: %.2f" (:avg-goals s))))))
    (testing "When I ask for the biggest wins"
      (let [ms (q/biggest-wins (:matches db))
            margins (map #(abs (- (:hg %) (:ag %))) ms)]
        (is (apply >= margins))
        (is (<= 7 (first margins)))
        (is (str/starts-with? (ok "biggest_wins" {"limit" 5}) "Biggest victories"))))
    (testing "When I ask which team has the best away record"
      (let [rows (q/rankings (q/find-matches db {:competition :serie-a}) :away "win_rate" 100)]
        (is (apply >= (map :win-rate rows)))
        (is (every? #(>= (:p %) 100) rows))))
    (testing "When I ask which team scored the most goals in Serie A 2019"
      (is (str/includes? (ok "team_rankings" {"metric" "goals_for" "competition" "Serie A"
                                              "season" 2019 "limit" 1})
                         "1. Flamengo")))
    (testing "goals_against ranks the tightest defence first"
      (let [rows (q/rankings (q/find-matches db {:competition :serie-a :season 2019}) :all "goals_against" 1)]
        (is (apply <= (map :ga rows)))))))

(deftest derbies
  (let [text (ok "find_derbies" {"season" 2023})]
    (is (str/includes? text "[Fla-Flu]"))
    (is (str/includes? text "By rivalry:"))))

;; -------------------------------------------------------------- Input handling

(deftest bad-input-is-reported-not-thrown
  (doseq [[tool args] [["team_stats" {"team" "Xyzzy United"}]
                       ["team_stats" {}]
                       ["search_matches" {"competition" "Premier League"}]
                       ["search_matches" {"season" "twenty"}]
                       ["search_matches" {"date_from" "yesterday"}]
                       ["search_matches" {"opponent" "Santos"}]
                       ["search_matches" {"team" "Santos" "venue" "moon"}]
                       ["head_to_head" {"team_a" "Santos" "team_b" "Santos-SP"}]
                       ["team_rankings" {"metric" "vibes"}]
                       ["compare_seasons" {"seasons" []}]
                       ["no_such_tool" {}]]]
    (let [{:keys [error? text]} (run tool args)]
      (is error? (str tool " " args))
      (is (not (str/blank? text)))))
  (testing "no matches is an answer, not an error"
    (is (str/includes? (ok "search_matches" {"team" "Flamengo" "season" 1950}) "No matches found")))
  (testing "limits are clamped rather than rejected"
    (is (string? (ok "search_matches" {"team" "Flamengo" "limit" -5})))
    (is (string? (ok "search_matches" {"team" "Flamengo" "limit" 100000})))))

;; ---------------------------------------------- Sample questions and performance

(def sample-questions
  [["Show me all Flamengo vs Fluminense matches" "search_matches" {"team" "Flamengo" "opponent" "Fluminense"}]
   ["What matches did Palmeiras play in 2023?" "search_matches" {"team" "Palmeiras" "season" 2023}]
   ["Find all Copa do Brasil finals" "search_matches" {"competition" "Copa do Brasil" "stage" "final"}]
   ["What is Corinthians' home record in 2022?" "team_stats" {"team" "Corinthians" "season" 2022 "venue" "home"}]
   ["Which team scored the most goals in Serie A 2023?" "team_rankings" {"metric" "goals_for" "competition" "Serie A" "season" 2023}]
   ["Compare Palmeiras and Santos head-to-head" "head_to_head" {"team_a" "Palmeiras" "team_b" "Santos"}]
   ["Find all Brazilian players in the dataset" "search_players" {"nationality" "Brazil"}]
   ["Who are the highest-rated players at Grêmio?" "search_players" {"club" "Grêmio" "limit" 5}]
   ["Show me all forwards from Santos" "search_players" {"club" "Santos" "position" "forward"}]
   ["Who won the 2019 Brasileirão?" "standings" {"season" 2019}]
   ["Show the 2018 Copa Libertadores bracket" "competition_bracket" {"competition" "Libertadores" "season" 2018}]
   ["Which teams were relegated in 2020?" "standings" {"season" 2020}]
   ["What's the average goals per match in the Brasileirão?" "match_statistics" {"competition" "Brasileirão"}]
   ["Which team has the best away record?" "team_rankings" {"venue" "away" "competition" "Serie A"}]
   ["Show me the biggest wins in the dataset" "biggest_wins" {}]
   ["When did Flamengo last play Corinthians?" "search_matches" {"team" "Flamengo" "opponent" "Corinthians" "limit" 1}]
   ["Who is Neymar?" "player_details" {"name" "Neymar"}]
   ["Which players play for Cruzeiro?" "search_players" {"club" "Cruzeiro"}]
   ["Show me all derbies in 2023" "find_derbies" {"season" 2023}]
   ["What competitions has Palmeiras played in?" "team_overview" {"team" "Palmeiras"}]
   ["Which team has the best home record?" "team_rankings" {"venue" "home"}]
   ["Who are the top Brazilian players?" "search_players" {"nationality" "Brazil" "limit" 10}]
   ["Compare the 2018 and 2019 seasons" "compare_seasons" {"seasons" [2018 2019]}]
   ["How has Santos done season by season?" "team_season_trend" {"team" "Santos"}]
   ["Brazilian players at Brazilian clubs" "brazilian_club_players" {"nationality" "Brazil"}]
   ["Which teams are called Atlético?" "list_teams" {"query" "atlético"}]
   ["What data do you have?" "dataset_info" {}]])

(deftest sample-questions-are-answered-quickly
  (testing "Given the data is loaded"
    (data/db)
    (is (<= 20 (count sample-questions)))
    (doseq [[question tool args] sample-questions]
      (testing (str "When asked: " question)
        (let [start (System/nanoTime)
              {:keys [text error?]} (run tool args)
              ms (/ (- (System/nanoTime) start) 1e6)]
          (testing "Then a non-empty, non-error answer comes back"
            (is (not error?) text)
            (is (< 40 (count text)))
            (is (not (re-find #"(?i)no .* found|unknown" text)) text))
          (testing "And within the 2 second budget"
            (is (< ms 2000.0) (str ms " ms"))))))))

(deftest cross-file-query
  (testing "team overview joins match files with the FIFA player file"
    (let [text (ok "team_overview" {"team" "Sport Recife"})]
      (is (str/includes? text "Brasileirão Série A"))
      (is (str/includes? text "Copa do Brasil"))
      (is (str/includes? text "club listed as \"Sport Club do Recife\"")))))

(deftest cold-load-performance
  (testing "building the whole database from CSV stays well inside the aggregate budget"
    (let [start (System/nanoTime)
          db (data/build-db (data/data-dir))]
      (is (< (/ (- (System/nanoTime) start) 1e9) 5.0))
      (is (= (count (:matches db)) (count (:matches (data/db))))))))
