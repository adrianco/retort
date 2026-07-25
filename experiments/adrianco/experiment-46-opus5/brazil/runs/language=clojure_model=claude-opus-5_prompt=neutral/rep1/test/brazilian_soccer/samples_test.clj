(ns brazilian-soccer.samples-test
  "Acceptance test for the sample questions in the specification.

  CONTEXT
  -------
  The success criteria require that at least 20 sample questions can be
  answered.  resources/sample_questions.edn holds the questions, the tool call
  an LLM would make for each and the substrings the answer must contain; this
  test runs every one of them through the tool layer.  The same file drives
  `clojure -M:cli demo`, so the demo and the acceptance test can never drift."
  (:require [clojure.string :as str]
            [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.cli :as cli]
            [brazilian-soccer.fixtures :refer [test-db]]
            [brazilian-soccer.tools :as tools]))

(deftest enough-sample-questions
  (let [questions (cli/sample-questions)]
    (is (>= (count questions) 20)
        "the specification requires at least 20 answerable sample questions")
    (testing "all five capability groups are represented"
      (is (= #{"Match queries" "Team queries" "Player queries"
               "Competition queries" "Statistical analysis"}
             (set (map :category questions)))))
    (testing "every question names a tool that exists"
      (is (every? #(contains? tools/tools-by-name (:tool %)) questions)))))

(deftest every-sample-question-is-answered
  (let [db (test-db)]
    (doseq [{:keys [question tool args expect]} (cli/sample-questions)]
      (testing question
        (let [answer (try (tools/call-tool db tool args)
                          (catch Exception e (str "EXCEPTION: " (.getMessage e))))]
          (is (string? answer))
          (is (not (str/starts-with? answer "EXCEPTION:")) answer)
          (is (> (count answer) 40) (str "answer too short for: " question))
          (doseq [substring expect]
            (is (str/includes? answer substring)
                (str "expected \"" substring "\" in the answer to: " question))))))))

(deftest cross-file-questions
  (testing "a question that needs both the player data and the match data"
    (let [db (test-db)
          answer (tools/call-tool db "club_squad" {"club" "Atlético Mineiro"})]
      (is (str/includes? answer "Average overall rating"))
      (is (str/includes? answer "in the match data")
          "the squad must be linked to the club that plays the matches")))
  (testing "a player profile reaches through to the club's match record"
    (let [db (test-db)
          answer (tools/call-tool db "player_profile" {"name" "Ronaldo Cabrais"})]
      (is (str/includes? answer "Grêmio"))
      (is (str/includes? answer "Club in the match data")))))
