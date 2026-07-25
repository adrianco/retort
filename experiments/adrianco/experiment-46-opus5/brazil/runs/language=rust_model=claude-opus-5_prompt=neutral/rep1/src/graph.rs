//! The knowledge graph.
//!
//! Nodes are teams, matches, players and competitions; edges are the
//! relationships between them (`Team -hosted-> Match -part_of-> Competition`,
//! `Player -plays_for-> Team`). Adjacency is materialised as index vectors at
//! build time, so every traversal in [`crate::queries`] is a slice lookup.
//!
//! Two data-quality problems are solved here:
//!
//! 1. **Team identity** – 700+ raw spellings collapse onto ~600 canonical
//!    clubs via [`crate::normalize`], plus a merge pass that folds an
//!    unqualified spelling (`Santos`) into a state-qualified one (`Santos-SP`)
//!    when that mapping is unambiguous.
//! 2. **Overlapping sources** – four files describe Série A and two describe
//!    the Copa do Brasil. For each (competition, season) the highest-priority
//!    file wins and its rows are flagged `canonical`; the rest stay queryable
//!    but are excluded from aggregates so nothing is counted twice.

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::path::Path;
use std::time::Instant;

use crate::data::{self, DataError, PendingMatch, SourceReport};
use crate::model::*;
use crate::normalize::{best_display_name, edit_distance, normalize_query, simplify, text_key};

/// True when `needle` appears in `haystack` as a run of whole words.
fn contains_words(haystack: &str, needle: &str) -> bool {
    let haystack: Vec<&str> = haystack.split_whitespace().collect();
    let needle: Vec<&str> = needle.split_whitespace().collect();
    if needle.is_empty() || needle.len() > haystack.len() {
        return false;
    }
    haystack
        .windows(needle.len())
        .any(|window| window == needle)
}

/// Reference to a node in the knowledge graph.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NodeRef {
    Team(TeamId),
    Match(MatchId),
    Player(PlayerId),
    Competition(Competition),
}

/// Edge label.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Relation {
    /// Team -> Match (team was the home side)
    Hosted,
    /// Team -> Match (team was the away side)
    Visited,
    /// Match -> Team
    HomeTeam,
    /// Match -> Team
    AwayTeam,
    /// Match -> Competition
    PartOf,
    /// Competition -> Match
    Includes,
    /// Player -> Team
    PlaysFor,
    /// Team -> Player
    HasPlayer,
}

impl Relation {
    pub fn name(&self) -> &'static str {
        match self {
            Relation::Hosted => "hosted",
            Relation::Visited => "visited",
            Relation::HomeTeam => "home_team",
            Relation::AwayTeam => "away_team",
            Relation::PartOf => "part_of",
            Relation::Includes => "includes",
            Relation::PlaysFor => "plays_for",
            Relation::HasPlayer => "has_player",
        }
    }
}

/// Outcome of turning a user-supplied club name into a graph node.
#[derive(Debug, Clone)]
pub enum Resolution {
    Unique(TeamId),
    /// Several clubs share the base name (e.g. `Atlético` -> MG/GO/PR).
    Ambiguous(Vec<TeamId>),
    /// Nothing matched; the payload holds "did you mean" suggestions.
    NotFound(Vec<TeamId>),
}

/// Aggregate size of the graph, surfaced by the `dataset_overview` tool.
#[derive(Debug, Clone)]
pub struct GraphStats {
    pub teams: usize,
    pub matches: usize,
    pub canonical_matches: usize,
    pub players: usize,
    pub competitions: usize,
    pub edges: usize,
}

/// Immutable, fully indexed knowledge graph over the Kaggle datasets.
pub struct KnowledgeGraph {
    pub teams: Vec<Team>,
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    pub reports: Vec<SourceReport>,
    pub load_millis: u128,
    pub duplicate_rows_dropped: usize,

