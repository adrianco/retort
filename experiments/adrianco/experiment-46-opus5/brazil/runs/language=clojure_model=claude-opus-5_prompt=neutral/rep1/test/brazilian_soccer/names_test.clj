(ns brazilian-soccer.names-test
  "Unit tests for team-name normalisation.

  CONTEXT
  -------
  The specification calls out three data quality hazards: name variations,
  multiple date formats and UTF-8 accents.  This namespace covers the first and
  the third; date parsing is covered in data_test."
  (:require [clojure.test :refer [deftest testing is]]
            [brazilian-soccer.names :as names]))

(defn- id-of [raw]
  (let [{:keys [base region]} (names/parse-team-name raw)]
    (names/team-id base region)))

(deftest accents-are-stripped-not-lost
  (testing "UTF-8 Portuguese text folds to a comparable form"
    (is (= "Sao Paulo" (names/strip-accents "São Paulo")))
    (is (= "Gremio" (names/strip-accents "Grêmio")))
    (is (= "Avai" (names/strip-accents "Avaí")))
    (is (= "Atletico Mineiro" (names/strip-accents "Atlético Mineiro")))
    (is (= "Fortaleza Esporte Clube" (names/strip-accents "Fortaleza Esporte Clube")))))

(deftest state-suffixes-are-recognised
  (testing "every spelling of a state suffix resolves to the same club"
    (is (= "flamengo|rj" (id-of "Flamengo-RJ") (id-of "Flamengo - RJ") (id-of "Flamengo")))
    (is (= "sao paulo|sp" (id-of "São Paulo") (id-of "Sao Paulo-SP") (id-of "São Paulo - SP")))
    (is (= "vasco da gama|rj" (id-of "Vasco") (id-of "Vasco da Gama-RJ") (id-of "Vasco Da Gama RJ")))))

(deftest ambiguous-bases-stay-apart
  (testing "clubs that share a base name are kept apart by their state"
    (is (= "atletico|mg" (id-of "Atlético-MG") (id-of "Atletico Mineiro") (id-of "Atlético Mineiro - MG")))
    (is (= "atletico|pr" (id-of "Athletico-PR") (id-of "Athletico") (id-of "Atletico Paranaense")))
    (is (= "atletico|go" (id-of "Atlético-GO") (id-of "Atletico Goianiense")))
    (is (not= (id-of "Atlético-MG") (id-of "Atlético-GO")))
    (is (not= (id-of "América - MG") (id-of "América - RN")))
    (is (not= (id-of "Bragantino - PA") (id-of "Red Bull Bragantino-SP")))))

(deftest club-decorations-are-dropped
  (testing "EC / FC / Esporte Clube and friends carry no identity"
    (is (= "bahia|ba" (id-of "EC Bahia") (id-of "Bahia - BA") (id-of "Bahia")))
    (is (= "juventude|rs" (id-of "EC Juventude") (id-of "Juventude - RS")))
    (is (= "fortaleza|ce" (id-of "Fortaleza EC") (id-of "Fortaleza FC") (id-of "Fortaleza - CE"))))
  (testing "curated aliases handle the names that rules cannot"
    (is (= "sport|pe" (id-of "Sport Club do Recife") (id-of "Sport Recife") (id-of "Sport - PE")))
    (is (= "nautico|pe" (id-of "Nautico Capibaribe") (id-of "Náutico - PE")))
    (is (= "ceara|ce" (id-of "Ceará Sporting Club") (id-of "Ceara") (id-of "Ceará - CE")))
    (is (= "america|mg" (id-of "América FC (Minas Gerais)") (id-of "América-MG")))
    (is (= "remo|pa" (id-of "Clube Do Remo") (id-of "Remo - PA")))))

(deftest foreign-clubs-keep-their-country
  (testing "Libertadores opponents are namespaced by country code"
    (is (= "nacional|uru" (id-of "Nacional (URU)") (id-of "Nacional-URU")))
    (is (= "guarani|par" (id-of "Guaraní (PAR)") (id-of "Guaraní-PAR")))
    (is (not= (id-of "Guaraní-PAR") (id-of "Guarani")))
    (is (= "river plate|arg" (id-of "River Plate")))
    (is (not= (id-of "River Plate") (id-of "River Plate-URU")))))

(deftest hyphenated-names-survive
  (testing "a hyphen that is not a state suffix is kept"
    (is (= "colo colo|chi" (id-of "Colo-Colo")))
    (is (= "ji-parana|ro" (id-of "Ji-paraná - RO")))))
