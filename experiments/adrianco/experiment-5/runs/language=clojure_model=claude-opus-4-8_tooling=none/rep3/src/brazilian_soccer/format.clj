;; =============================================================================
;; brazilian-soccer.format
;; -----------------------------------------------------------------------------
;; Render query results as human-readable text blocks for MCP tool responses.
;;
;; The MCP `tools/call` result returns text content, so each formatter turns a
;; data structure from queries.clj into a concise, LLM-friendly string that
;; mirrors the example answer formats in the specification.
;; =============================================================================
(ns brazilian-soccer.format
  (:require [clojure.string :as str]))

(defn pct [x] (format "%.1f%%" (* 100.0 (double x))))

(defn match-line
  "One-line summary of a match, e.g.
     2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)"
  [m]
  (let [score (if (and (some? (:home-goal m)) (some? (:away-goal m)))
                (str (:home-goal m) "-" (:away-goal m))
                "?-?")
        ctx   (->> [(:competition m)
                    (when (:round m) (str "Round " (:round m)))]
                   (remove nil?)
                   (str/join ", "))]
    (str (or (:date m) "????-??-??") ": "
         (:home m) " " score " " (:away m)
         (when (seq ctx) (str " (" ctx ")")))))

(defn matches-block
  "Header + up to `limit` match lines + an overflow note."
  [title matches limit]
  (let [n (count matches)
        shown (take limit matches)]
    (str title " (" n " found):\n"
         (if (zero? n)
           "  (no matches)"
           (str/join "\n" (map #(str "- " (match-line %)) shown)))
         (when (> n limit)
           (str "\n  ... (" (- n limit) " more not shown)")))))

(defn head-to-head-block [h]
  (str "Head-to-head: " (:team-a h) " vs " (:team-b h) "\n"
       "- Matches with result: " (:played h) "\n"
       "- " (:team-a h) " wins: " (:a-wins h) "\n"
       "- " (:team-b h) " wins: " (:b-wins h) "\n"
       "- Draws: " (:draws h) "\n"
       "- Goals: " (:team-a h) " " (:a-goals h)
       " - " (:b-goals h) " " (:team-b h)))

(defn team-record-block [r]
  (let [venue (case (:venue r) :home "home " :away "away " "")]
    (str (:display r) " " venue "record:\n"
         "- Matches: " (:played r) "\n"
         "- Wins: " (:wins r) ", Draws: " (:draws r) ", Losses: " (:losses r) "\n"
         "- Goals For: " (:goals-for r) ", Goals Against: " (:goals-against r) "\n"
         "- Win rate: " (pct (:win-rate r)))))

(defn player-line [p]
  (str (:name p)
       " - Overall: " (or (:overall p) "?")
       ", Position: " (or (:position p) "?")
       ", Age: " (or (:age p) "?")
       ", Nationality: " (or (:nationality p) "?")
       ", Club: " (or (:club p) "?")))

(defn players-block [title players limit]
  (let [n (count players)
        shown (take limit players)]
    (str title " (" n " found):\n"
         (if (zero? n)
           "  (no players)"
           (str/join "\n"
                     (map-indexed (fn [i p] (str (inc i) ". " (player-line p)))
                                  shown)))
         (when (> n limit)
           (str "\n  ... (" (- n limit) " more not shown)")))))

(defn standings-block [title rows limit]
  (str title ":\n"
       (str/join "\n"
                 (map-indexed
                  (fn [i r]
                    (format "%2d. %s - %d pts (%dW %dD %dL, GD %+d)"
                            (inc i) (:team r) (:points r)
                            (:wins r) (:draws r) (:losses r) (:gd r)))
                  (take limit rows)))))

(defn ok
  "Wrap text into the MCP tools/call content shape."
  [text]
  {:content [{:type "text" :text text}]})

(defn err [text]
  {:content [{:type "text" :text text}] :isError true})