    team_by_key: HashMap<String, TeamId>,
    team_by_base: HashMap<String, Vec<TeamId>>,
    team_by_alias: HashMap<String, TeamId>,
    team_matches: Vec<Vec<MatchId>>,
    team_home_matches: Vec<Vec<MatchId>>,
    team_away_matches: Vec<Vec<MatchId>>,
    competition_matches: HashMap<Competition, Vec<MatchId>>,
    competition_seasons: BTreeMap<Competition, BTreeSet<i32>>,
    players_by_team: HashMap<TeamId, Vec<PlayerId>>,
    player_tokens: HashMap<String, Vec<PlayerId>>,
    players_by_nationality: HashMap<String, Vec<PlayerId>>,
}

impl KnowledgeGraph {
    /// Loads every CSV in `dir` and builds the graph.
    pub fn load(dir: &Path) -> Result<KnowledgeGraph, DataError> {
        let started = Instant::now();
        let raw = data::load_all(dir)?;
        let mut graph = KnowledgeGraph::build(raw.matches, raw.players, raw.reports);
        graph.load_millis = started.elapsed().as_millis();
        Ok(graph)
    }

    fn build(
        pending: Vec<PendingMatch>,
        players: Vec<data::PendingPlayer>,
        reports: Vec<SourceReport>,
    ) -> KnowledgeGraph {
        // ---- 1. team identities -------------------------------------------------
        let mut variants: HashMap<String, HashMap<String, usize>> = HashMap::new();
        let mut key_meta: HashMap<String, (String, Option<String>, Option<String>)> =
            HashMap::new();
        for m in &pending {
            for (key, raw) in [(&m.home_key, &m.home_raw), (&m.away_key, &m.away_raw)] {
                let id = key.id();
                *variants
                    .entry(id.clone())
                    .or_default()
                    .entry(raw.clone())
                    .or_insert(0) += 1;
                key_meta
                    .entry(id)
                    .or_insert_with(|| (key.base.clone(), key.state.clone(), key.country.clone()));
            }
        }

        // Fold bare spellings into a qualified club when that is unambiguous:
        // `Santos` -> `santos-SP`, but `América` stays ambiguous (MG and RN).
        let mut qualified_by_base: HashMap<String, Vec<String>> = HashMap::new();
        for (id, (base, state, country)) in &key_meta {
            if state.is_some() || country.is_some() {
                qualified_by_base
                    .entry(base.clone())
                    .or_default()
                    .push(id.clone());
            }
        }
        let mut redirect: HashMap<String, String> = HashMap::new();
        for (id, (base, state, country)) in &key_meta {
            if state.is_none() && country.is_none() {
                if let Some(candidates) = qualified_by_base.get(base) {
                    if candidates.len() == 1 {
                        redirect.insert(id.clone(), candidates[0].clone());
                    }
                }
            }
        }

        let mut merged_variants: HashMap<String, HashMap<String, usize>> = HashMap::new();
        for (id, spellings) in variants {
            let target = redirect.get(&id).cloned().unwrap_or(id);
            let entry = merged_variants.entry(target).or_default();
            for (spelling, count) in spellings {
                *entry.entry(spelling).or_insert(0) += count;
            }
        }

        let mut team_keys: Vec<String> = merged_variants.keys().cloned().collect();
        team_keys.sort();
        let mut teams = Vec::with_capacity(team_keys.len());
        let mut team_by_key = HashMap::new();
        let mut team_by_base: HashMap<String, Vec<TeamId>> = HashMap::new();
        let mut team_by_alias: HashMap<String, TeamId> = HashMap::new();
        // Several clubs clean down to the same display name ("Botafogo" exists
        // in RJ, SP and PB; "Fluminense" in RJ and PI). A dominant club keeps
        // the bare name and the rest carry their state, so common answers stay
        // readable while remaining unambiguous.
        let mut display_by_key: HashMap<String, String> = HashMap::new();
        let mut collisions: HashMap<String, Vec<(String, usize)>> = HashMap::new();
        for key in &team_keys {
            let (base, _, _) = &key_meta[key];
            let name = best_display_name(&merged_variants[key], base);
            let appearances: usize = merged_variants[key].values().sum();
            collisions
                .entry(simplify(&name))
                .or_default()
                .push((key.clone(), appearances));
            display_by_key.insert(key.clone(), name);
        }
        let mut needs_qualifier: HashSet<String> = HashSet::new();
        for group in collisions.values_mut() {
            if group.len() < 2 {
                continue;
            }
            group.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
            let dominant = group[0].1 >= 5 * group[1].1.max(1);
            for (idx, (key, _)) in group.iter().enumerate() {
                if idx > 0 || !dominant {
                    needs_qualifier.insert(key.clone());
                }
            }
        }

        for key in team_keys {
            let id = teams.len();
            let spellings = &merged_variants[&key];
            let (base, state, country) = key_meta[&key].clone();
            let mut aliases: Vec<String> = spellings.keys().cloned().collect();
            aliases.sort();
            let mut name = display_by_key[&key].clone();
            if needs_qualifier.contains(&key) {
                if let Some(qualifier) = state.as_deref().or(country.as_deref()) {
                    name = format!("{name}-{qualifier}");
                }
            }
            for alias in &aliases {
                team_by_alias.entry(simplify(alias)).or_insert(id);
            }
            team_by_alias.entry(simplify(&name)).or_insert(id);
            team_by_key.insert(key.clone(), id);
            team_by_base.entry(base.clone()).or_default().push(id);
            teams.push(Team {
                id,
                key,
                name,
                state,
                country,
                aliases,
            });
        }
        let resolve_key = |key: &str| -> TeamId {
            let target = redirect.get(key).map(String::as_str).unwrap_or(key);
            team_by_key[target]
        };

        // ---- 2. matches ---------------------------------------------------------
        // Within a file, identical fixtures (same date, teams and score) are
        // duplicate rows and only counted once.
        let mut seen: HashSet<(Source, Competition, i32, Option<Date>, TeamId, TeamId)> =
            HashSet::new();
        let mut duplicate_rows_dropped = 0usize;
        let mut matches: Vec<Match> = Vec::with_capacity(pending.len());
        for m in &pending {
            let home = resolve_key(&m.home_key.id());
            let away = resolve_key(&m.away_key.id());
            let fingerprint = (m.source, m.competition, m.season, m.date, home, away);
            if !seen.insert(fingerprint) {
                duplicate_rows_dropped += 1;
                continue;
            }
            matches.push(Match {
                id: 0,
                competition: m.competition,
                season: m.season,
                date: m.date,
                time: m.time.clone(),
                home,
                away,
                home_goals: m.home_goals,
                away_goals: m.away_goals,
                round: m.round.clone(),
                stage: m.stage.clone(),
                venue: m.venue.clone(),
                source: m.source,
                canonical: true,
                stats: m.stats.clone(),
            });
        }
        matches.sort_by(|a, b| {
            a.date
                .cmp(&b.date)
                .then(a.competition.cmp(&b.competition))
                .then(a.home.cmp(&b.home))
                .then(a.away.cmp(&b.away))
                .then(a.source.cmp(&b.source))
        });
        for (idx, m) in matches.iter_mut().enumerate() {
            m.id = idx;
        }

        // ---- 3. canonical source per (competition, season) ----------------------
        // The preferred file wins unless it is materially less complete than a
        // rival: `Brasileirao_Matches.csv` was scraped during the 2022 season
        // and carries 81 fixtures with `NA` scores, so for that season the
        // BR-Football file becomes canonical.
        const COVERAGE_TOLERANCE: f64 = 0.95;
        let mut played_by_slot: HashMap<(Competition, i32), HashMap<Source, usize>> =
            HashMap::new();
        for m in &matches {
            let entry = played_by_slot
                .entry((m.competition, m.season))
                .or_default()
                .entry(m.source)
                .or_insert(0);
            if m.played() {
                *entry += 1;
            }
        }
        let mut canonical_source: HashMap<(Competition, i32), Source> = HashMap::new();
        for (slot, played) in &played_by_slot {
            let best = played.values().copied().max().unwrap_or(0) as f64;
            let chosen = Source::priority_for(slot.0)
                .iter()
                .find(|source| {
                    played
                        .get(source)
                        .map(|count| *count as f64 >= best * COVERAGE_TOLERANCE)
                        .unwrap_or(false)
                })
                .copied()
                .or_else(|| {
                    played
                        .iter()
                        .max_by_key(|(source, count)| (**count, std::cmp::Reverse(**source)))
                        .map(|(source, _)| *source)
                });
            if let Some(chosen) = chosen {
                canonical_source.insert(*slot, chosen);
            }
        }
        for m in &mut matches {
            m.canonical = canonical_source
                .get(&(m.competition, m.season))
                .map(|s| *s == m.source)
                .unwrap_or(true);
        }

        // ---- 4. adjacency -------------------------------------------------------
        let mut team_matches = vec![Vec::new(); teams.len()];
        let mut team_home_matches = vec![Vec::new(); teams.len()];
        let mut team_away_matches = vec![Vec::new(); teams.len()];
        let mut competition_matches: HashMap<Competition, Vec<MatchId>> = HashMap::new();
        let mut competition_seasons: BTreeMap<Competition, BTreeSet<i32>> = BTreeMap::new();
        for m in &matches {
            team_matches[m.home].push(m.id);
            team_home_matches[m.home].push(m.id);
            if m.away != m.home {
                team_matches[m.away].push(m.id);
            }
            team_away_matches[m.away].push(m.id);
            competition_matches
                .entry(m.competition)
                .or_default()
                .push(m.id);
            competition_seasons
                .entry(m.competition)
                .or_default()
                .insert(m.season);
        }

        // ---- 5. players ---------------------------------------------------------
        // The FIFA club column is worldwide, so a bare foreign name must not be
        // folded onto a same-named Brazilian side ("Boavista FC" of Porto is
        // not Boavista-RJ). A club is linked only when it resolves to a
        // Brazilian club *and* its FIFA squad is overwhelmingly Brazilian,
        // which is true of every club in the Brazilian league and of no
        // European club.
        const BRAZILIAN_SQUAD_SHARE: f64 = 0.6;
        let mut squad_nationalities: HashMap<&str, (usize, usize)> = HashMap::new();
        for player in &players {
            if let Some(club) = player.club.as_deref() {
                let entry = squad_nationalities.entry(club).or_insert((0, 0));
                entry.0 += 1;
                if player.nationality == "Brazil" {
                    entry.1 += 1;
                }
            }
        }
        let resolve_club = |club: &str| -> Option<TeamId> {
            let (total, brazilians) = squad_nationalities.get(club).copied()?;
            if total == 0 || (brazilians as f64 / total as f64) < BRAZILIAN_SQUAD_SHARE {
                return None;
            }
            let key = normalize_query(club);
            let direct = team_by_key.get(&key.id()).copied().or_else(|| {
                if key.is_bare() {
                    team_by_base
                        .get(&key.base)
                        .filter(|ids| ids.len() == 1)
                        .map(|ids| ids[0])
                } else {
                    None
                }
            })?;
            teams[direct].state.as_ref().map(|_| direct)
        };

        let mut player_list = Vec::with_capacity(players.len());
        let mut players_by_team: HashMap<TeamId, Vec<PlayerId>> = HashMap::new();
        let mut player_tokens: HashMap<String, Vec<PlayerId>> = HashMap::new();
        let mut players_by_nationality: HashMap<String, Vec<PlayerId>> = HashMap::new();
        let club_links: Vec<Option<TeamId>> = players
            .iter()
            .map(|player| player.club.as_deref().and_then(resolve_club))
            .collect();
        for (idx, p) in players.into_iter().enumerate() {
            let club_team = club_links[idx];
            let player = Player {
                id: idx,
                fifa_id: p.fifa_id,
                name: p.name,
                age: p.age,
                nationality: p.nationality,
                overall: p.overall,
                potential: p.potential,
                club: p.club,
                club_team,
                position: p.position,
                jersey_number: p.jersey_number,
                height: p.height,
                weight: p.weight,
                value: p.value,
                wage: p.wage,
                preferred_foot: p.preferred_foot,
                attributes: p.attributes,
            };
            if let Some(team) = club_team {
                players_by_team.entry(team).or_default().push(idx);
            }
            let full = text_key(&player.name);
            player_tokens.entry(full.clone()).or_default().push(idx);
            for token in full.split_whitespace() {
                if token.len() > 1 {
                    player_tokens
                        .entry(token.to_string())
                        .or_default()
                        .push(idx);
                }
            }
            players_by_nationality
                .entry(text_key(&player.nationality))
                .or_default()
                .push(idx);
            player_list.push(player);
        }

        KnowledgeGraph {
            teams,
            matches,
            players: player_list,
            reports,
            load_millis: 0,
            duplicate_rows_dropped,
            team_by_key,
            team_by_base,
            team_by_alias,
            team_matches,
            team_home_matches,
            team_away_matches,
            competition_matches,
            competition_seasons,
            players_by_team,
            player_tokens,
            players_by_nationality,
        }
    }

