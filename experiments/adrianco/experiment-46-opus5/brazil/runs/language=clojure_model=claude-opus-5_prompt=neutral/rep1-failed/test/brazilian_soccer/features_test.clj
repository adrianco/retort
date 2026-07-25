(ns brazilian-soccer.features-test
  "BDD scenarios for the five capability groups in the specification.

  CONTEXT
  -------
  These are the Given/When/Then scenarios the specification asks for, written
  with the DSL in brazilian-soccer.bdd.  They exercise the query layer directly
  (values, not prose) so a failure points at behaviour rather than wording; the
  text rendering is covered by tools_test and samples_test."
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest]]
            [brazilian-soccer.bdd :refer [feature scenario given when* then and*]]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.fixtures :refer [test-db]]
            [brazilian-soccer.query :as q]))

;; ---------------------------------------------------------------------------
;; 1. Match queries
;; ---------------------------------------------------------------------------

(feature "Match Queries"

  (scenario "Find matches between two teams"
    (given "the match data is loaded" [db (test-db)]
      (when* "I search for matches between Flamengo and Fluminense"
        [result (q/find-matches db {:team-id (q/team-id! db "Flamengo")
                                    :opponent-id (q/team-id! db "Fluminense")})]
        (then "I should receive a list of matches" (seq result))
        (and* "each match should have date, scores and a competition"
          (every? #(and (:date %) (:home-goals %) (:away-goals %) (:competition-name %)) result))
        (and* "every match involves both clubs"
          (every? #(= #{"flamengo|rj" "fluminense|rj"} (set [(:home-id %) (:away-id %)])) result))
        (and* "the Fla-Flu is recognised as a derby"
          (= "Fla-Flu" (:name (q/derby-of (first result))))))))

  (scenario "Find matches of one team in one season"
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask what Palmeiras played in 2023"
        [result (q/find-matches db {:team-id (q/team-id! db "Palmeiras") :season 2023})]
        (then "I receive matches from that season only" (every? #(= 2023 (:season %)) result))
        (and* "they include league and cup fixtures"
          (= #{:serie-a :copa-do-brasil} (set (map :competition result)))))))

  (scenario "Find the most recent meeting of two teams"
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask when Flamengo last played Corinthians"
        [result (q/find-matches db {:team-id (q/team-id! db "Flamengo")
                                    :opponent-id (q/team-id! db "Corinthians")
                                    :sort :date-desc :limit 1})]
        (then "I receive exactly one match" (= 1 (count result)))
        (and* "it is the latest one in the data"
          (= (:date (first result))
             (last (sort (map :date (q/find-matches db {:team-id "flamengo|rj"
                                                        :opponent-id "corinthians|sp"})))))))))

  (scenario "Filter matches by date range and competition"
    (given "the match data is loaded" [db (test-db)]
      (when* "I search the Libertadores between two dates"
        [result (q/find-matches db {:competition :libertadores
                                    :date-from "2019-01-01" :date-to "2019-12-31"})]
        (then "every match is inside the range"
          (every? #(<= (compare "2019-01-01" (:date %)) 0) result))
        (and* "every match belongs to the competition"
          (every? #(= :libertadores (:competition %)) result)))))

  (scenario "Find the finals of a knockout competition"
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask for the 2018 Copa Libertadores final"
        [result (:finals (q/finals db :libertadores 2018))]
        (then "I receive the two legs" (= 2 (count result)))
        (and* "they are the Boca Juniors vs River Plate final"
          (= #{"boca juniors|arg" "river plate|arg"}
             (set (mapcat (juxt :home-id :away-id) result))))))))

;; ---------------------------------------------------------------------------
;; 2. Team queries
;; ---------------------------------------------------------------------------

(feature "Team Queries"

  (scenario "Get team statistics for a season"
    (given "the match data is loaded" [db (test-db)]
      (when* "I request statistics for Palmeiras in season 2023"
        [result (q/team-summary db (q/team-id! db "Palmeiras")
                                {:season 2023 :competition :serie-a})]
        (then "I receive wins, losses, draws and goals"
          (every? #(number? (get-in result [:overall %]))
                  [:wins :losses :draws :goals-for :goals-against]))
        (and* "the record adds up to the matches played"
          (= (get-in result [:overall :matches])
             (+ (get-in result [:overall :wins])
                (get-in result [:overall :draws])
                (get-in result [:overall :losses]))))
        (and* "home and away splits add up to the total"
          (= (get-in result [:overall :matches])
             (+ (get-in result [:home :matches]) (get-in result [:away :matches])))))))

  (scenario "Home record of a club in one season"
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask for Corinthians' home record in the 2022 Brasileirão"
        [result (q/team-summary db (q/team-id! db "Corinthians")
                                {:season 2022 :competition :serie-a :venue :home})]
        (then "there are 19 home matches" (= 19 (get-in result [:overall :matches])))
        (and* "no away matches are included" (zero? (get-in result [:away :matches])))
        (and* "the win rate is reported as a fraction"
          (<= 0.0 (get-in result [:overall :win-rate]) 1.0)))))

  (scenario "Compare two clubs head-to-head"
    (given "the match data is loaded" [db (test-db)]
      (when* "I compare Palmeiras and Santos"
        [result (q/head-to-head db (q/team-id! db "Palmeiras") (q/team-id! db "Santos") {})]
        (then "the totals balance"
          (= (:played result)
             (+ (get-in result [:a-record :wins]) (get-in result [:b-record :wins])
                (:draws result))))
        (and* "goals scored by one side are goals conceded by the other"
          (= (get-in result [:a-record :goals-for]) (get-in result [:b-record :goals-against])))
        (and* "the meetings span more than one competition"
          (> (count (:by-competition result)) 1)))))

  (scenario "Rank clubs by home record"
    (given "the match data is loaded" [db (test-db)]
      (when* "I rank clubs by points per home match"
        [result (q/team-rankings db {:venue :home :metric :points-per-match
                                     :min-matches 100 :limit 5})]
        (then "I receive a ranked list" (= 5 (count (:rows result))))
        (and* "the list is ordered by the metric"
          (= (map :points-per-match (:rows result))
             (reverse (sort (map :points-per-match (:rows result))))))
        (and* "small samples are excluded"
          (every? #(>= (:matches %) 100) (:rows result))))))

  (scenario "Resolve a club name that matches several clubs"
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask for \"Atletico\""
        [result (q/resolve-team db "Atletico")]
        (then "the query is reported as ambiguous" (= :ambiguous (:status result)))
        (and* "Atlético Mineiro and Athletico Paranaense are offered"
          (let [ids (set (map :id (:candidates result)))]
            (and (ids "atletico|mg") (ids "atletico|pr"))))))
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask for a club that does not exist"
        [result (q/resolve-team db "Manchester United")]
        (then "the query is reported as not found" (= :not-found (:status result)))))))

;; ---------------------------------------------------------------------------
;; 3. Player queries
;; ---------------------------------------------------------------------------

(feature "Player Queries"

  (scenario "Find players by nationality"
    (given "the player data is loaded" [db (test-db)]
      (when* "I search for Brazilian players sorted by rating"
        [result (q/search-players db {:nationality "Brazil" :sort :overall :limit 5})]
        (then "there are hundreds of Brazilians in the dataset" (> (:total result) 500))
        (and* "the best rated is Neymar" (= "Neymar Jr" (:name (first (:players result)))))
        (and* "results are sorted by overall rating"
          (= (map :overall (:players result))
             (reverse (sort (map :overall (:players result))))))
        (and* "every player really is Brazilian"
          (every? #(= "Brazil" (:nationality %)) (:players result))))))

  (scenario "Find players by club and position"
    (given "the player data is loaded" [db (test-db)]
      (when* "I search for forwards at Fluminense"
        [result (q/search-players db {:club "Fluminense" :position-group :forward})]
        (then "I receive players" (pos? (:total result)))
        (and* "they all play for that club"
          (every? #(= "Fluminense" (:club %)) (:players result)))
        (and* "they are all forwards"
          (every? #(= :forward (data/position-group (:position %))) (:players result))))))

  (scenario "Look up one player"
    (given "the player data is loaded" [db (test-db)]
      (when* "I ask who Neymar is"
        [result (q/player-profile db "Neymar")]
        (then "I receive a profile" (some? result))
        (and* "with ratings and attributes"
          (and (= 92 (get-in result [:player :overall]))
               (seq (get-in result [:player :skills])))))))

  (scenario "Cross-file query: a club's squad and its match record"
    (given "both datasets are loaded" [db (test-db)]
      (when* "I ask for the Cruzeiro squad"
        [squad (q/club-squad db "Cruzeiro")]
        (then "the squad is found" (some? squad))
        (and* "it is linked to the club in the match data"
          (= "cruzeiro|mg" (:team-id squad)))
        (and* "the linked club has matches"
          (pos? (count (q/find-matches db {:team-id (:team-id squad)}))))
        (and* "an average rating is available" (pos? (:avg-overall squad))))))

  (scenario "A club that FIFA 19 does not license"
    (given "the player data is loaded" [db (test-db)]
      (when* "I search for players at Flamengo"
        [result (q/search-players db {:club "Flamengo"})]
        (then "no players are returned rather than wrong ones" (zero? (:total result)))))))

;; ---------------------------------------------------------------------------
;; 4. Competition queries
;; ---------------------------------------------------------------------------

(feature "Competition Queries"

  (scenario "Calculate a final league table from match results"
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask for the 2019 Brasileirão standings"
        [result (q/standings db :serie-a 2019)]
        (then "twenty clubs are ranked" (= 20 (count (:table result))))
        (and* "Flamengo are champions with 90 points"
          (= ["Flamengo" 90] ((juxt :team :points) (first (:table result)))))
        (and* "every club played 38 matches"
          (every? #(= 38 (:matches %)) (:table result)))
        (and* "positions are consecutive"
          (= (range 1 21) (map :position (:table result)))))))

  (scenario "Season coverage of a competition"
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask which seasons the Copa do Brasil covers"
        [result (q/seasons db :copa-do-brasil)]
        (then "the seasons are contiguous from 2012 to 2023"
          (= (range 2012 2024) (seq result))))))

  (scenario "Aggregate statistics for a competition"
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask for Brasileirão statistics"
        [result (q/competition-summary db :serie-a nil)]
        (then "the average goals per match is plausible"
          (< 2.0 (:goals-per-match result) 3.5))
        (and* "results partition the matches"
          (= (:matches result) (+ (:home-wins result) (:away-wins result) (:draws result))))
        (and* "home advantage is visible"
          (> (:home-win-rate result) (:away-win-rate result)))
        (and* "top scoring teams are listed" (= 10 (count (:top-scoring-teams result))))))))

;; ---------------------------------------------------------------------------
;; 5. Statistical analysis
;; ---------------------------------------------------------------------------

(feature "Statistical Analysis"

  (scenario "Biggest wins in the dataset"
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask for the biggest margins"
        [result (q/biggest-wins db {:limit 10})]
        (then "ten matches are returned" (= 10 (count result)))
        (and* "they are ordered by margin"
          (= (map q/margin result) (reverse (sort (map q/margin result)))))
        (and* "the largest margin is at least seven goals"
          (>= (q/margin (first result)) 7)))))

  (scenario "Biggest wins of one club"
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask for Santos' biggest wins in the Libertadores"
        [result (q/biggest-wins db {:team-id (q/team-id! db "Santos")
                                    :competition :libertadores :limit 5})]
        (then "every match is a Santos victory"
          (every? #(= :win (q/outcome "santos|sp" %)) result)))))

  (scenario "Compare two seasons"
    (given "the match data is loaded" [db (test-db)]
      (when* "I summarise 2018 and 2019"
        [a (q/competition-summary db :serie-a 2018)
         b (q/competition-summary db :serie-a 2019)]
        (then "both seasons have 380 matches"
          (= 380 (:matches a) (:matches b)))
        (and* "each has its own goals per match figure"
          (and (pos? (:goals-per-match a)) (pos? (:goals-per-match b)))))))

  (scenario "Home versus away performance of a club"
    (given "the match data is loaded" [db (test-db)]
      (when* "I look at Grêmio's home and away records"
        [result (q/team-summary db (q/team-id! db "Grêmio") {:competition :serie-a})]
        (then "home and away are reported separately"
          (and (pos? (get-in result [:home :matches])) (pos? (get-in result [:away :matches]))))
        (and* "the club wins more often at home"
          (> (get-in result [:home :win-rate]) (get-in result [:away :win-rate]))))))

  (scenario "Derby matches are identified"
    (given "the match data is loaded" [db (test-db)]
      (when* "I ask for derbies in 2023"
        [result (q/derbies db {:season 2023})]
        (then "derbies are found" (seq result))
        (and* "each is tagged with a rivalry name" (every? :derby result))
        (and* "the Fla-Flu is among them"
          (some #(= "Fla-Flu" (:derby %)) result))
        (and* "all are from 2023" (every? #(= 2023 (:season %)) result))))))

;; ---------------------------------------------------------------------------
;; Data quality guarantees called out by the specification
;; ---------------------------------------------------------------------------

(feature "Data Quality"

  (scenario "Team name variations resolve to one club"
    (given "the match data is loaded" [db (test-db)]
      (when* "I look up a club by each spelling used in the files"
        [ids (map #(q/team-id! db %) ["Flamengo" "Flamengo-RJ" "Flamengo - RJ" "flamengo"])]
        (then "they all resolve to the same club" (= 1 (count (distinct ids)))))))

  (scenario "Accented queries work"
    (given "the match data is loaded" [db (test-db)]
      (when* "I search with and without accents"
        [with    (q/team-id! db "São Paulo")
         without (q/team-id! db "Sao Paulo")]
        (then "both find the club" (= with without "sao paulo|sp"))
        (and* "the display name keeps its accents"
          (= "São Paulo" (:display (q/team db with)))))))

  (scenario "Matches without a score are kept but never counted"
    (given "the match data is loaded" [db (test-db)]
      (when* "I look at every match in the graph"
        [unplayed (remove :played? (:matches db))]
        (then "the unplayed fixtures are visible" (seq unplayed))
        (and* "they are excluded from team records"
          (let [m (first unplayed)
                id (:home-id m)
                r (q/record id [m])]
            (zero? (:matches r)))))))

  (scenario "Every club has a display name and a canonical id"
    (given "the match data is loaded" [db (test-db)]
      (when* "I inspect the club index"
        [teams (vals (:teams db))]
        (then "there are hundreds of clubs" (> (count teams) 300))
        (and* "each has a non-blank display name"
          (every? #(not (str/blank? (:display %))) teams))
        (and* "each id matches its base name"
          (every? #(str/starts-with? (:id %) (:base %)) teams))))))
