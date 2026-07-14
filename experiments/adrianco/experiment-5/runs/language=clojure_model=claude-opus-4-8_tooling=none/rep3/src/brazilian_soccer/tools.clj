;; =============================================================================
;; brazilian-soccer.tools
;; -----------------------------------------------------------------------------
;; MCP tool catalogue and dispatch.
;;
;; Defines the set of tools exposed to an MCP client, each with a JSON-Schema
;; `inputSchema`, and a handler that runs the matching query (queries.clj) over
;; the cached datasets (data.clj) and renders the result (format.clj).
;;
;; `tool-defs`     -> the list returned by the MCP `tools/list` request
;; `call-tool`     -> dispatch for the MCP `tools/call` request
;;
;; Handlers are written against `(data/matches)` / `(data/players)` but accept an
;; optional explicit dataset (via `*matches*` / `*players*` bindings) so tests can
;; inject fixtures without touching disk.
;; =============================================================================
(ns brazilian-soccer.tools
  (:require [clojure.string :as str]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.queries :as q]
            [brazilian-soccer.format :as fmt]))

(def ^:dynamic *matches* nil)
(def ^:dynamic *players* nil)

(defn matches [] (or *matches* (data/matches)))
(defn players [] (or *players* (data/players)))

(def default-limit 25)

(defn- as-int [x]
  (cond (integer? x) x
        (string? x)  (try (Long/parseLong (str/trim x)) (catch Exception _ nil))
        (number? x)  (long x)
        :else nil))

(defn- blank->nil [x]
  (when (and (string? x) (not (str/blank? x))) x))

;; ---------------------------------------------------------------------------
;; Handlers (each takes the parsed `arguments` map with string keys)
;; ---------------------------------------------------------------------------

(defn h-find-matches [args]
  (let [crit {:team        (blank->nil (get args "team"))
              :home        (blank->nil (get args "home"))
              :away        (blank->nil (get args "away"))
              :opponent    (blank->nil (get args "opponent"))
              :competition (blank->nil (get args "competition"))
              :season      (as-int (get args "season"))
              :from        (blank->nil (get args "from"))
              :to          (blank->nil (get args "to"))}
        limit (or (as-int (get args "limit")) default-limit)
        res   (q/find-matches (matches) crit)]
    (fmt/ok (fmt/matches-block "Matches" res limit))))

(defn h-matches-between [args]
  (let [a (blank->nil (get args "team_a"))
        b (blank->nil (get args "team_b"))
        limit (or (as-int (get args "limit")) default-limit)]
    (if (and a b)
      (let [res (q/matches-between (matches) a b)
            h   (q/head-to-head (matches) a b)]
        (fmt/ok (str (fmt/matches-block (str a " vs " b) res limit)
                     "\n\n" (fmt/head-to-head-block h))))
      (fmt/err "Both team_a and team_b are required."))))

(defn h-head-to-head [args]
  (let [a (blank->nil (get args "team_a"))
        b (blank->nil (get args "team_b"))]
    (if (and a b)
      (fmt/ok (fmt/head-to-head-block (q/head-to-head (matches) a b)))
      (fmt/err "Both team_a and team_b are required."))))

(defn h-team-record [args]
  (let [team (blank->nil (get args "team"))
        venue (case (some-> (get args "venue") str/lower-case)
                "home" :home "away" :away :all)
        season (as-int (get args "season"))
        competition (blank->nil (get args "competition"))]
    (if team
      (let [ms (q/find-matches (matches)
                               (cond-> {:team team}
                                 season      (assoc :season season)
                                 competition (assoc :competition competition)))
            rec (q/team-record ms team venue)
            ctx (->> [(when competition competition)
                      (when season (str "season " season))]
                     (remove nil?) (str/join ", "))]
        (fmt/ok (str (fmt/team-record-block rec)
                     (when (seq ctx) (str "\n(filtered: " ctx ")")))))
      (fmt/err "team is required."))))

