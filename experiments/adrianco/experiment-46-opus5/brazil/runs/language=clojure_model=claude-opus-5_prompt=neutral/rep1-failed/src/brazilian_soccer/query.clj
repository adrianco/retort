(ns brazilian-soccer.query
  "Pure query functions over the knowledge graph built by `brazilian-soccer.data`.

  CONTEXT
  -------
  Everything an MCP tool needs to answer a question lives here, returning plain
  Clojure data; `brazilian-soccer.format` turns that data into the prose an LLM
  reads back to the user.  Keeping the two apart means the same query can be
  rendered as text today and as JSON tomorrow, and makes the BDD tests assert
  on values rather than on wording.

  Conventions
    * a team is always addressed by canonical id (\"flamengo|rj\"); use
      `resolve-team` to turn user input into one, it reports ambiguity instead
      of guessing between Atlético Mineiro, Athletico Paranaense and Atlético
      Goianiense.
    * matches with no score in the data (:played? false) are listed but never
      counted in a statistic.
    * every returned collection is ordered deterministically."
  (:require [clojure.string :as str]
            [brazilian-soccer.data :as data]
            [brazilian-soccer.names :as names]))

;; ---------------------------------------------------------------------------
;; Team resolution
;; ---------------------------------------------------------------------------

(defn- fold [s] (-> s str names/strip-accents str/lower-case str/trim))

(defn team [db id] (get-in db [:teams id]))

(defn resolve-team
  "Turn user input into a canonical team.  Returns
     {:status :ok        :team {...}}
     {:status :ambiguous :candidates [{...}]}
     {:status :not-found :candidates [{...}]}   ; best-effort suggestions"
  [db q]
  (let [teams   (:teams db)
        needle  (fold q)
        by-id   (get teams q)
        id      (data/resolve-name (:index db) q)
        direct  (or by-id (get teams id))
        base    (names/id-base id)
        same-base (->> (vals teams)
                       (filter #(= base (:base %)))
                       (sort-by (comp - :match-count)))
        partial* (->> (vals teams)
                      (filter (fn [t]
                                (or (str/includes? (fold (:display t)) needle)
                                    (str/includes? (:base t) needle)
                                    (some #(str/includes? (fold %) needle) (:variants t)))))
                      (sort-by (comp - :match-count)))]
    (cond
      direct            {:status :ok :team direct}
      (= 1 (count same-base)) {:status :ok :team (first same-base)}
      (seq same-base)   {:status :ambiguous :candidates (vec same-base)}
      (= 1 (count partial*)) {:status :ok :team (first partial*)}
      (seq partial*)    {:status :ambiguous :candidates (vec (take 10 partial*))}
      :else             {:status :not-found
                         :candidates (->> (vals teams)
                                          (filter #(str/includes? (fold (:display %))
                                                                  (first (str/split needle #"\s+"))))
                                          (sort-by (comp - :match-count))
                                          (take 5)
                                          vec)})))

(defn team-id!
  "Resolve or throw an ex-info the tool layer turns into a helpful message."
  [db q]
  (let [{:keys [status team candidates]} (resolve-team db q)]
    (case status
      :ok (:id team)
      :ambiguous (throw (ex-info (str "\"" q "\" matches several clubs: "
                                      (str/join ", " (map :display candidates))
                                      ". Please be more specific.")
                                 {:type :ambiguous-team :query q :candidates candidates}))
      (throw (ex-info (str "No club matching \"" q "\" in the dataset."
                           (when (seq candidates)
                             (str " Closest names: " (str/join ", " (map :display candidates)) ".")))
                      {:type :unknown-team :query q :candidates candidates})))))

(defn search-teams
  "Free-text club search, used by the list_teams tool."
  [db q]
  (let [needle (fold q)
        ts (vals (:teams db))]
    (->> (if (str/blank? (str q))
           ts
           (filter (fn [t] (or (str/includes? (fold (:display t)) needle)
                               (str/includes? (:base t) needle)
                               (some #(str/includes? (fold %) needle) (:variants t))))
                   ts))
         (sort-by (juxt (comp - :match-count) :display))
         vec)))

;; ---------------------------------------------------------------------------
;; Matches
;; ---------------------------------------------------------------------------

(defn played? [m] (:played? m))

(defn- in-range? [{:keys [date]} from to]
  (and (or (nil? from) (and date (>= (compare date from) 0)))
       (or (nil? to)   (and date (<= (compare date to) 0)))))

(defn- venue-ok? [m team-id venue]
  (case (or venue :any)
    :home (= team-id (:home-id m))
    :away (= team-id (:away-id m))
    true))

(defn find-matches
  "Filter the match graph.  Options:
     :team-id :opponent-id :competition :season :season-from :season-to
     :date-from :date-to :venue (:home/:away/:any) :round :stage
     :played-only? :sort (:date-desc/:date-asc/:goals-desc) :limit"
  [db {:keys [team-id opponent-id competition season season-from season-to
              date-from date-to venue round stage played-only? sort limit]}]
  (let [base (cond team-id     (get-in db [:by-team team-id] [])
                   opponent-id (get-in db [:by-team opponent-id] [])
                   :else       (:matches db))
        xs (cond->> base
             team-id      (filter #(venue-ok? % team-id venue))
             opponent-id  (filter #(or (= opponent-id (:home-id %))
                                       (= opponent-id (:away-id %))))
             competition  (filter #(= competition (:competition %)))
             season       (filter #(= season (:season %)))
             season-from  (filter #(>= (:season %) season-from))
             season-to    (filter #(<= (:season %) season-to))
             (or date-from date-to) (filter #(in-range? % date-from date-to))
             round        (filter #(= round (:round %)))
             stage        (filter #(= (fold stage) (fold (:stage %))))
             played-only? (filter played?))
        xs (case (or sort :date-desc)
             :date-desc  (reverse (sort-by (juxt :date :competition) xs))
             :date-asc   (sort-by (juxt :date :competition) xs)
             :goals-desc (sort-by (juxt (comp - #(or (:total-goals %) 0)) :date) xs)
             xs)]
    (vec (if limit (take limit xs) xs))))

(defn margin [m]
  (when (played? m) (abs (- (:home-goals m) (:away-goals m)))))

(defn outcome
  "Result of a match from one team's point of view: :win, :draw, :loss or nil."
  [team-id m]
  (when (played? m)
    (let [home? (= team-id (:home-id m))
          gf (if home? (:home-goals m) (:away-goals m))
          ga (if home? (:away-goals m) (:home-goals m))]
      (cond (> gf ga) :win (< gf ga) :loss :else :draw))))

(defn biggest-wins
  "Matches ordered by goal margin, then by goals scored.  When a team is given,
  only that team's own victories are considered - \"Santos' biggest wins\" must
  not answer with a 3-0 defeat."
  [db {:keys [team-id limit] :as opts}]
  (->> (find-matches db (assoc opts :played-only? true :limit nil))
       (filter (fn [m] (or (nil? team-id) (= :win (outcome team-id m)))))
       (sort-by (juxt (comp - #(margin %)) (comp - :total-goals) :date))
       (take (or limit 10))
       vec))

;; ---------------------------------------------------------------------------
;; Records and statistics
;; ---------------------------------------------------------------------------

(defn- tally [team-id matches]
  (reduce (fn [acc m]
            (let [home? (= team-id (:home-id m))
                  gf    (if home? (:home-goals m) (:away-goals m))
                  ga    (if home? (:away-goals m) (:home-goals m))
                  outcome (cond (> gf ga) :win (< gf ga) :loss :else :draw)]
              (-> acc
                  (update :matches inc)
                  (update outcome inc)
                  (update :goals-for + gf)
                  (update :goals-against + ga)
                  (update (if home? :home-matches :away-matches) inc))))
          {:matches 0 :win 0 :draw 0 :loss 0 :goals-for 0 :goals-against 0
           :home-matches 0 :away-matches 0}
          (filter played? matches)))

(defn record
  "Win/draw/loss record of a team over a collection of matches."
  [team-id matches]
  (let [{:keys [matches win draw loss goals-for goals-against] :as t} (tally team-id matches)]
    (assoc t
           :wins win :draws draw :losses loss
           :goal-difference (- goals-for goals-against)
           :points (+ (* 3 win) draw)
           :win-rate (if (pos? matches) (double (/ win matches)) 0.0)
           :points-per-match (if (pos? matches) (double (/ (+ (* 3 win) draw) matches)) 0.0)
           :goals-per-match (if (pos? matches) (double (/ goals-for matches)) 0.0))))

(defn team-summary
  "Everything the team_stats tool reports for one club."
  [db team-id opts]
  (let [ms   (find-matches db (assoc opts :team-id team-id :limit nil))
        home (filter #(= team-id (:home-id %)) ms)
        away (filter #(= team-id (:away-id %)) ms)]
    {:team    (team db team-id)
     :filters (select-keys opts [:competition :season :season-from :season-to
                                 :date-from :date-to :venue])
     :overall (record team-id ms)
     :home    (record team-id home)
     :away    (record team-id away)
     :by-competition (->> (group-by :competition ms)
                          (map (fn [[c cms]] [c (record team-id cms)]))
                          (sort-by (comp - :matches second))
                          vec)
     :by-season (->> (group-by :season ms)
                     (map (fn [[s sms]] [s (record team-id sms)]))
                     (sort-by first)
                     vec)
     :biggest-win  (->> ms
                        (filter #(= :win (outcome team-id %)))
                        (sort-by (juxt (comp - margin) :date))
                        first)
     :recent  (vec (take 5 (reverse (sort-by :date ms))))
     :matches ms}))

(defn head-to-head
  "Complete head-to-head between two clubs."
  [db a-id b-id opts]
  (let [ms (find-matches db (merge opts {:team-id a-id :opponent-id b-id :limit nil}))
        played (filter played? ms)]
    {:team-a (team db a-id)
     :team-b (team db b-id)
     :matches ms
     :played (count played)
     :a-record (record a-id ms)
     :b-record (record b-id ms)
     :draws (count (filter #(= :draw (:result %)) played))
     :by-competition (->> (group-by :competition played)
                          (map (fn [[c cms]] [c {:matches (count cms)
                                                 :a (record a-id cms)
                                                 :b (record b-id cms)}]))
                          (sort-by (comp - :matches second))
                          vec)
     :first-meeting (first (sort-by :date played))
     :last-meeting  (last (sort-by :date played))
     :biggest (->> played (sort-by (comp - margin)) first)}))

;; ---------------------------------------------------------------------------
;; Competitions
;; ---------------------------------------------------------------------------

(defn league? [competition] (get-in data/competitions [competition :league?]))

(defn standings
  "League table calculated from the match results in the dataset.
  3 points per win, ranked on points, wins, goal difference, goals for."
  [db competition season]
  (let [ms (find-matches db {:competition competition :season season :played-only? true})
        ids (distinct (mapcat (juxt :home-id :away-id) ms))
        rows (for [id ids
                   :let [team-ms (filter #(or (= id (:home-id %)) (= id (:away-id %))) ms)
                         r (record id team-ms)]]
               (assoc r
                      :team-id id
                      :team (:display (team db id))
                      :home (record id (filter #(= id (:home-id %)) team-ms))
                      :away (record id (filter #(= id (:away-id %)) team-ms))))]
    {:competition competition
     :season season
     :match-count (count ms)
     :table (->> rows
                 (sort-by (juxt (comp - :points) (comp - :wins)
                                (comp - :goal-difference) (comp - :goals-for) :team))
                 (map-indexed (fn [i r] (assoc r :position (inc i))))
                 vec)}))

(def ranking-metrics
  {:points-per-match :points-per-match :win-rate :win-rate :points :points
   :wins :wins :goals-for :goals-for :goal-difference :goal-difference
   :goals-per-match :goals-per-match :matches :matches})

(defn team-rankings
  "Rank every club by a metric over the filtered matches.  With :venue :home
  this answers \"which team has the best home record?\"; with :metric
  :goals-for it answers \"which team scored the most goals?\"."
  [db {:keys [venue metric min-matches limit] :as opts}]
  (let [venue   (or venue :any)
        metric  (get ranking-metrics (or metric :points-per-match) :points-per-match)
        ms      (find-matches db (assoc (dissoc opts :venue :metric :min-matches :limit)
                                        :played-only? true :limit nil))
        grouped (reduce (fn [m mt]
                          (cond-> m
                            (not= venue :away) (update (:home-id mt) (fnil conj []) mt)
                            (not= venue :home) (update (:away-id mt) (fnil conj []) mt)))
                        {} ms)
        rows    (for [[id team-ms] grouped
                      :let [r (record id team-ms)]
                      :when (>= (:matches r) (or min-matches 20))]
                  (assoc r :team-id id :team (:display (team db id))))]
    {:metric metric
     :venue venue
     :min-matches (or min-matches 20)
     :rows (->> rows
                (sort-by (juxt (comp - metric) (comp - :points) :team))
                (take (or limit 10))
                (map-indexed (fn [i r] (assoc r :position (inc i))))
                vec)}))

(defn competition-summary
  "Aggregate statistics for a competition, optionally for one season."
  [db competition season]
  (let [ms (find-matches db (cond-> {:played-only? true}
                              competition (assoc :competition competition)
                              season      (assoc :season season)))
        n  (count ms)
        goals (reduce + 0 (map :total-goals ms))
        results (frequencies (map :result ms))]
    {:competition competition
     :season season
     :matches n
     :goals goals
     :goals-per-match (if (pos? n) (double (/ goals n)) 0.0)
     :home-wins (get results :home-win 0)
     :away-wins (get results :away-win 0)
     :draws     (get results :draw 0)
     :home-win-rate (if (pos? n) (double (/ (get results :home-win 0) n)) 0.0)
     :away-win-rate (if (pos? n) (double (/ (get results :away-win 0) n)) 0.0)
     :draw-rate     (if (pos? n) (double (/ (get results :draw 0) n)) 0.0)
     :seasons (vec (sort (distinct (map :season ms))))
     :teams (count (distinct (mapcat (juxt :home-id :away-id) ms)))
     :biggest-win (first (sort-by (comp - margin) ms))
     :highest-scoring (first (sort-by (comp - :total-goals) ms))
     :top-scoring-teams
     (->> (mapcat (fn [m] [[(:home-id m) (:home-goals m)] [(:away-id m) (:away-goals m)]]) ms)
          (reduce (fn [acc [id g]] (update acc id (fnil + 0) g)) {})
          (sort-by (comp - val))
          (take 10)
          (mapv (fn [[id g]] {:team-id id :team (:display (team db id)) :goals g})))}))

(defn finals
  "Knockout finals: Libertadores rows tagged \"final\", or the last round of a
  Copa do Brasil season.  The cup file numbers rounds instead of naming them,
  so the final is the highest round of the season - but only when that round
  holds one or two matches (a single game or a two-legged tie).  Seasons whose
  data stops earlier, or that come from the file without round numbers, have no
  identifiable final and are reported separately."
  [db competition season]
  (let [ms (find-matches db (cond-> {:competition competition :sort :date-asc}
                              season (assoc :season season)))]
    (case competition
      :libertadores {:finals (filterv #(= "final" (some-> (:stage %) str/lower-case)) ms)
                     :incomplete-seasons []}
      :copa-do-brasil
      (let [by-season (group-by :season ms)
            resolved  (for [[s sms] (sort-by key by-season)
                            :let [rounds (keep :round sms)
                                  final-round (when (seq rounds) (apply max rounds))
                                  candidates (when final-round
                                               (filter #(= final-round (:round %)) sms))]]
                        [s (when (<= 1 (count candidates) 2) candidates)])]
        {:finals (vec (sort-by :date (mapcat second (filter second resolved))))
         :incomplete-seasons (vec (keep (fn [[s f]] (when-not f s)) resolved))})
      {:finals (vec ms) :incomplete-seasons []})))

(defn seasons
  "Seasons available for a competition (or for everything)."
  [db competition]
  (->> (:matches db)
       (filter #(or (nil? competition) (= competition (:competition %))))
       (map :season)
       distinct
       sort
       vec))

;; ---------------------------------------------------------------------------
;; Derbies
;; ---------------------------------------------------------------------------

(def rivalries
  [{:name "Fla-Flu"                 :teams ["flamengo|rj" "fluminense|rj"]}
   {:name "Clássico dos Milhões"    :teams ["flamengo|rj" "vasco da gama|rj"]}
   {:name "Clássico da Rivalidade"  :teams ["botafogo|rj" "flamengo|rj"]}
   {:name "Clássico Vovô"           :teams ["botafogo|rj" "fluminense|rj"]}
   {:name "Clássico dos Gigantes"   :teams ["botafogo|rj" "vasco da gama|rj"]}
   {:name "Derby Paulista"          :teams ["corinthians|sp" "palmeiras|sp"]}
   {:name "Majestoso"               :teams ["corinthians|sp" "sao paulo|sp"]}
   {:name "Clássico Alvinegro"      :teams ["corinthians|sp" "santos|sp"]}
   {:name "Choque-Rei"              :teams ["palmeiras|sp" "sao paulo|sp"]}
   {:name "Clássico da Saudade"     :teams ["palmeiras|sp" "santos|sp"]}
   {:name "San-São"                 :teams ["santos|sp" "sao paulo|sp"]}
   {:name "Gre-Nal"                 :teams ["gremio|rs" "internacional|rs"]}
   {:name "Clássico Mineiro"        :teams ["atletico|mg" "cruzeiro|mg"]}
   {:name "Atletiba"                :teams ["atletico|pr" "coritiba|pr"]}
   {:name "Ba-Vi"                   :teams ["bahia|ba" "vitoria|ba"]}
   {:name "Clássico dos Clássicos"  :teams ["sport|pe" "nautico|pe"]}
   {:name "Clássico das Multidões"  :teams ["sport|pe" "santa cruz|pe"]}
   {:name "Clássico-Rei"            :teams ["ceara|ce" "fortaleza|ce"]}
   {:name "Re-Pa"                   :teams ["remo|pa" "paysandu|pa"]}])

(defn derby-of
  "The rivalry a match belongs to, if any."
  [m]
  (let [pair (set [(:home-id m) (:away-id m)])]
    (some #(when (= pair (set (:teams %))) %) rivalries)))

(defn derbies
  "All derby matches matching the filters, tagged with the rivalry name."
  [db opts]
  (->> (find-matches db (assoc opts :limit nil))
       (keep (fn [m] (when-let [d (derby-of m)] (assoc m :derby (:name d)))))
       (sort-by :date)
       reverse
       (take (or (:limit opts) 50))
       vec))

;; ---------------------------------------------------------------------------
;; Players
;; ---------------------------------------------------------------------------

(defn- matches-text? [needle s]
  (and s (str/includes? (fold s) needle)))

(defn resolve-fifa-clubs
  "FIFA club names a user's club query refers to.  The club linked to the
  canonical club wins, then an exact name match, then a substring - otherwise
  \"Santos\" would drag in Santos Laguna of Mexico."
  [db club-query]
  (let [needle (fold club-query)
        team-id (try (team-id! db club-query) (catch Exception _ nil))
        all (filter some? (keys (:players-by-club db)))]
    (or (seq (filter #(and team-id (= team-id (get-in db [:club->team-id %]))) all))
        (seq (filter #(= needle (fold %)) all))
        (seq (filter #(str/includes? (fold %) needle) all)))))

(defn search-players
  "Options: :name :nationality :club :position :position-group :min-overall
   :max-overall :min-age :max-age :foot :sort (:overall/:potential/:age/:name)
   :limit"
  [db {:keys [name nationality club position position-group min-overall
              max-overall min-age max-age foot sort limit]}]
  (let [pos-group (when position-group (keyword (str/lower-case (clojure.core/name position-group))))
        clubs (when club (set (resolve-fifa-clubs db club)))
        xs (cond->> (:players db)
             name          (filter #(matches-text? (fold name) (:name %)))
             nationality   (filter #(= (fold nationality) (fold (:nationality %))))
             club          (filter #(contains? clubs (:club %)))
             position      (filter #(= (str/upper-case position) (str (:position %))))
             pos-group     (filter #(= pos-group (data/position-group (:position %))))
             min-overall   (filter #(>= (or (:overall %) 0) min-overall))
             max-overall   (filter #(<= (or (:overall %) 0) max-overall))
             min-age       (filter #(>= (or (:age %) 0) min-age))
             max-age       (filter #(<= (or (:age %) 999) max-age))
             foot          (filter #(= (fold foot) (fold (:foot %)))))
        xs (case (or sort :overall)
             :overall   (sort-by (juxt (comp - #(or (:overall %) 0)) :name) xs)
             :potential (sort-by (juxt (comp - #(or (:potential %) 0)) :name) xs)
             :age       (sort-by (juxt #(or (:age %) 0) :name) xs)
             :name      (sort-by :name xs)
             xs)]
    {:total (count xs)
     :players (vec (take (or limit 20) xs))}))

(defn player-profile
  "Best match for a player name, with the club linked to the match graph."
  [db name*]
  (let [needle (fold name*)
        candidates (->> (:players db)
                        (filter #(matches-text? needle (:name %)))
                        (sort-by (juxt #(if (= needle (fold (:name %))) 0 1)
                                       #(count (:name %))
                                       (comp - #(or (:overall %) 0)))))
        p (first candidates)]
    (when p
      {:player p
       :team-id (get-in db [:club->team-id (:club p)])
       :alternatives (vec (take 5 (rest candidates)))})))

(defn brazilian-club-squads
  "FIFA squads of the clubs that also appear in the match data."
  [db]
  (->> (:club->team-id db)
       (map (fn [[club team-id]]
              (let [squad (get-in db [:players-by-club club])
                    ratings (keep :overall squad)]
                {:club club
                 :team-id team-id
                 :team (:display (team db team-id))
                 :players (count squad)
                 :brazilians (count (filter #(= "Brazil" (:nationality %)) squad))
                 :avg-overall (when (seq ratings)
                                (double (/ (reduce + ratings) (count ratings))))
                 :top (->> squad (sort-by (comp - #(or (:overall %) 0))) (take 3) vec)})))
       (sort-by (comp - :avg-overall))
       vec))

(defn club-squad
  "Squad for a club named either as it appears in FIFA data or as a canonical
  club.  Returns nil when the club is not part of the FIFA snapshot."
  [db club-query]
  (let [clubs (resolve-fifa-clubs db club-query)
        squad (vec (mapcat #(get-in db [:players-by-club %]) clubs))]
    (when (seq squad)
      (let [ratings (keep :overall squad)]
        {:clubs (vec clubs)
         :team-id (some #(get-in db [:club->team-id %]) clubs)
         :players (vec (sort-by (comp - #(or (:overall %) 0)) squad))
         :player-count (count squad)
         :brazilians (count (filter #(= "Brazil" (:nationality %)) squad))
         :avg-overall (when (seq ratings) (double (/ (reduce + ratings) (count ratings))))
         :nationalities (->> squad (map :nationality) frequencies
                             (sort-by (comp - val)) (take 5) vec)}))))

;; ---------------------------------------------------------------------------
;; Dataset overview
;; ---------------------------------------------------------------------------

(defn dataset-info [db]
  (let [ms (:matches db)]
    {:data-dir (:dir db)
     :sources (:sources db)
     :stats (:stats db)
     :matches (count ms)
     :played (count (filter played? ms))
     :teams (count (:teams db))
     :players (count (:players db))
     :linked-clubs (count (:club->team-id db))
     :by-competition (->> (group-by :competition ms)
                          (map (fn [[c cms]]
                                 {:competition c
                                  :name (data/competition-name c)
                                  :matches (count cms)
                                  :seasons [(apply min (map :season cms))
                                            (apply max (map :season cms))]}))
                          (sort-by :competition)
                          vec)
     :date-range (let [ds (sort (keep :date ms))] [(first ds) (last ds)])}))