    // ---- lookups ---------------------------------------------------------------

    pub fn team(&self, id: TeamId) -> &Team {
        &self.teams[id]
    }

    pub fn match_by_id(&self, id: MatchId) -> &Match {
        &self.matches[id]
    }

    pub fn player(&self, id: PlayerId) -> &Player {
        &self.players[id]
    }

    pub fn team_by_key(&self, key: &str) -> Option<TeamId> {
        self.team_by_key.get(key).copied()
    }

    /// All matches involving a team, chronologically ordered.
    pub fn team_matches(&self, id: TeamId) -> &[MatchId] {
        &self.team_matches[id]
    }

    pub fn team_home_matches(&self, id: TeamId) -> &[MatchId] {
        &self.team_home_matches[id]
    }

    pub fn team_away_matches(&self, id: TeamId) -> &[MatchId] {
        &self.team_away_matches[id]
    }

    pub fn competition_matches(&self, competition: Competition) -> &[MatchId] {
        self.competition_matches
            .get(&competition)
            .map(Vec::as_slice)
            .unwrap_or(&[])
    }

    pub fn seasons(&self, competition: Competition) -> Vec<i32> {
        self.competition_seasons
            .get(&competition)
            .map(|s| s.iter().copied().collect())
            .unwrap_or_default()
    }

