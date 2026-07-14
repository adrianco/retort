(ns brazilian-soccer-mcp.normalization
  (:require [clojure.string :as str]))

;; Brazilian state abbreviations used as suffixes
(def state-abbrevs
  #{"AC" "AL" "AP" "AM" "BA" "CE" "DF" "ES" "GO" "MA" "MT" "MS"
    "MG" "PA" "PB" "PR" "PE" "PI" "RJ" "RN" "RS" "RO" "RR" "SC"
    "SP" "SE" "TO"})

;; Club names that include a state abbreviation as part of their official identity
(def state-is-part-of-name
  #{"Athletico-PR" "Atlético-MG" "Atlético-GO" "Atlético-BA"
    "América-MG" "América-RN" "América-PE" "América-RJ"
    "Atlético-AC" "Atlético-CE" "Atlético-ES"
    "Náutico-PE" "Ituano-SP"})

(defn normalize-team
  "Strips state suffix (e.g. -SP, -RJ) from a team name, unless the state is part of the club's official name."
  [team-name]
  (when team-name
    (let [trimmed (str/trim team-name)]
      (if (empty? trimmed)
        trimmed
        (if (contains? state-is-part-of-name trimmed)
          trimmed
          (let [parts (str/split trimmed #"-")
                last-part (last parts)]
            (if (and (> (count parts) 1)
                     (contains? state-abbrevs last-part))
              (str/trim (str/join "-" (butlast parts)))
              trimmed)))))))

(def canonical-names
  {"Sport Club Corinthians Paulista" "Corinthians"
   "Corinthians Paulista" "Corinthians"
   "Athletico-PR" "Athletico Paranaense"
   "Athletic Club Paranaense" "Athletico Paranaense"
   "Atlético-PR" "Athletico Paranaense"
   "São Paulo FC" "São Paulo"
   "Sao Paulo" "São Paulo"
   "Sport Recife" "Sport"
   "Sport Club do Recife" "Sport"
   "Atlético Mineiro" "Atlético-MG"
   "Atletico-MG" "Atlético-MG"
   "Atlético-GO" "Atlético Goianiense"
   "Fluminense FC" "Fluminense"
   "Santos FC" "Santos"
   "Grêmio FBPA" "Grêmio"
   "Internacional" "Internacional"
   "Vasco da Gama" "Vasco"
   "Clube de Regatas do Flamengo" "Flamengo"
   "Cruzeiro EC" "Cruzeiro"
   "Botafogo de Futebol e Regatas" "Botafogo"
   "Boavista Sport Club (antigo Esporte Clube Barreira)" "Boavista"})

(defn canonical-name
  "Returns the canonical (simplified) team name."
  [team-name]
  (when team-name
    (let [normalized (normalize-team team-name)]
      (or (get canonical-names team-name)
          (get canonical-names normalized)
          normalized))))

(defn team-matches?
  "Returns true if query-name matches team-name (case-insensitive, ignoring state suffix and partial matches)."
  [query-name team-name]
  (when (and query-name team-name)
    (let [q (str/lower-case (normalize-team query-name))
          t (str/lower-case (normalize-team team-name))
          qc (str/lower-case (canonical-name query-name))
          tc (str/lower-case (canonical-name team-name))]
      (or (= q t)
          (= qc tc)
          (str/includes? t q)
          (str/includes? q t)
          (str/includes? tc qc)
          (str/includes? qc tc)))))