(defn h-find-players [args]
  (let [crit {:name        (blank->nil (get args "name"))
              :nationality (blank->nil (get args "nationality"))
              :club        (blank->nil (get args "club"))
              :position    (blank->nil (get args "position"))
              :min-overall (as-int (get args "min_overall"))}
        limit (or (as-int (get args "limit")) default-limit)
        res   (q/find-players (players) crit)]
    (fmt/ok (fmt/players-block "Players" res limit))))

(defn h-top-players [args]
  (let [n (or (as-int (get args "limit")) 10)
        nationality (blank->nil (get args "nationality"))
        res (q/top-players (players) n nationality)]
    (fmt/ok (fmt/players-block
             (str "Top " n " players"
                  (when nationality (str " (" nationality ")")))
             res n))))

(defn h-standings [args]
  (let [season (as-int (get args "season"))
        competition (or (blank->nil (get args "competition")) "Brasileirão")
        limit (or (as-int (get args "limit")) 20)]
    (if season
      (let [ms (q/find-matches (matches) {:competition competition :season season})
            rows (q/standings ms)]
        (if (seq rows)
          (fmt/ok (fmt/standings-block
                   (str competition " " season " standings (computed from "
                        (count ms) " matches)")
                   rows limit))
          (fmt/err (str "No matches found for " competition " " season "."))))
      (fmt/err "season is required."))))

(defn h-champion [args]
  (let [season (as-int (get args "season"))
        competition (or (blank->nil (get args "competition")) "Brasileirão")]
    (if season
      (let [ms (q/find-matches (matches) {:competition competition :season season})
            c  (q/champion ms)]
        (if c
          (fmt/ok (format "%s %d champion (computed from %d matches): %s — %d pts (%dW %dD %dL, GD %+d)"
                          competition season (count ms) (:team c) (:points c)
                          (:wins c) (:draws c) (:losses c) (:gd c)))
          (fmt/err (str "No matches found for " competition " " season "."))))
      (fmt/err "season is required."))))

(defn h-statistics [args]
  (let [competition (blank->nil (get args "competition"))
        season (as-int (get args "season"))
        crit (cond-> {} competition (assoc :competition competition)
                       season (assoc :season season))
        ms (if (seq crit) (q/find-matches (matches) crit) (matches))
        scope (->> [(or competition "all competitions")
                    (when season (str "season " season))]
                   (remove nil?) (str/join ", "))]
    (fmt/ok (str "Statistics (" scope ", " (count ms) " matches):\n"
                 "- Average goals per match: " (format "%.2f" (q/avg-goals ms)) "\n"
                 "- Home win rate: " (fmt/pct (q/home-win-rate ms)) "\n\n"
                 (fmt/matches-block "Biggest victories" (q/biggest-wins ms 5) 5)))))

(defn h-list-teams [args]
  (let [competition (blank->nil (get args "competition"))
        ms (if competition
             (q/find-matches (matches) {:competition competition})
             (matches))
        teams (q/all-teams ms)]
    (fmt/ok (str "Teams (" (count teams) "):\n" (str/join ", " teams)))))

;; ---------------------------------------------------------------------------
;; Tool catalogue
;; ---------------------------------------------------------------------------