    pub fn competitions(&self) -> Vec<Competition> {
        self.competition_seasons.keys().copied().collect()
    }

    pub fn players_of_team(&self, id: TeamId) -> &[PlayerId] {
        self.players_by_team
            .get(&id)
            .map(Vec::as_slice)
            .unwrap_or(&[])
    }

    pub fn players_of_nationality(&self, nationality: &str) -> &[PlayerId] {
        self.players_by_nationality
            .get(&text_key(nationality))
            .map(Vec::as_slice)
            .unwrap_or(&[])
    }

    /// Players whose name contains the given token(s), best matches first.
    pub fn players_by_name(&self, query: &str) -> Vec<PlayerId> {
        let key = text_key(query);
        if key.is_empty() {
            return Vec::new();
        }
        let mut scored: Vec<(i32, PlayerId)> = Vec::new();
        let mut seen = HashSet::new();
        if let Some(exact) = self.player_tokens.get(&key) {
            for id in exact {
                if seen.insert(*id) {
                    let score = if text_key(&self.players[*id].name) == key {
                        0
                    } else {
                        1
                    };
                    scored.push((score, *id));
                }
            }
        }
        // Substring fallback ("gabriel barbosa" vs "Gabriel Barbosa Almeida").
        if scored.is_empty() || key.contains(' ') {
            for (id, player) in self.players.iter().enumerate() {
                let name = text_key(&player.name);
                if name.contains(&key) && seen.insert(id) {
                    scored.push((2, id));
                }
            }
        }
        if scored.is_empty() {
            for (id, player) in self.players.iter().enumerate() {
                let name = text_key(&player.name);
                if name
                    .split_whitespace()
                    .any(|token| edit_distance(token, &key) <= 1 && token.len() > 3)
                    && seen.insert(id)
                {
                    scored.push((3, id));
                }
            }
        }
        scored.sort_by(|a, b| {
            a.0.cmp(&b.0)
                .then(self.players[b.1].overall.cmp(&self.players[a.1].overall))
                .then(self.players[a.1].name.cmp(&self.players[b.1].name))
        });
        scored.into_iter().map(|(_, id)| id).collect()
    }

