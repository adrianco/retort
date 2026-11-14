(ns brsoccer.tools
  "MCP tool definitions: JSON schemas plus handlers that turn arguments into
  query calls and render the answer as plain text for the LLM."
  (:require [brsoccer.data :as data]
            [brsoccer.queries :as q]
            [brsoccer.teams :as teams]
            [clojure.string :as str]))

;; ------------------------------------------------------------------ arguments

(defn- arg [args k]
  (let [v (get args k)]
    (when-not (or (nil? v) (and (string? v) (str/blank? v))) v)))

(defn- int-arg [args k default lo hi]
  (let [v (arg args k)
        n (cond (nil? v) default
                (integer? v) v
                (number? v) (long v)
                :else (or (data/parse-int v)
                          (q/fail (str "Invalid " k ": \"" v "\". Expected a whole number."))))]
    (when n (-> n (max lo) (min hi)))))

(defn- venue-arg [args]
  (when-let [v (arg args "venue")]
    (case (teams/fold v)
      ("home" "casa" "mandante") :home
      ("away" "fora" "visitante") :away
      ("all" "both" "either" "any") nil
      (q/fail (str "Invalid venue: \"" v "\". Use home, away or all.")))))

(defn- match-filters
  "Shared competition/season/date filters."
  [args]
  {:competition (q/resolve-competition (arg args "competition"))
   :season      (q/parse-season (arg args "season"))
   :from        (q/parse-date! (arg args "date_from"))
   :to          (q/parse-date! (arg args "date_to"))})

;; ------------------------------------------------------------------ rendering

(defn- comp-name [c] (data/competitions c))

(defn- scope-label [{:keys [competition season]}]
  (let [parts (remove nil? [(some-> season str) (some-> competition comp-name)])]
    (if (seq parts) (str/join " " parts) "all competitions, all seasons")))

(defn- detail [m]
  (str/join ", "
            (remove nil? [(comp-name (:competition m))
                          (when (and (:season m) (:date m)
                                     (not= (str (:season m)) (subs (:date m) 0 4)))
                            (str (:season m) " season"))
                          (some-> (:stage m) str/capitalize)
                          (when (:round m) (str "Round " (:round m)))])))

(defn- match-line
  ([m] (match-line m false))
  ([m stats?]
   (str (or (:date m) "date unknown") ": " (:home-name m) " " (:hg m) "-" (:ag m) " " (:away-name m)
        " (" (detail m) ")"
        (when-let [d (q/derby-name m)] (str " [" d "]"))
        (when (and stats? (:arena m)) (str " @ " (:arena m)))
        (when-let [s (and stats? (:stats m))]
          (let [pair (fn [label a b] (when (and (s a) (s b)) (str label " " (s a) "-" (s b))))
                bits (remove nil? [(pair "corners" :home-corners :away-corners)
                                   (pair "shots" :home-shots :away-shots)
                                   (pair "attacks" :home-attacks :away-attacks)])]
            (when (seq bits) (str " {" (str/join ", " bits) "}")))))))