(def tool-defs
  [{:name "find_matches"
    :description "Find soccer matches by team, opponent, competition, season, or date range. Searches Brasileirão, Copa do Brasil, Copa Libertadores and extended match datasets."
    :inputSchema {:type "object"
                  :properties {"team"        {:type "string" :description "Team that played (home or away)"}
                               "home"        {:type "string" :description "Team playing at home"}
                               "away"        {:type "string" :description "Team playing away"}
                               "opponent"    {:type "string" :description "Restrict to matches also involving this team"}
                               "competition" {:type "string" :description "Competition name, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'"}
                               "season"      {:type "integer" :description "Season year, e.g. 2019"}
                               "from"        {:type "string" :description "Earliest date, ISO yyyy-MM-dd"}
                               "to"          {:type "string" :description "Latest date, ISO yyyy-MM-dd"}
                               "limit"       {:type "integer" :description "Max rows to display (default 25)"}}}
    :handler h-find-matches}

   {:name "matches_between"
    :description "List all matches between two teams plus a head-to-head summary (the derby/clássico view)."
    :inputSchema {:type "object"
                  :properties {"team_a" {:type "string"}
                               "team_b" {:type "string"}
                               "limit"  {:type "integer"}}
                  :required ["team_a" "team_b"]}
    :handler h-matches-between}

   {:name "head_to_head"
    :description "Head-to-head record (wins/draws/goals) between two teams across all competitions."
    :inputSchema {:type "object"
                  :properties {"team_a" {:type "string"}
                               "team_b" {:type "string"}}
                  :required ["team_a" "team_b"]}
    :handler h-head-to-head}

   {:name "team_record"
    :description "Win/draw/loss and goals record for a team, optionally restricted to a season, competition, and home/away venue."
    :inputSchema {:type "object"
                  :properties {"team"        {:type "string"}
                               "venue"       {:type "string" :enum ["all" "home" "away"]}
                               "season"      {:type "integer"}
                               "competition" {:type "string"}}
                  :required ["team"]}
    :handler h-team-record}

   {:name "find_players"
    :description "Search FIFA player data by name, nationality, club, position, or minimum overall rating."
    :inputSchema {:type "object"
                  :properties {"name"        {:type "string"}
                               "nationality" {:type "string" :description "e.g. 'Brazil'"}
                               "club"        {:type "string"}
                               "position"    {:type "string" :description "Position code, e.g. 'ST', 'GK', 'CB'"}
                               "min_overall" {:type "integer"}
                               "limit"       {:type "integer"}}}
    :handler h-find-players}

   {:name "top_players"
    :description "Highest-rated players overall, optionally filtered by nationality (e.g. top Brazilian players)."
    :inputSchema {:type "object"
                  :properties {"nationality" {:type "string"}
                               "limit"       {:type "integer" :description "How many (default 10)"}}}
    :handler h-top-players}

   {:name "standings"
    :description "Compute a league table for a competition and season from match results (3 pts win / 1 draw)."
    :inputSchema {:type "object"
                  :properties {"season"      {:type "integer"}
                               "competition" {:type "string" :description "Default 'Brasileirão'"}
                               "limit"       {:type "integer"}}
                  :required ["season"]}
    :handler h-standings}

   {:name "champion"
    :description "Determine the champion of a competition/season from computed standings."
    :inputSchema {:type "object"
                  :properties {"season"      {:type "integer"}
                               "competition" {:type "string"}}
                  :required ["season"]}
    :handler h-champion}

   {:name "statistics"
    :description "Aggregate statistics (average goals per match, home win rate, biggest victories) for a competition/season or the whole dataset."
    :inputSchema {:type "object"
                  :properties {"competition" {:type "string"}
                               "season"      {:type "integer"}}}
    :handler h-statistics}

   {:name "list_teams"
    :description "List distinct team names known to the dataset, optionally for one competition."
    :inputSchema {:type "object"
                  :properties {"competition" {:type "string"}}}
    :handler h-list-teams}])

(def ^:private by-name
  (into {} (map (juxt :name identity) tool-defs)))

(defn list-tools
  "Tool descriptors for the MCP tools/list response (handlers stripped)."
  []
  (mapv #(dissoc % :handler) tool-defs))

(defn call-tool
  "Dispatch an MCP tools/call. `name` is the tool name, `arguments` the parsed
   argument map (string keys). Returns an MCP content map."
  [name arguments]
  (if-let [{:keys [handler]} (by-name name)]
    (try
      (handler (or arguments {}))
      (catch Exception e
        (fmt/err (str "Error running tool '" name "': " (.getMessage e)))))
    (fmt/err (str "Unknown tool: " name))))