    /// Players whose name shares tokens with the query, for "did you mean"
    /// messages when a player is absent from the FIFA snapshot.
    pub fn similar_player_names(&self, query: &str, limit: usize) -> Vec<PlayerId> {
        let key = text_key(query);
        let tokens: Vec<&str> = key.split_whitespace().filter(|t| t.len() > 2).collect();
        if tokens.is_empty() {
            return Vec::new();
        }
        let mut scored: Vec<(usize, i32, PlayerId)> = self
            .players
            .iter()
            .filter_map(|player| {
                let name = text_key(&player.name);
                let hits = tokens
                    .iter()
                    .filter(|token| {
                        name.split_whitespace()
                            .any(|word| word == **token || edit_distance(word, token) <= 1)
                    })
                    .count();
                (hits > 0).then_some((hits, player.overall, player.id))
            })
            .collect();
        scored.sort_by(|a, b| b.0.cmp(&a.0).then(b.1.cmp(&a.1)));
        scored
            .into_iter()
            .take(limit)
            .map(|(_, _, id)| id)
            .collect()
    }

    /// Maps a free-text club name onto a graph team.
    pub fn resolve_team(&self, query: &str) -> Resolution {
        let key = normalize_query(query);
        if let Some(id) = self.team_by_key.get(&key.id()) {
            return Resolution::Unique(*id);
        }
        if let Some(ids) = self.team_by_base.get(&key.base) {
            let mut ids = ids.clone();
            if ids.len() == 1 {
                return Resolution::Unique(ids[0]);
            }
            if ids.len() > 1 {
                self.sort_by_prominence(&mut ids);
                return Resolution::Ambiguous(ids);
            }
        }
        if let Some(id) = self.team_by_alias.get(&simplify(query)) {
            return Resolution::Unique(*id);
        }
        // Partial match, e.g. "Grêmio Porto Alegre" -> gremio-RS. The names
        // must overlap as whole words and be of comparable length, so
        // "Real Madrid" does not collapse onto a Brazilian club called "Real".
        let needle = key.base;
        if needle.len() >= 4 {
            let mut hits: Vec<TeamId> = self
                .teams
                .iter()
                .filter(|t| {
                    let base = t.key.split('-').next().unwrap_or("").replace('_', " ");
                    let (short, long) = if base.len() <= needle.len() {
                        (base.as_str(), needle.as_str())
                    } else {
                        (needle.as_str(), base.as_str())
                    };
                    if (short.len() as f64) < 0.6 * long.len() as f64 {
                        return false;
                    }
                    contains_words(long, short)
                })
                .map(|t| t.id)
                .collect();
            if !hits.is_empty() {
                self.sort_by_prominence(&mut hits);
                if hits.len() == 1 {
                    return Resolution::Unique(hits[0]);
                }
                // A dominant match wins outright (Flamengo vs Flamengo de Guarulhos).
                if self.team_matches(hits[0]).len() > 5 * self.team_matches(hits[1]).len().max(1) {
                    return Resolution::Unique(hits[0]);
                }
                return Resolution::Ambiguous(hits);
            }
        }
        let mut suggestions: Vec<(usize, TeamId)> = self
            .teams
            .iter()
            .map(|t| (edit_distance(&simplify(&t.name), &needle), t.id))
            .filter(|(distance, _)| *distance <= 2)
            .collect();
        suggestions
            .sort_by_key(|(distance, id)| (*distance, usize::MAX - self.team_matches(*id).len()));
        Resolution::NotFound(suggestions.into_iter().map(|(_, id)| id).take(5).collect())
    }

