(ns brazilian-soccer-mcp.normalize
  (:require [clojure.string :as str])
  (:import [java.text Normalizer Normalizer$Form]))

(defn strip-accents [s]
  (-> s
      (Normalizer/normalize Normalizer$Form/NFD)
      (str/replace #"\p{InCombiningDiacriticalMarks}" "")))

(defn normalize-team
  "Normalize team name for comparison: strip state codes, accents, lowercase."
  [name]
  (when (and name (seq name))
    (-> name
        str/trim
        ;; Remove parenthetical notes like "(antigo Esporte Clube Barreira)"
        (str/replace #"\s*\([^)]*\)\s*" " ")
        ;; Remove " - SP" or "- SP" state codes at end
        (str/replace #"\s*-\s*[A-Z]{2}$" "")
        ;; Remove "-SP" style (no space) at end
        (str/replace #"-[A-Z]{2}$" "")
        str/trim
        str/lower-case
        strip-accents
        (str/replace #"\s+" " ")
        str/trim)))

(defn team-matches?
  "Returns true if team-name matches the query (case-insensitive, accent-insensitive, partial match)."
  [team-name query]
  (when (and team-name query (seq team-name) (seq query))
    (let [norm-team (normalize-team team-name)
          norm-query (normalize-team query)]
      (when (and norm-team norm-query (seq norm-team) (seq norm-query))
        (or (= norm-team norm-query)
            (str/includes? norm-team norm-query)
            (str/includes? norm-query norm-team))))))

(defn parse-date
  "Parse date from various formats to ISO YYYY-MM-DD string."
  [s]
  (when (and s (seq (str/trim s)))
    (let [s (str/trim s)]
      (cond
        (re-matches #"\d{4}-\d{2}-\d{2}.*" s)
        (subs s 0 10)

        :else
        (when-let [[_ d m y] (re-matches #"(\d{1,2})/(\d{1,2})/(\d{4})" s)]
          (format "%s-%02d-%02d" y (Integer/parseInt m) (Integer/parseInt d)))))))

(defn parse-int [s]
  (when (and s (seq (str/trim (str s))))
    (try (Integer/parseInt (str/trim (str s)))
         (catch NumberFormatException _ nil))))

(defn parse-double-str [s]
  (when (and s (seq (str/trim (str s))))
    (try (Double/parseDouble (str/trim (str s)))
         (catch NumberFormatException _ nil))))

(defn extract-year [date-str]
  (when (and date-str (>= (count date-str) 4))
    (parse-int (subs date-str 0 4))))

(defn competition-label [comp-key]
  (case comp-key
    :brasileirao "Brasileirão Serie A"
    :brasileirao-historico "Brasileirão Serie A"
    :copa-brasil "Copa do Brasil"
    :libertadores "Copa Libertadores"
    :copa-do-brasil "Copa do Brasil"
    :copa-libertadores "Copa Libertadores"
    :brasileirao-serie-a "Brasileirão Serie A"
    (str/replace (name comp-key) #"-" " ")))

(defn match-result-line
  "Format a single match as a human-readable line."
  [m]
  (let [comp (competition-label (:competition m))
        round-info (cond
                     (:stage m) (str ", " (:stage m))
                     (:round m) (str ", Round " (:round m))
                     (:tournament m) (str " (" (:tournament m) ")")
                     :else "")]
    (format "%s: %s %s - %s %s (%s%s)"
            (or (:date m) "?")
            (or (:home-team m) "?")
            (or (:home-goals m) "?")
            (or (:away-goals m) "?")
            (or (:away-team m) "?")
            comp
            round-info)))
