(ns brazilian-soccer.tools-test
  "The MCP tool surface: schemas, argument handling and error messages.

  CONTEXT
  -------
  Tool descriptions and schemas are what an LLM sees before choosing a tool, so
  they are asserted as part of the contract.  Error paths matter as much as
  happy paths here: an ambiguous or unknown club must come back as a readable
  sentence listing alternatives, because that message is what the model reads."
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.fixtures :refer [test-db]]
            [brazilian-soccer.tools :as tools]))

(deftest catalogue-is-well-formed
  (testing "every tool is describable to a model"
    (doseq [t tools/tools]
      (is (re-matches #"[a-z][a-z0-9_]*" (:name t)) (str "snake_case name: " (:name t)))
      (is (> (count (:description t)) 40) (str (:name t) " needs a useful description"))
      (is (= "object" (get (:schema t) "type")) (str (:name t) " schema must be an object"))
      (is (map? (get (:schema t) "properties")))
      (is (fn? (:handler t)))))
  (testing "the catalogue covers every capability group in the specification"
    (is (every? (set (map :name tools/tools))
                ["search_matches" "head_to_head" "team_stats" "team_profile" "standings"
                 "competition_stats" "biggest_wins" "team_rankings" "list_finals"
                 "find_derbies" "search_players" "player_profile" "club_squad"
                 "list_teams" "dataset_info"])))
  (testing "tools/list serialises to JSON-friendly maps"
    (let [listing (tools/tool-list-json)]
      (is (= (count tools/tools) (count listing)))
      (is (every? #(and (get % "name") (get % "description") (get % "inputSchema")) listing)))))

(deftest arguments-accept-strings-and-numbers
  (let [db (test-db)]
    (testing "an MCP client may send a season as either 2019 or \"2019\""
      (is (= (tools/call-tool db "standings" {"competition" "brasileirao" "season" 2019})
             (tools/call-tool db "standings" {"competition" "brasileirao" "season" "2019"}))))
    (testing "competition aliases are accepted"
      (is (str/includes? (tools/call-tool db "competition_stats" {"competition" "Série A"})
                         "Brasileirão Série A"))
      (is (str/includes? (tools/call-tool db "competition_stats" {"competition" "libertadores"})
                         "Copa Libertadores")))))

(deftest helpful-errors
  (let [db (test-db)]
    (testing "an ambiguous club lists the candidates"
      (let [msg (try (tools/call-tool db "team_stats" {"team" "Atletico"}) (catch Exception e (.getMessage e)))]
        (is (str/includes? msg "Atlético Mineiro"))
        (is (str/includes? msg "Athletico Paranaense"))))
    (testing "an unknown club says so"
      (let [msg (try (tools/call-tool db "team_stats" {"team" "Nonexistent United"})
                     (catch Exception e (.getMessage e)))]
        (is (str/includes? msg "No club matching"))))
    (testing "an unknown competition lists the known ones"
      (let [msg (try (tools/call-tool db "standings" {"competition" "Premier League" "season" 2019})
                     (catch Exception e (.getMessage e)))]
        (is (str/includes? msg "Unknown competition"))
        (is (str/includes? msg "Copa do Brasil"))))
    (testing "a season with no data lists the seasons that do exist"
      (let [msg (try (tools/call-tool db "standings" {"competition" "brasileirao" "season" 1975})
                     (catch Exception e (.getMessage e)))]
        (is (str/includes? msg "Available seasons"))))
    (testing "a knockout competition cannot produce a league table"
      (let [msg (try (tools/call-tool db "standings" {"competition" "libertadores" "season" 2018})
                     (catch Exception e (.getMessage e)))]
        (is (str/includes? msg "knockout"))))
    (testing "an unknown tool is reported with the list of tools"
      (let [msg (try (tools/call-tool db "make_coffee" {}) (catch Exception e (.getMessage e)))]
        (is (str/includes? msg "Unknown tool"))))))

(deftest answers-follow-the-specified-format
  (let [db (test-db)]
    (testing "a match line carries date, teams, score and competition"
      (let [answer (tools/call-tool db "search_matches" {"team" "Flamengo" "opponent" "Fluminense"
                                                        "season" 2019})]
        (is (re-find #"\d{4}-\d{2}-\d{2}: .+ \d+-\d+ .+ \(Brasileirão Série A" answer))))
    (testing "a team record carries matches, results, goals and win rate"
      (let [answer (tools/call-tool db "team_stats" {"team" "Corinthians" "season" 2022
                                                    "competition" "brasileirao" "venue" "home"})]
        (is (str/includes? answer "Matches: 19"))
        (is (re-find #"Wins: \d+, Draws: \d+, Losses: \d+" answer))
        (is (re-find #"Win rate: \d+\.\d%" answer))))
    (testing "a standings table marks the champion and the relegation zone"
      (let [answer (tools/call-tool db "standings" {"competition" "brasileirao" "season" 2019})]
        (is (str/includes? answer "champion"))
        (is (str/includes? answer "relegation zone"))
        (is (str/includes? answer "Flamengo"))))
    (testing "player answers carry rating, position and club"
      (let [answer (tools/call-tool db "search_players" {"nationality" "Brazil" "limit" 3})]
        (is (re-find #"Overall: \d+, Potential: \d+, Position: \w+" answer))))
    (testing "dataset_info names every source file and license"
      (let [answer (tools/call-tool db "dataset_info" {})]
        (doseq [file ["Brasileirao_Matches.csv" "Brazilian_Cup_Matches.csv"
                      "Libertadores_Matches.csv" "BR-Football-Dataset.csv"
                      "novo_campeonato_brasileiro.csv" "fifa_data.csv"]]
          (is (str/includes? answer file)))
        (is (str/includes? answer "CC BY 4.0"))
        (is (str/includes? answer "CC0"))
        (is (str/includes? answer "Apache 2.0"))))))

(deftest every-tool-answers-with-defaults
  (testing "no tool throws on a reasonable minimal call"
    (let [db (test-db)
          calls {"search_matches" {"team" "Santos" "limit" 3}
                 "head_to_head"   {"team_a" "Grêmio" "team_b" "Internacional"}
                 "team_stats"     {"team" "Bahia"}
                 "team_profile"   {"team" "Vitória"}
                 "standings"      {"season" 2015}
                 "competition_stats" {}
                 "biggest_wins"   {}
                 "team_rankings"  {}
                 "list_finals"    {"competition" "libertadores"}
                 "find_derbies"   {"limit" 5}
                 "search_players" {"nationality" "Brazil" "limit" 2}
                 "player_profile" {"name" "Alisson"}
                 "club_squad"     {}
                 "list_teams"     {"query" "santa"}
                 "dataset_info"   {}}]
      (doseq [t tools/tools
              :let [args (get calls (:name t))]]
        (is (some? args) (str "no smoke-test arguments for " (:name t)))
        (let [answer (tools/call-tool db (:name t) args)]
          (is (string? answer))
          (is (> (count answer) 40) (str (:name t) " returned a suspiciously short answer")))))))