    fn sort_by_prominence(&self, ids: &mut [TeamId]) {
        ids.sort_by(|a, b| {
            self.team_matches(*b)
                .len()
                .cmp(&self.team_matches(*a).len())
                .then(self.teams[*a].name.cmp(&self.teams[*b].name))
        });
    }

    /// Convenience wrapper returning a single team id or a human-readable error.
    pub fn require_team(&self, query: &str) -> Result<TeamId, String> {
        match self.resolve_team(query) {
            Resolution::Unique(id) => Ok(id),
            Resolution::Ambiguous(ids) => Err(format!(
                "'{query}' is ambiguous. Did you mean: {}?",
                ids.iter()
                    .take(6)
                    .map(|id| self.teams[*id].display())
                    .collect::<Vec<_>>()
                    .join(", ")
            )),
            Resolution::NotFound(suggestions) if !suggestions.is_empty() => Err(format!(
                "No team named '{query}' in the datasets. Closest names: {}.",
                suggestions
                    .iter()
                    .map(|id| self.teams[*id].display())
                    .collect::<Vec<_>>()
                    .join(", ")
            )),
            Resolution::NotFound(_) => Err(format!("No team named '{query}' in the datasets.")),
        }
    }

    // ---- graph traversal --------------------------------------------------------

    /// Human-readable label for any node.
    pub fn node_label(&self, node: NodeRef) -> String {
        match node {
            NodeRef::Team(id) => self.teams[id].display(),
            NodeRef::Player(id) => self.players[id].name.clone(),
            NodeRef::Competition(c) => c.name().to_string(),
            NodeRef::Match(id) => {
                let m = &self.matches[id];
                format!(
                    "{} {} {}-{} {}",
                    m.date.map(|d| d.to_string()).unwrap_or_else(|| "?".into()),
                    self.teams[m.home].name,
                    m.home_goals
                        .map(|g| g.to_string())
                        .unwrap_or_else(|| "?".into()),
                    m.away_goals
                        .map(|g| g.to_string())
                        .unwrap_or_else(|| "?".into()),
                    self.teams[m.away].name
                )
            }
        }
    }