(defn- match-list [matches limit stats?]
  (let [shown (take limit matches)
        more  (- (count matches) (count shown))]
    (str/join "\n" (concat (map #(str "- " (match-line % stats?)) shown)
                           (when (pos? more) [(str "- ... (" more " more matches in dataset)")])))))

(defn- pct [x] (format "%.1f%%" (double x)))

(defn- record-lines [r]
  (str "- Matches: " (:p r) "\n"
       "- Wins: " (:w r) ", Draws: " (:d r) ", Losses: " (:l r) "\n"
       "- Goals For: " (:gf r) ", Goals Against: " (:ga r)
       " (difference " (format "%+d" (:gd r)) ")\n"
       "- Points (3/1/0): " (:pts r) "\n"
       "- Win rate: " (pct (:win-rate r))))

(defn- record-brief [r]
  (str (:p r) " matches, " (:w r) "W " (:d r) "D " (:l r) "L, goals " (:gf r) "-" (:ga r)
       ", win rate " (pct (:win-rate r))))

(defn- player-line [p]
  (str (:name p) " - Overall: " (:overall p) ", Position: " (or (:position p) "n/a")
       ", Club: " (or (:club p) "no club") ", Nationality: " (:nationality p)
       ", Age: " (:age p)))

;; --------------------------------------------------------------------- tools

(defn- search-matches [db args]
  (let [team   (some->> (arg args "team") (q/team! db))
        opp    (some->> (arg args "opponent") (q/team! db))
        _      (when (and opp (not team)) (q/fail "\"opponent\" requires \"team\"."))
        f      (merge (match-filters args)
                      {:team team :opponent opp :venue (venue-arg args)
                       :stage (some-> (arg args "stage") str/lower-case str/trim)
                       :round (int-arg args "round" nil 1 100)})
        ms     (q/find-matches db f)
        ms     (if (= "oldest" (arg args "order")) (reverse ms) ms)
        limit  (int-arg args "limit" 20 1 500)
        title  (str (cond (and team opp) (str (q/team-name db team) " vs " (q/team-name db opp))
                          team (str (q/team-name db team)
                                    (case (:venue f) :home " home" :away " away" "") " matches")
                          :else "Matches")
                    (when-let [d (and team opp (teams/derby-index #{team opp}))] (str " (" d " derby)"))
                    " - " (scope-label f)
                    (when (:stage f) (str ", stage: " (:stage f)))
                    (when (or (:from f) (:to f))
                      (str ", " (or (:from f) "start") " to " (or (:to f) "end"))))]
    (if (empty? ms)
      (str title ":\nNo matches found in the dataset for these criteria.")
      (str title " (" (count ms) " found):\n"
           (match-list ms limit (boolean (arg args "include_stats")))
           (when (and team opp)
             (let [r (q/record ms team :all)]
               (str "\n\nHead-to-head in dataset: " (q/team-name db team) " " (:w r) " wins, "
                    (q/team-name db opp) " " (:l r) " wins, " (:d r) " draws")))
           (when (and team (not opp))
             (str "\n\nRecord in these matches: "
                  (record-brief (q/record ms team (or (:venue f) :all)))))))))

(defn- head-to-head [db args]
  (let [a (q/team! db (or (arg args "team_a") (q/fail "team_a is required.")))
        b (q/team! db (or (arg args "team_b") (q/fail "team_b is required.")))
        _ (when (= a b) (q/fail "team_a and team_b resolve to the same club."))
        f (match-filters args)
        {:keys [matches a-wins b-wins draws a-goals b-goals]} (q/head-to-head db a b f)
        an (q/team-name db a) bn (q/team-name db b)]
    (if (empty? matches)
      (str an " vs " bn " (" (scope-label f) "): no matches found in the dataset.")
      (let [home-a (q/record (filter #(= a (:home %)) matches) a :home)
            home-b (q/record (filter #(= b (:home %)) matches) b :home)
            last-m (first matches)]
        (str an " vs " bn
             (when-let [d (teams/derby-index #{a b})] (str " (" d " derby)"))
             " - " (scope-label f) ":\n"
             "- Matches: " (count matches) "\n"
             "- " an " wins: " a-wins "\n"
             "- " bn " wins: " b-wins "\n"
             "- Draws: " draws "\n"
             "- Goals: " an " " a-goals ", " bn " " b-goals "\n"
             "- " an " at home: " (:w home-a) "W " (:d home-a) "D " (:l home-a) "L\n"
             "- " bn " at home: " (:w home-b) "W " (:d home-b) "D " (:l home-b) "L\n"
             "- By competition: "
             (str/join "; " (map (fn [[c ms]] (str (comp-name c) " " (count ms)))
                                 (sort-by (comp - count val) (group-by :competition matches))))
             "\n- Most recent: " (match-line last-m)
             "\n\nRecent matches:\n" (match-list matches (int-arg args "limit" 10 1 500) false))))))

(defn- team-stats [db args]
  (let [team  (q/team! db (or (arg args "team") (q/fail "team is required.")))
        f     (match-filters args)
        venue (venue-arg args)
        ms    (q/find-matches db (assoc f :team team))
        nm    (q/team-name db team)]
    (if (empty? ms)
      (str nm " (" (scope-label f) "): no matches found in the dataset.")
      (let [all  (q/record ms team :all)
            home (q/record ms team :home)
            away (q/record ms team :away)]
        (if venue
          (str nm " " (name venue) " record (" (scope-label f) "):\n"
               (record-lines (if (= venue :home) home away)))
          (str nm " record (" (scope-label f) "):\n" (record-lines all)
               "\n- Home: " (record-brief home)
               "\n- Away: " (record-brief away)
               (when-not (:competition f)
                 (str "\n\nBy competition:\n"
                      (str/join "\n"
                                (for [[c cms] (sort-by (comp - count val) (group-by :competition ms))]
                                  (str "- " (comp-name c) ": " (record-brief (q/record cms team :all)))))))))))))

(defn- team-overview [db args]
  (let [team (q/team! db (or (arg args "team") (q/fail "team is required.")))
        ms   (q/find-matches db {:team team})
        nm   (q/team-name db team)
        ps   (sort-by (comp - :overall) (filter #(= team (:club-key %)) (:players db)))]
    (str nm " - overview from the dataset:\n"
         "- Matches: " (count ms) " (" (:date (last ms)) " to " (:date (first ms)) ")\n"
         "- Overall: " (record-brief (q/record ms team :all)) "\n"
         "\nCompetitions played:\n"
         (str/join "\n"
                   (for [[c cms] (sort-by (comp - count val) (group-by :competition ms))
                         :let [seasons (sort (distinct (keep :season cms)))]]
                     (str "- " (comp-name c) ": " (count seasons) " seasons ("
                          (first seasons) "-" (last seasons) "), "
                          (record-brief (q/record cms team :all)))))
         "\n\nMost recent matches:\n" (match-list ms 5 false)
         "\n\nPlayers in FIFA dataset"
         (if (seq ps)
           (str " (" (count ps) ", club listed as \"" (:club (first ps)) "\", avg overall "
                (format "%.1f" (/ (double (reduce + (map :overall ps))) (count ps))) "):\n"
                (str/join "\n" (map-indexed #(str (inc %1) ". " (player-line %2)) (take 10 ps))))
           ": none (this club is not in the FIFA player file)."))))

(defn- team-trend [db args]
  (let [team (q/team! db (or (arg args "team") (q/fail "team is required.")))
        comp (or (q/resolve-competition (arg args "competition")) :serie-a)
        ms   (q/find-matches db {:team team :competition comp})
        nm   (q/team-name db team)]
    (if (empty? ms)
      (str nm ": no " (comp-name comp) " matches in the dataset.")
      (str nm " season-by-season in " (comp-name comp) ":\n"
           (str/join "\n"
                     (for [[season sms] (sort-by key (group-by :season ms))
                           :let [r (q/record sms team :all)
                                 pos (when (#{:serie-a :serie-b} comp)
                                       (first (keep-indexed #(when (= team (:team %2)) (inc %1))
                                                            (q/standings db comp season))))]]
                       (str "- " season ": " (:pts r) " pts, " (record-brief r)
                            (when pos (str ", finished " pos
                                           (case (mod pos 10) 1 (if (= pos 11) "th" "st")
                                                 2 (if (= pos 12) "th" "nd")
                                                 3 (if (= pos 13) "th" "rd") "th"))))))))))

(defn- standings [db args]
  (let [comp   (or (q/resolve-competition (arg args "competition")) :serie-a)
        season (or (q/parse-season (arg args "season")) (q/fail "season is required."))
        _      (when-not (#{:serie-a :serie-b :serie-c} comp)
                 (q/fail (str (comp-name comp) " is a knockout competition; use competition_bracket.")))
        rows   (q/standings db comp season)
        n      (count rows)
        full?  (and (pos? n) (every? #(= (:p %) (* 2 (dec n))) rows))
        releg  (if full? (q/relegation-slots comp season) 0)
        limit  (int-arg args "limit" 40 1 100)]
    (if (empty? rows)
      (str "No " (comp-name comp) " matches for season " season " in the dataset.")
      (str season " " (comp-name comp) " standings (calculated from "
           (reduce + (map :p rows)) "/2 = " (quot (reduce + (map :p rows)) 2) " matches):\n"
           (str/join "\n"
                     (map-indexed
                      (fn [i r]
                        (str (inc i) ". " (q/team-name db (:team r)) " - " (:pts r) " pts ("
                             (:w r) "W, " (:d r) "D, " (:l r) "L), goals " (:gf r) "-" (:ga r)
                             " (" (format "%+d" (:gd r)) ")"
                             (cond (and full? (zero? i)) " - Champion"
                                   (>= i (- n releg)) " - Relegated")))
                      (take limit rows)))
           "\n\n"
           (if full?
             "Note: computed from match results (3 pts/win; ties broken by wins, goal difference, goals scored). Sporting-tribunal point deductions are not in the data, so official tables can differ slightly."
             "Note: this season is incomplete or not a single round-robin in the dataset, so no champion/relegation labels are shown.")))))

(defn- bracket [db args]
  (let [comp   (or (q/resolve-competition (arg args "competition")) (q/fail "competition is required."))
        season (or (q/parse-season (arg args "season")) (q/fail "season is required."))
        _      (when-not (#{:copa-do-brasil :libertadores} comp)
                 (q/fail (str (comp-name comp) " is a league; use standings.")))
        ms     (q/find-matches db {:competition comp :season season})
        order  ["round of 16" "quarterfinals" "semifinals" "final"]
        staged (group-by :stage ms)
        tie-line (fn [{:keys [legs a b a-goals b-goals winner]}]
                   (str "- " (q/team-name db a) " " a-goals "-" b-goals " " (q/team-name db b)
                        " on aggregate"
                        (if winner
                          (str " -> " (q/team-name db winner) " advance")
                          " -> level; decided by away goals/penalties (not in data)")
                        " [" (str/join "; " (map #(str (:date %) " " (:home-name %) " " (:hg %) "-"
                                                       (:ag %) " " (:away-name %)) legs)) "]"))]
    (if (empty? ms)
      (str "No " (comp-name comp) " matches for season " season " in the dataset.")
      (str season " " (comp-name comp) " knockout bracket:\n"
           (str/join "\n"
                     (for [stage order :let [sms (staged stage)] :when (seq sms)]
                       (str (str/capitalize stage) ":\n"
                            (str/join "\n" (map tie-line (q/ties sms))))))
           (when-not (some staged order)
             "Knockout stages are not identifiable for this season in the dataset.")
           (let [early (remove #(some #{(:stage %)} order) ms)]
             (when (seq early)
               (str "\n\nEarlier rounds / group stage: " (count early) " matches"
                    " (use search_matches with competition and season to list them).")))
           (when-let [fin (seq (staged "final"))]
             (let [t (last (q/ties fin))]
               (str "\n\n" (if (:winner t)
                             (str "Champion: " (q/team-name db (:winner t)))
                             "Champion: final level on aggregate in the data (decided on penalties/away goals)."))))))))

(defn- summary-block [s]
  (str "- Matches: " (:matches s) "\n"
       "- Goals: " (:goals s) " (home " (:home-goals s) ", away " (:away-goals s) ")\n"
       "- Average goals per match: " (format "%.2f" (:avg-goals s)) "\n"
       "- Home win rate: " (pct (:home-win-rate s)) " (" (:home-wins s) ")\n"
       "- Draw rate: " (pct (:draw-rate s)) " (" (:draws s) ")\n"
       "- Away win rate: " (pct (:away-win-rate s)) " (" (:away-wins s) ")"))

(defn- match-statistics [db args]
  (let [f    (match-filters args)
        team (some->> (arg args "team") (q/team! db))
        ms   (q/find-matches db (assoc f :team team))]
    (if (empty? ms)
      "No matches found in the dataset for these criteria."
      (let [with-stats (filter :stats ms)
            avg (fn [k1 k2]
                  (let [vs (keep #(let [s (:stats %)] (when (and (s k1) (s k2)) (+ (s k1) (s k2))))
                                 with-stats)]
                    (when (seq vs) (format "%.1f" (/ (double (reduce + vs)) (count vs))))))]
        (str "Match statistics - " (scope-label f)
             (when team (str ", " (q/team-name db team) " matches")) ":\n"
             (summary-block (q/summary ms))
             (when (seq with-stats)
               (str "\n- Extended stats available for " (count with-stats) " matches: avg corners "
                    (avg :home-corners :away-corners) ", avg shots " (avg :home-shots :away-shots)))
             (when-not (:competition f)
               (str "\n\nBy competition:\n"
                    (str/join "\n"
                              (for [[c cms] (sort-by (comp name key) (group-by :competition ms))
                                    :let [s (q/summary cms)]]
                                (str "- " (comp-name c) ": " (:matches s) " matches, "
                                     (format "%.2f" (:avg-goals s)) " goals/match, home win rate "
                                     (pct (:home-win-rate s))))))))))))

(defn- compare-seasons [db args]
  (let [comp    (or (q/resolve-competition (arg args "competition")) :serie-a)
        seasons (map q/parse-season (or (arg args "seasons") (q/fail "seasons is required.")))
        _       (when (empty? seasons) (q/fail "seasons must list at least one year."))]
    (str "Season comparison - " (comp-name comp) ":\n"
         (str/join "\n\n"
                   (for [season seasons
                         :let [ms (q/find-matches db {:competition comp :season season})]]
                     (if (empty? ms)
                       (str season ": no matches in the dataset.")
                       (let [tbl  (if (#{:serie-a :serie-b} comp) (q/standings db comp season) [])
                             top  (first tbl)
                             best (first (q/rankings ms :all "goals_for" 1))]
                         (str season ":\n" (summary-block (q/summary ms))
                              (when top
                                (str "\n- Top of table: " (q/team-name db (:team top)) " ("
                                     (:pts top) " pts)"))
                              (when best
                                (str "\n- Most goals scored: " (q/team-name db (:team best)) " ("
                                     (:gf best) ")"))
                              "\n- Biggest win: " (match-line (first (q/biggest-wins ms)))))))))))

(defn- team-rankings [db args]
  (let [f      (match-filters args)
        venue  (or (venue-arg args) :all)
        metric (or (some-> (arg args "metric") str/lower-case) "win_rate")
        _      (when-not (q/ranking-metrics metric)
                 (q/fail (str "Invalid metric: \"" metric "\". Use one of: "
                              (str/join ", " (sort (keys q/ranking-metrics))) ".")))
        ms     (q/find-matches db f)
        minm   (int-arg args "min_matches" (if (:season f) 5 20) 1 100000)
        rows   (q/rankings ms venue metric minm)
        limit  (int-arg args "limit" 10 1 200)]
    (if (empty? rows)
      "No teams meet these criteria in the dataset."
      (str "Team ranking by " (str/replace metric "_" " ") " - "
           (case venue :home "home matches" :away "away matches" "all matches")
           ", " (scope-label f) " (min " minm " matches):\n"
           (str/join "\n"
                     (map-indexed
                      (fn [i r]
                        (str (inc i) ". " (q/team-name db (:team r)) " - " (record-brief r)
                             ", " (:pts r) " pts (" (format "%.2f" (:ppg r)) "/match)"))
                      (take limit rows)))))))

(defn- biggest-wins [db args]
  (let [f    (match-filters args)
        team (some->> (arg args "team") (q/team! db))
        ms   (q/biggest-wins (q/find-matches db (assoc f :team team)))
        s    (q/summary (q/find-matches db (assoc f :team team)))]
    (if (empty? ms)
      "No decisive matches found in the dataset for these criteria."
      (str "Biggest victories - " (scope-label f)
           (when team (str ", " (q/team-name db team) " matches")) ":\n"
           (str/join "\n" (map-indexed #(str (inc %1) ". " (match-line %2))
                                       (take (int-arg args "limit" 10 1 200) ms)))
           "\n\nAverage goals per match: " (format "%.2f" (:avg-goals s))
           "\nHome win rate: " (pct (:home-win-rate s))))))

(defn- find-derbies [db args]
  (let [f    (match-filters args)
        team (some->> (arg args "team") (q/team! db))
        ms   (filter q/derby-name (q/find-matches db (assoc f :team team)))]
    (if (empty? ms)
      "No derby matches found in the dataset for these criteria."
      (str "Derbies (traditional rivalries) - " (scope-label f) " (" (count ms) " found):\n"
           (match-list ms (int-arg args "limit" 30 1 500) false)
           "\n\nBy rivalry: "
           (str/join "; " (map (fn [[d n]] (str d " " n))
                               (sort-by (comp - val) (frequencies (map q/derby-name ms)))))))))

(defn- search-players [db args]
  (let [opts  {:name (arg args "name") :nationality (arg args "nationality")
               :club (arg args "club") :position (arg args "position")
               :min-overall (int-arg args "min_overall" nil 0 100)
               :max-age (int-arg args "max_age" nil 0 100)
               :sort (some-> (arg args "sort_by") str/lower-case)}
        {:keys [players approximate?]} (q/find-players db opts)
        limit (int-arg args "limit" 20 1 200)
        crit  (str/join ", " (for [[k v] (dissoc opts :sort) :when v] (str (name k) "=" v)))]
    (cond
      (empty? players)
      (str "No players found in the FIFA dataset (" (if (str/blank? crit) "no filters" crit) ")."
           (when (:club opts)
             " Note: the FIFA file only covers some Brazilian clubs; use brazilian_club_players to see which."))

      :else
      (str (if approximate?
             (str "No player matches every word of \"" (:name opts) "\"; closest partial matches")
             (str "Players (" (if (str/blank? crit) "all" crit) ")"))
           " - " (count players) " found, sorted by " (or (:sort opts) "overall") ":\n"
           (str/join "\n" (map-indexed #(str (inc %1) ". " (player-line %2)) (take limit players)))
           (when (> (count players) limit)
             (str "\n... (" (- (count players) limit) " more players in dataset)"))))))

(defn- player-details [db args]
  (let [id (int-arg args "id" nil 0 Long/MAX_VALUE)
        nm (arg args "name")
        _  (when-not (or id nm) (q/fail "Provide a player name or id."))
        {:keys [players approximate?]}
        (if id
          {:players (filter #(= id (:id %)) (:players db))}
          (q/find-players db {:name nm}))
        p  (first players)]
    (if-not p
      (str "No player found for " (if id (str "id " id) (str "\"" nm "\"")) " in the FIFA dataset.")
      (str (when approximate? (str "No exact match for \"" nm "\"; showing the closest player.\n"))
           (:name p) " (FIFA id " (:id p) "):\n"
           "- Age: " (:age p) ", Nationality: " (:nationality p) "\n"
           "- Club: " (or (:club p) "no club")
           (when-let [k (:club-key p)] (str " (in match data as " (q/team-name db k) ")")) "\n"
           "- Position: " (or (:position p) "n/a") ", Jersey: " (or (:jersey p) "n/a") "\n"
           "- Overall: " (:overall p) ", Potential: " (:potential p) "\n"
           "- Height: " (or (:height p) "n/a") ", Weight: " (or (:weight p) "n/a")
           ", Preferred foot: " (or (:foot p) "n/a") "\n"
           "- Value: " (or (:value p) "n/a") ", Wage: " (or (:wage p) "n/a") "\n"
           "- Joined: " (or (:joined p) "n/a") ", Contract until: " (or (:contract p) "n/a") "\n"
           "- Top attributes: "
           (str/join ", " (map (fn [[k v]] (str k " " v)) (take 8 (sort-by (comp - val) (:skills p)))))
           (when (> (count players) 1)
             (str "\n\nOther matches: "
                  (str/join "; " (map #(str (:name %) " (" (:overall %) ", " (or (:club %) "no club") ")")
                                      (take 8 (rest players))))))))))

(defn- club-players [db args]
  (let [nat  (arg args "nationality")
        rows (q/club-summary db nat)]
    (if (empty? rows)
      "No players at Brazilian clubs match these criteria in the FIFA dataset."
      (str (if nat (str nat " players") "Players") " at Brazilian clubs in the FIFA dataset:\n"
           (str/join "\n" (map #(str "- " (:club %) ": " (:count %) " players (avg rating: "
                                     (format "%.1f" (:avg %)) ", best: " (:name (:best %)) " "
                                     (:overall (:best %)) ")")
                               rows))
           "\n\nNote: only clubs present in the FIFA file are listed; clubs such as Flamengo, "
           "Palmeiras, Corinthians and São Paulo are absent from it."))))

(defn- list-teams [db args]
  (let [qry   (some-> (arg args "query") teams/fold)
        cmp   (q/resolve-competition (arg args "competition"))
        rows  (->> (vals (:teams db))
                   (filter #(or (nil? qry) (str/includes? (:name-fold %) qry) (str/includes? (:key %) qry)))
                   (filter #(or (nil? cmp) ((:competitions %) cmp)))
                   (sort-by (juxt (comp - :matches) :name)))
        limit (int-arg args "limit" 50 1 500)]
    (if (empty? rows)
      "No teams match."
      (str "Teams in dataset (" (count rows) " found, by matches played):\n"
           (str/join "\n" (map #(str "- " (:name %) ": " (:matches %) " matches ("
                                     (str/join ", " (map comp-name (sort (:competitions %)))) ")")
                               (take limit rows)))
           (when (> (count rows) limit) (str "\n... (" (- (count rows) limit) " more)"))))))

(defn- dataset-info [db _]
  (let [ms (:matches db)]
    (str "Brazilian soccer dataset:\n"
         "Source files (rows):\n"
         (str/join "\n" (map #(str "- " % ": " (get (:row-counts db) %)) data/files))
         "\n\nUnique matches after merging duplicates across files: " (count ms) "\n"
         (str/join "\n"
                   (for [[c cms] (sort-by (comp name key) (group-by :competition ms))
                         :let [ss (sort (distinct (keep :season cms)))]]
                     (str "- " (comp-name c) ": " (count cms) " matches, seasons "
                          (first ss) "-" (last ss))))
         "\n\nTeams: " (count (:teams db))
         "\nPlayers (FIFA): " (count (:players db)) ", of which Brazilian: "
         (count (filter #(= "Brazil" (:nationality %)) (:players db)))
         "\n\nLimits: no goal-scorer data (top scorers cannot be derived); player data is a single FIFA snapshot.")))

;; ------------------------------------------------------------------- registry

(def ^:private common
  {"competition" {:type "string"
                  :description "Competition: Brasileirão / Serie A, Serie B, Serie C, Copa do Brasil, or Libertadores."}
   "season"      {:type "integer" :description "Season year, e.g. 2019."}
   "date_from"   {:type "string" :description "Earliest match date (YYYY-MM-DD or DD/MM/YYYY)."}
   "date_to"     {:type "string" :description "Latest match date (YYYY-MM-DD or DD/MM/YYYY)."}
   "limit"       {:type "integer" :description "Maximum rows to list."}
   "venue"       {:type "string" :enum ["home" "away" "all"] :description "Count only home or away matches."}
   "team"        {:type "string" :description "Team name; any spelling works (Flamengo, Flamengo-RJ, Sao Paulo, Atlético Mineiro)."}})

(defn- schema [props required]
  {:type "object"
   :properties (into {} (map (fn [p] (if (string? p) [p (common p)] p))) props)
   :required required})

(def tools
  [{:name "search_matches"
    :description "Find matches by team, opponent, venue, competition, season, date range, stage or round. Newest first. With team+opponent also gives the head-to-head tally. Use stage=\"final\" for cup finals."
    :inputSchema (schema ["team" ["opponent" {:type "string" :description "Second team (requires team)."}]
                          "venue" "competition" "season" "date_from" "date_to"
                          ["stage" {:type "string" :description "Knockout stage: group stage, round of 16, quarterfinals, semifinals, final."}]
                          ["round" {:type "integer" :description "Round number (league round or cup round)."}]
                          ["order" {:type "string" :enum ["newest" "oldest"]}]
                          ["include_stats" {:type "boolean" :description "Show stadium, corners and shots where available."}]
                          "limit"] [])
    :handler search-matches}
   {:name "head_to_head"
    :description "Compare two teams: wins, draws, goals, home records and recent meetings."
    :inputSchema (schema [["team_a" {:type "string"}] ["team_b" {:type "string"}]
                          "competition" "season" "date_from" "date_to" "limit"] ["team_a" "team_b"])
    :handler head-to-head}
   {:name "team_stats"
    :description "A team's win/draw/loss record, goals and win rate, optionally for one season, competition or venue (home/away)."
    :inputSchema (schema ["team" "season" "competition" "venue" "date_from" "date_to"] ["team"])
    :handler team-stats}
   {:name "team_overview"
    :description "Everything known about a team: competitions played, records per competition, latest matches, and its players in the FIFA data."
    :inputSchema (schema ["team"] ["team"])
    :handler team-overview}
   {:name "team_season_trend"
    :description "A team's season-by-season performance in one competition (default Serie A)."
    :inputSchema (schema ["team" "competition"] ["team"])
    :handler team-trend}
   {:name "standings"
    :description "League table for a season, calculated from match results, with champion and relegated teams. Default competition: Serie A."
    :inputSchema (schema ["competition" "season" "limit"] ["season"])
    :handler standings}
   {:name "competition_bracket"
    :description "Knockout rounds of the Copa do Brasil or Copa Libertadores for a season, with aggregate scores and the champion."
    :inputSchema (schema ["competition" "season"] ["competition" "season"])
    :handler bracket}
   {:name "match_statistics"
    :description "Aggregate statistics: average goals per match, home/draw/away rates, optionally filtered by competition, season, team or dates."
    :inputSchema (schema ["competition" "season" "team" "date_from" "date_to"] [])
    :handler match-statistics}
   {:name "compare_seasons"
    :description "Compare aggregate statistics of several seasons of one competition (default Serie A)."
    :inputSchema (schema ["competition" ["seasons" {:type "array" :items {:type "integer"}
                                                    :description "Season years, e.g. [2018, 2019]."}]]
                         ["seasons"])
    :handler compare-seasons}
   {:name "team_rankings"
    :description "Rank teams by win_rate, points, points_per_game, wins, goals_for, goals_against, goal_difference or losses; filter by venue (best home/away record), competition and season."
    :inputSchema (schema [["metric" {:type "string" :enum (vec (sort (keys q/ranking-metrics)))}]
                          "venue" "competition" "season" "date_from" "date_to"
                          ["min_matches" {:type "integer" :description "Ignore teams with fewer matches."}]
                          "limit"] [])
    :handler team-rankings}
   {:name "biggest_wins"
    :description "Largest winning margins, optionally by competition, season or team."
    :inputSchema (schema ["competition" "season" "team" "date_from" "date_to" "limit"] [])
    :handler biggest-wins}
   {:name "find_derbies"
    :description "Matches between traditional rivals (Fla-Flu, Derby Paulista, Grenal...), optionally by season, competition or team."
    :inputSchema (schema ["season" "competition" "team" "date_from" "date_to" "limit"] [])
    :handler find-derbies}
   {:name "search_players"
    :description "Search FIFA players by name, nationality, club, position (FIFA code or forward/midfielder/defender/goalkeeper), rating and age."
    :inputSchema (schema [["name" {:type "string"}] ["nationality" {:type "string" :description "e.g. Brazil"}]
                          ["club" {:type "string"}] ["position" {:type "string"}]
                          ["min_overall" {:type "integer"}] ["max_age" {:type "integer"}]
                          ["sort_by" {:type "string" :enum ["overall" "potential" "age" "name"]}]
                          "limit"] [])
    :handler search-players}
   {:name "player_details"
    :description "Full profile of one FIFA player (by name or FIFA id): ratings, physical data, contract and top attributes."
    :inputSchema (schema [["name" {:type "string"}] ["id" {:type "integer"}]] [])
    :handler player-details}
   {:name "brazilian_club_players"
    :description "Player count and average rating per Brazilian club in the FIFA data, optionally only one nationality (e.g. Brazil)."
    :inputSchema (schema [["nationality" {:type "string"}]] [])
    :handler club-players}
   {:name "list_teams"
    :description "List or search team names known to the dataset."
    :inputSchema (schema [["query" {:type "string"}] "competition" "limit"] [])
    :handler list-teams}
   {:name "dataset_info"
    :description "What data is loaded: files, competitions, season coverage and limits."
    :inputSchema (schema [] [])
    :handler dataset-info}])

(def by-name (into {} (map (juxt :name identity)) tools))

(defn call
  "Run a tool. Returns {:text s :error? bool}; bad input is reported as an
  error result rather than thrown."
  [db tool-name args]
  (if-let [{:keys [handler]} (by-name tool-name)]
    (try
      {:text (handler db (or args {})) :error? false}
      (catch clojure.lang.ExceptionInfo e
        (if (:user-error (ex-data e))
          {:text (ex-message e) :error? true}
          (throw e))))
    {:text (str "Unknown tool: " tool-name) :error? true :unknown? true}))