    /// Outgoing edges of a node. `limit` caps the fan-out for hub nodes.
    pub fn neighbors(&self, node: NodeRef, limit: usize) -> Vec<(Relation, NodeRef)> {
        let mut out = Vec::new();
        match node {
            NodeRef::Team(id) => {
                for m in self.team_home_matches(id).iter().take(limit) {
                    out.push((Relation::Hosted, NodeRef::Match(*m)));
                }
                for m in self.team_away_matches(id).iter().take(limit) {
                    out.push((Relation::Visited, NodeRef::Match(*m)));
                }
                for p in self.players_of_team(id).iter().take(limit) {
                    out.push((Relation::HasPlayer, NodeRef::Player(*p)));
                }
            }
            NodeRef::Match(id) => {
                let m = &self.matches[id];
                out.push((Relation::HomeTeam, NodeRef::Team(m.home)));
                out.push((Relation::AwayTeam, NodeRef::Team(m.away)));
                out.push((Relation::PartOf, NodeRef::Competition(m.competition)));
            }
            NodeRef::Player(id) => {
                if let Some(team) = self.players[id].club_team {
                    out.push((Relation::PlaysFor, NodeRef::Team(team)));
                }
            }
            NodeRef::Competition(c) => {
                for m in self.competition_matches(c).iter().take(limit) {
                    out.push((Relation::Includes, NodeRef::Match(*m)));
                }
            }
        }
        out
    }

    pub fn stats(&self) -> GraphStats {
        let canonical_matches = self.matches.iter().filter(|m| m.canonical).count();
        // 2 team edges + 1 competition edge per match, 1 edge per linked player.
        let edges = self.matches.len() * 3
            + self
                .players
                .iter()
                .filter(|p| p.club_team.is_some())
                .count();
        GraphStats {
            teams: self.teams.len(),
            matches: self.matches.len(),
            canonical_matches,
            players: self.players.len(),
            competitions: self.competition_seasons.len(),
            edges,
        }
    }
}
