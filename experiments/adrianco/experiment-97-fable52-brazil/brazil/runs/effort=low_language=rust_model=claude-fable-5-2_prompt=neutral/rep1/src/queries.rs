//! Query layer: filtering, records, standings, head-to-head, players, statistics.
use crate::data::{Competition, Db, Match, Player};
use crate::normalize::{fold, team_key};
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::fmt::Write;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Venue {
    Home,
    Away,
    #[default]
    Either,
}

impl Venue {
    pub fn parse(s: &str) -> Result<Venue, String> {
        match fold(s).as_str() {
            "home" => Ok(Venue::Home),
            "away" => Ok(Venue::Away),
            "either" | "any" | "all" | "overall" | "" => Ok(Venue::Either),
            o => Err(format!("invalid venue '{o}' (use home, away or either)")),
        }
    }
    fn label(self) -> &'static str {
        match self {
            Venue::Home => "home",
            Venue::Away => "away",
            Venue::Either => "overall",
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct Filter {
    pub team: Option<HashSet<String>>,
    pub opponent: Option<HashSet<String>>,
    pub venue: Venue,
    pub competition: Option<Competition>,
    pub season: Option<i32>,
    pub date_from: Option<String>,
    pub date_to: Option<String>,
    pub stage: Option<String>,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Record {
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
}

impl Record {
    fn add(&mut self, gf: u32, ga: u32) {
        self.played += 1;
        self.goals_for += gf;
        self.goals_against += ga;
        match gf.cmp(&ga) {
            std::cmp::Ordering::Greater => self.wins += 1,
            std::cmp::Ordering::Equal => self.draws += 1,
            std::cmp::Ordering::Less => self.losses += 1,
        }
    }
    pub fn points(&self) -> u32 {
        self.wins * 3 + self.draws
    }
    pub fn goal_diff(&self) -> i64 {
        self.goals_for as i64 - self.goals_against as i64
    }
    pub fn win_rate(&self) -> f64 {
        pct(self.wins, self.played)
    }
    fn block(&self) -> String {
        format!(
            "- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {} (diff {:+})\n- Win rate: {:.1}%\n",
            self.played, self.wins, self.draws, self.losses, self.goals_for, self.goals_against,
            self.goal_diff(), self.win_rate()
        )
    }
    fn line(&self) -> String {
        format!(
            "{} played, {}W {}D {}L, goals {}:{}, win rate {:.1}%",
            self.played, self.wins, self.draws, self.losses, self.goals_for, self.goals_against,
            self.win_rate()
        )
    }
}

fn pct(a: u32, b: u32) -> f64 {
    if b == 0 { 0.0 } else { a as f64 * 100.0 / b as f64 }
}

fn norm_stage(s: &str) -> String {
    fold(s).trim_end_matches('s').to_string()
}

/// Aggregate league-level numbers for a set of matches.
#[derive(Debug, Clone, Copy, Default)]
pub struct LeagueStats {
    pub matches: u32,
    pub goals: u32,
    pub home_wins: u32,
    pub draws: u32,
    pub away_wins: u32,
}

impl LeagueStats {
    pub fn avg_goals(&self) -> f64 {
        if self.matches == 0 { 0.0 } else { self.goals as f64 / self.matches as f64 }
    }
}

/// Traditional rivalries (canonical keys) and their nicknames.
pub const DERBIES: &[(&str, &str, &str)] = &[
    ("flamengo", "fluminense", "Fla-Flu"),
    ("flamengo", "vasco", "Clássico dos Milhões"),
    ("flamengo", "botafogo", "Clássico da Rivalidade"),
    ("fluminense", "vasco", "Clássico dos Gigantes"),
    ("fluminense", "botafogo", "Clássico Vovô"),
    ("botafogo", "vasco", "Clássico da Amizade"),
    ("corinthians", "palmeiras", "Derby Paulista"),
    ("corinthians", "sao paulo", "Majestoso"),
    ("palmeiras", "sao paulo", "Choque-Rei"),
    ("corinthians", "santos", "Clássico Alvinegro"),
    ("palmeiras", "santos", "Clássico da Saudade"),
    ("santos", "sao paulo", "San-São"),
    ("gremio", "internacional", "Gre-Nal"),
    ("atletico-mg", "cruzeiro", "Clássico Mineiro"),
    ("bahia", "vitoria", "Ba-Vi"),
    ("atletico-pr", "coritiba", "Atletiba"),
    ("sport", "nautico", "Clássico dos Clássicos"),
    ("sport", "santa cruz", "Clássico das Multidões"),
    ("nautico", "santa cruz", "Clássico das Emoções"),
    ("ceara", "fortaleza", "Clássico-Rei"),
    ("goias", "vila nova", "Derby do Cerrado"),
    ("avai", "figueirense", "Clássico de Florianópolis"),
    ("remo", "paysandu", "Re-Pa"),
];

pub fn derby_name(a: &str, b: &str) -> Option<&'static str> {
    DERBIES
        .iter()
        .find(|(x, y, _)| (*x == a && *y == b) || (*x == b && *y == a))
        .map(|d| d.2)
}

impl Db {
    /// Resolve a user-supplied team name to canonical keys. Exact key match wins;
    /// otherwise any team whose key contains the query (e.g. "Atletico").
    pub fn resolve_team(&self, query: &str) -> Result<HashSet<String>, String> {
        let k = team_key(query, None);
        if k.is_empty() {
            return Err("empty team name".into());
        }
        if self.display.contains_key(&k) {
            return Ok(HashSet::from([k]));
        }
        let f = fold(query);
        let found: HashSet<String> = self
            .display
            .keys()
            .filter(|key| key.contains(&k) || key.contains(&f))
            .cloned()
            .collect();
        if found.is_empty() {
            Err(format!("no team matching '{query}' found in the match data"))
        } else {
            Ok(found)
        }
    }

    pub fn team_label(&self, keys: &HashSet<String>) -> String {
        let mut v: Vec<&str> = keys.iter().map(|k| self.name(k)).collect();
        v.sort();
        v.join(" / ")
    }

    /// De-duplicated matches satisfying the filter, newest first.
    pub fn find_matches(&self, f: &Filter) -> Vec<&Match> {
        let stage = f.stage.as_deref().map(norm_stage);
        let mut out: Vec<&Match> = self
            .matches
            .iter()
            .filter(|m| !m.duplicate)
            .filter(|m| f.competition.map_or(true, |c| m.competition == c))
            .filter(|m| f.season.map_or(true, |s| m.season == s))
            .filter(|m| f.date_from.as_ref().map_or(true, |d| &m.date >= d))
            .filter(|m| f.date_to.as_ref().map_or(true, |d| &m.date <= d))
            .filter(|m| {
                stage.as_ref().map_or(true, |q| {
                    let l = norm_stage(&m.stage);
                    l == *q || l == format!("round {q}") || (q != "final" && q.len() > 3 && l.contains(q.as_str()))
                })
            })
            .filter(|m| {
                let (team, opp) = match (&f.team, &f.opponent) {
                    (None, Some(o)) => (Some(o), None),
                    (t, o) => (t.as_ref(), o.as_ref()),
                };
                let Some(t) = team else { return true };
                let as_home = t.contains(&m.home_key) && opp.map_or(true, |o| o.contains(&m.away_key));
                let as_away = t.contains(&m.away_key) && opp.map_or(true, |o| o.contains(&m.home_key));
                match f.venue {
                    Venue::Home => as_home,
                    Venue::Away => as_away,
                    Venue::Either => as_home || as_away,
                }
            })
            .collect();
        out.sort_by(|a, b| b.date.cmp(&a.date));
        out
    }

    pub fn format_match(&self, m: &Match) -> String {
        let mut ctx = m.competition.name().to_string();
        if !m.stage.is_empty() {
            write!(ctx, ", {}", m.stage).unwrap();
        }
        format!(
            "{}: {} {}-{} {} ({})",
            m.date,
            self.name(&m.home_key),
            m.home_goals,
            m.away_goals,
            self.name(&m.away_key),
            ctx
        )
    }

    /// Record of `team` over `matches` (matches where the team is on both sides are ignored).
    pub fn record(&self, matches: &[&Match], team: &HashSet<String>, venue: Venue) -> Record {
        let mut r = Record::default();
        for m in matches {
            let (h, a) = (team.contains(&m.home_key), team.contains(&m.away_key));
            if h && !a && venue != Venue::Away {
                r.add(m.home_goals, m.away_goals);
            } else if a && !h && venue != Venue::Home {
                r.add(m.away_goals, m.home_goals);
            }
        }
        r
    }

    /// Per-team records over a set of matches.
    pub fn tally(&self, matches: &[&Match], venue: Venue) -> HashMap<String, Record> {
        let mut t: HashMap<String, Record> = HashMap::new();
        for m in matches {
            if venue != Venue::Away {
                t.entry(m.home_key.clone()).or_default().add(m.home_goals, m.away_goals);
            }
            if venue != Venue::Home {
                t.entry(m.away_key.clone()).or_default().add(m.away_goals, m.home_goals);
            }
        }
        t
    }

    /// All de-duplicated matches of one competition season, across source files.
    pub fn season_matches(&self, comp: Competition, season: i32) -> Vec<&Match> {
        self.matches
            .iter()
            .filter(|m| !m.duplicate && m.competition == comp && m.season == season)
            .collect()
    }

    /// League table computed from results: points, then wins, goal difference, goals for.
    pub fn standings(&self, comp: Competition, season: i32) -> Vec<(String, Record)> {
        let ms = self.season_matches(comp, season);
        let mut rows: Vec<(String, Record)> = self.tally(&ms, Venue::Either).into_iter().collect();
        // The source data has a few mislabelled rows (e.g. a one-off friendly tagged as
        // Série A); a team with only one or two matches in a full season is not a participant.
        let max_played = rows.iter().map(|(_, r)| r.played).max().unwrap_or(0);
        if max_played >= 20 {
            let stray: HashSet<String> = rows.iter().filter(|(_, r)| r.played < 3).map(|(k, _)| k.clone()).collect();
            if !stray.is_empty() {
                let kept: Vec<&Match> = ms.iter().copied().filter(|m| !stray.contains(&m.home_key) && !stray.contains(&m.away_key)).collect();
                rows = self.tally(&kept, Venue::Either).into_iter().collect();
            }
        }
        rows.sort_by(|a, b| {
            (b.1.points(), b.1.wins, b.1.goal_diff(), b.1.goals_for)
                .cmp(&(a.1.points(), a.1.wins, a.1.goal_diff(), a.1.goals_for))
                .then_with(|| a.0.cmp(&b.0))
        });
        rows
    }

    pub fn league_stats(&self, matches: &[&Match]) -> LeagueStats {
        let mut s = LeagueStats::default();
        for m in matches {
            s.matches += 1;
            s.goals += m.home_goals + m.away_goals;
            match m.home_goals.cmp(&m.away_goals) {
                std::cmp::Ordering::Greater => s.home_wins += 1,
                std::cmp::Ordering::Equal => s.draws += 1,
                std::cmp::Ordering::Less => s.away_wins += 1,
            }
        }
        s
    }

    // ---------- text answers ----------

    fn scope(&self, f: &Filter) -> String {
        let mut parts = Vec::new();
        if let Some(s) = f.season {
            parts.push(s.to_string());
        }
        parts.push(f.competition.map_or("all competitions", |c| c.name()).to_string());
        if let Some(s) = &f.stage {
            parts.push(format!("stage '{s}'"));
        }
        match (&f.date_from, &f.date_to) {
            (Some(a), Some(b)) => parts.push(format!("{a} to {b}")),
            (Some(a), None) => parts.push(format!("from {a}")),
            (None, Some(b)) => parts.push(format!("until {b}")),
            _ => {}
        }
        parts.join(", ")
    }

    fn list(&self, out: &mut String, ms: &[&Match], limit: usize) {
        for m in ms.iter().take(limit) {
            writeln!(out, "- {}", self.format_match(m)).unwrap();
        }
        if ms.len() > limit {
            writeln!(out, "- ... ({} more matches in dataset)", ms.len() - limit).unwrap();
        }
    }

    pub fn search_matches_text(&self, f: &Filter, limit: usize) -> String {
        let ms = self.find_matches(f);
        let mut out = String::new();
        let who = match (&f.team, &f.opponent) {
            (Some(t), Some(o)) => format!("{} vs {}", self.team_label(t), self.team_label(o)),
            (Some(t), None) | (None, Some(t)) => {
                format!("{} ({} matches)", self.team_label(t), f.venue.label())
            }
            _ => "Matches".to_string(),
        };
        if ms.is_empty() {
            return format!("No matches found for {who} [{}].", self.scope(f));
        }
        writeln!(out, "{who} [{}] - {} matches found:", self.scope(f), ms.len()).unwrap();
        self.list(&mut out, &ms, limit);
        if let (Some(t), Some(o)) = (&f.team, &f.opponent) {
            let r = self.record(&ms, t, Venue::Either);
            writeln!(
                out,
                "\nHead-to-head in dataset: {} {} wins, {} {} wins, {} draws",
                self.team_label(t), r.wins, self.team_label(o), r.losses, r.draws
            )
            .unwrap();
        }
        out
    }

    pub fn head_to_head_text(&self, f: &Filter, limit: usize) -> Result<String, String> {
        let (Some(a), Some(b)) = (&f.team, &f.opponent) else {
            return Err("both team_a and team_b are required".into());
        };
        let ms = self.find_matches(f);
        let (la, lb) = (self.team_label(a), self.team_label(b));
        if ms.is_empty() {
            return Ok(format!("No matches between {la} and {lb} [{}].", self.scope(f)));
        }
        let r = self.record(&ms, a, Venue::Either);
        let mut out = String::new();
        let derby = match (a.iter().next(), b.iter().next()) {
            (Some(x), Some(y)) if a.len() == 1 && b.len() == 1 => {
                derby_name(x, y).map(|n| format!(" ({n} derby)")).unwrap_or_default()
            }
            _ => String::new(),
        };
        writeln!(out, "{la} vs {lb}{derby} [{}]:", self.scope(f)).unwrap();
        writeln!(out, "- Matches: {}", r.played).unwrap();
        writeln!(out, "- {la} wins: {}, {lb} wins: {}, Draws: {}", r.wins, r.losses, r.draws).unwrap();
        writeln!(out, "- Goals: {la} {}, {lb} {}", r.goals_for, r.goals_against).unwrap();
        let home = self.record(&ms, a, Venue::Home);
        let away = self.record(&ms, a, Venue::Away);
        writeln!(out, "- {la} at home: {}W {}D {}L; away: {}W {}D {}L", home.wins, home.draws, home.losses, away.wins, away.draws, away.losses).unwrap();
        let mut by_comp: BTreeMap<Competition, Vec<&Match>> = BTreeMap::new();
        for m in &ms {
            by_comp.entry(m.competition).or_default().push(m);
        }
        if by_comp.len() > 1 {
            for (c, v) in &by_comp {
                let r = self.record(v, a, Venue::Either);
                writeln!(out, "- {}: {la} {}W, {lb} {}W, {} draws", c.name(), r.wins, r.losses, r.draws).unwrap();
            }
        }
        writeln!(out, "\nMost recent meetings:").unwrap();
        self.list(&mut out, &ms, limit);
        Ok(out)
    }

    pub fn team_stats_text(&self, f: &Filter) -> Result<String, String> {
        let Some(t) = &f.team else { return Err("team is required".into()) };
        let ms = self.find_matches(f);
        let label = self.team_label(t);
        if ms.is_empty() {
            return Ok(format!("No matches found for {label} [{}].", self.scope(f)));
        }
        let mut out = String::new();
        writeln!(out, "{label} {} record ({}):", f.venue.label(), self.scope(f)).unwrap();
        out.push_str(&self.record(&ms, t, Venue::Either).block());
        if f.venue == Venue::Either {
            writeln!(out, "\nHome: {}", self.record(&ms, t, Venue::Home).line()).unwrap();
            writeln!(out, "Away: {}", self.record(&ms, t, Venue::Away).line()).unwrap();
        }
        if f.competition.is_none() {
            writeln!(out, "\nBy competition:").unwrap();
            for c in Competition::ALL {
                let v: Vec<&Match> = ms.iter().copied().filter(|m| m.competition == c).collect();
                if !v.is_empty() {
                    writeln!(out, "- {}: {}", c.name(), self.record(&v, t, Venue::Either).line()).unwrap();
                }
            }
        }
        if f.season.is_none() {
            let seasons: BTreeSet<i32> = ms.iter().map(|m| m.season).collect();
            writeln!(out, "\nSeasons covered: {}-{}", seasons.first().unwrap(), seasons.last().unwrap()).unwrap();
        }
        Ok(out)
    }

    pub fn standings_text(&self, comp: Competition, season: i32) -> String {
        let rows = self.standings(comp, season);
        if rows.is_empty() {
            return format!("No {} matches found for season {season}.", comp.name());
        }
        let league = matches!(comp, Competition::SerieA | Competition::SerieB | Competition::SerieC);
        let mut out = String::new();
        let srcs: BTreeSet<&str> = self.season_matches(comp, season).iter().map(|m| m.source.file()).collect();
        let src = srcs.into_iter().collect::<Vec<_>>().join(" + ");
        writeln!(out, "{season} {} {} (calculated from matches in {src}):", comp.name(), if league { "Final Standings" } else { "aggregate table" }).unwrap();
        let n = rows.len();
        let (min_p, max_p) = rows.iter().fold((u32::MAX, 0), |(lo, hi), (_, r)| (lo.min(r.played), hi.max(r.played)));
        let complete = min_p == max_p;
        for (i, (k, r)) in rows.iter().enumerate() {
            let note = if !league {
                ""
            } else if i == 0 {
                if complete { " - Champion" } else { " - Leader (incomplete data)" }
            } else if comp == Competition::SerieA && n >= 20 && i >= n - 4 {
                " - Relegation zone"
            } else {
                ""
            };
            writeln!(
                out,
                "{}. {} - {} pts ({}W, {}D, {}L), GF {} GA {} GD {:+}{}",
                i + 1, self.name(k), r.points(), r.wins, r.draws, r.losses, r.goals_for, r.goals_against, r.goal_diff(), note
            )
            .unwrap();
        }
        if league && !complete {
            writeln!(out, "\nWarning: the dataset is incomplete for this season (teams have between {min_p} and {max_p} matches), so positions may differ from the official final table.").unwrap();
        }
        if league {
            out.push_str("\nNote: computed purely from results (3 pts per win); off-field point deductions are not in the data. Since 2006 the bottom four of Série A are relegated.\n");
        } else {
            out.push_str("\nNote: this is a knockout competition; use competition_bracket for the round-by-round results.\n");
        }
        out
    }

    pub fn bracket_text(&self, comp: Competition, season: i32) -> String {
        let ms = self.season_matches(comp, season);
        if ms.is_empty() {
            return format!("No {} matches found for season {season}.", comp.name());
        }
        let mut stages: Vec<(String, Vec<&Match>)> = Vec::new();
        let mut sorted = ms.clone();
        sorted.sort_by(|a, b| a.date.cmp(&b.date));
        for m in sorted {
            match stages.iter_mut().find(|(s, _)| *s == m.stage) {
                Some((_, v)) => v.push(m),
                None => stages.push((m.stage.clone(), vec![m])),
            }
        }
        let mut out = format!("{season} {} - results by stage ({} matches):\n", comp.name(), ms.len());
        for (stage, v) in &stages {
            writeln!(out, "\n{} ({} matches):", if stage.is_empty() { "Matches" } else { stage }, v.len()).unwrap();
            let big = v.len() > 40;
            for m in v.iter().take(if big { 10 } else { v.len() }) {
                writeln!(out, "- {}: {} {}-{} {}", m.date, self.name(&m.home_key), m.home_goals, m.away_goals, self.name(&m.away_key)).unwrap();
            }
            if big {
                writeln!(out, "- ... ({} more; use search_matches with stage filter)", v.len() - 10).unwrap();
            }
        }
        if let Some((stage, v)) = stages.last() {
            if norm_stage(stage) == "final" {
                let (a, b) = (&v[0].home_key, &v[0].away_key);
                let (mut ga, mut gb) = (0, 0);
                for m in v {
                    if &m.home_key == a { ga += m.home_goals; gb += m.away_goals } else { ga += m.away_goals; gb += m.home_goals }
                }
                let verdict = match ga.cmp(&gb) {
                    std::cmp::Ordering::Greater => format!("winner on aggregate: {}", self.name(a)),
                    std::cmp::Ordering::Less => format!("winner on aggregate: {}", self.name(b)),
                    _ => "level on aggregate (decided by away goals/penalties, not in data)".to_string(),
                };
                writeln!(out, "\nFinal aggregate: {} {}-{} {} - {}", self.name(a), ga, gb, self.name(b), verdict).unwrap();
            }
        }
        out
    }

    pub fn league_stats_text(&self, f: &Filter) -> String {
        let ms = self.find_matches(f);
        if ms.is_empty() {
            return format!("No matches found [{}].", self.scope(f));
        }
        let s = self.league_stats(&ms);
        let mut out = format!("Statistics [{}]:\n", self.scope(f));
        writeln!(out, "- Matches: {}", s.matches).unwrap();
        writeln!(out, "- Total goals: {}", s.goals).unwrap();
        writeln!(out, "- Average goals per match: {:.2}", s.avg_goals()).unwrap();
        writeln!(out, "- Home win rate: {:.1}%", pct(s.home_wins, s.matches)).unwrap();
        writeln!(out, "- Draw rate: {:.1}%", pct(s.draws, s.matches)).unwrap();
        writeln!(out, "- Away win rate: {:.1}%", pct(s.away_wins, s.matches)).unwrap();
        let top = ms.iter().max_by_key(|m| (m.home_goals + m.away_goals, &m.date)).unwrap();
        writeln!(out, "- Highest-scoring match: {}", self.format_match(top)).unwrap();
        let avg = |get: fn(&crate::data::Extended) -> Option<(u32, u32)>| -> Option<(f64, usize)> {
            let v: Vec<u32> = ms.iter().filter_map(|m| m.extended.as_ref().and_then(get)).map(|(a, b)| a + b).collect();
            (!v.is_empty()).then(|| (v.iter().sum::<u32>() as f64 / v.len() as f64, v.len()))
        };
        if let Some((a, n)) = avg(|e| e.corners) {
            writeln!(out, "- Average corners per match: {a:.2} (from {n} matches with extended stats)").unwrap();
        }
        if let Some((a, n)) = avg(|e| e.shots) {
            writeln!(out, "- Average shots per match: {a:.2} (from {n} matches with extended stats)").unwrap();
        }
        out
    }

    pub fn biggest_wins_text(&self, f: &Filter, limit: usize) -> String {
        let mut ms = self.find_matches(f);
        if ms.is_empty() {
            return format!("No matches found [{}].", self.scope(f));
        }
        ms.sort_by(|a, b| {
            let k = |m: &Match| (m.home_goals.abs_diff(m.away_goals), m.home_goals + m.away_goals);
            k(b).cmp(&k(a)).then_with(|| b.date.cmp(&a.date))
        });
        let mut out = format!("Biggest victories [{}]:\n", self.scope(f));
        for (i, m) in ms.iter().take(limit).enumerate() {
            writeln!(out, "{}. {}", i + 1, self.format_match(m)).unwrap();
        }
        let s = self.league_stats(&ms);
        writeln!(out, "\nAverage goals per match: {:.2}", s.avg_goals()).unwrap();
        writeln!(out, "Home win rate: {:.1}%", pct(s.home_wins, s.matches)).unwrap();
        out
    }

    /// Rank teams by a metric: win_rate, points, goals_for, goals_against, goal_diff, wins.
    pub fn rank_teams(&self, f: &Filter, metric: &str, min_matches: u32) -> Result<Vec<(String, Record)>, String> {
        let ms = self.find_matches(f);
        let score: fn(&Record) -> f64 = match metric {
            "win_rate" => |r| r.win_rate(),
            "points" => |r| r.points() as f64,
            "points_per_match" => |r| if r.played == 0 { 0.0 } else { r.points() as f64 / r.played as f64 },
            "goals_for" => |r| r.goals_for as f64,
            "goals_against" => |r| -(r.goals_against as f64),
            "goal_diff" => |r| r.goal_diff() as f64,
            "wins" => |r| r.wins as f64,
            o => return Err(format!("unknown metric '{o}' (use win_rate, points, points_per_match, goals_for, goals_against, goal_diff or wins)")),
        };
        let mut rows: Vec<(String, Record)> = self
            .tally(&ms, f.venue)
            .into_iter()
            .filter(|(_, r)| r.played >= min_matches)
            .collect();
        rows.sort_by(|a, b| {
            score(&b.1)
                .partial_cmp(&score(&a.1))
                .unwrap()
                .then_with(|| b.1.played.cmp(&a.1.played))
                .then_with(|| a.0.cmp(&b.0))
        });
        Ok(rows)
    }

    pub fn rank_teams_text(&self, f: &Filter, metric: &str, min_matches: u32, limit: usize) -> Result<String, String> {
        let rows = self.rank_teams(f, metric, min_matches)?;
        if rows.is_empty() {
            return Ok(format!("No teams with at least {min_matches} matches [{}].", self.scope(f)));
        }
        let mut out = format!(
            "Team ranking by {metric}, {} matches [{}], minimum {min_matches} matches:\n",
            f.venue.label(), self.scope(f)
        );
        for (i, (k, r)) in rows.iter().take(limit).enumerate() {
            writeln!(out, "{}. {} - {} ({} pts, GD {:+})", i + 1, self.name(k), r.line(), r.points(), r.goal_diff()).unwrap();
        }
        Ok(out)
    }

    pub fn compare_seasons_text(&self, comp: Competition, a: i32, b: i32) -> String {
        let mut out = format!("{} season comparison:\n", comp.name());
        for s in [a, b] {
            let ms = self.season_matches(comp, s);
            if ms.is_empty() {
                writeln!(out, "\n{s}: no matches in dataset").unwrap();
                continue;
            }
            let st = self.league_stats(&ms);
            let table = self.standings(comp, s);
            writeln!(out, "\n{s}:").unwrap();
            writeln!(out, "- Matches: {}, Teams: {}", st.matches, table.len()).unwrap();
            writeln!(out, "- Goals: {} ({:.2} per match)", st.goals, st.avg_goals()).unwrap();
            writeln!(out, "- Home wins: {:.1}%, Draws: {:.1}%, Away wins: {:.1}%", pct(st.home_wins, st.matches), pct(st.draws, st.matches), pct(st.away_wins, st.matches)).unwrap();
            if matches!(comp, Competition::SerieA | Competition::SerieB | Competition::SerieC) {
                let (k, r) = &table[0];
                writeln!(out, "- Top of table: {} ({} pts, {}W {}D {}L)", self.name(k), r.points(), r.wins, r.draws, r.losses).unwrap();
            }
            let best = table.iter().max_by_key(|(_, r)| r.goals_for).unwrap();
            writeln!(out, "- Most goals scored: {} ({})", self.name(&best.0), best.1.goals_for).unwrap();
        }
        out
    }

    pub fn team_competitions_text(&self, team: &HashSet<String>) -> String {
        let f = Filter { team: Some(team.clone()), ..Default::default() };
        let ms = self.find_matches(&f);
        let mut out = format!("Competitions played by {} (in dataset):\n", self.team_label(team));
        for c in Competition::ALL {
            let v: Vec<&Match> = ms.iter().copied().filter(|m| m.competition == c).collect();
            if v.is_empty() {
                continue;
            }
            let seasons: BTreeSet<i32> = v.iter().map(|m| m.season).collect();
            writeln!(
                out,
                "- {}: {} matches, {} seasons ({}-{}); {}",
                c.name(), v.len(), seasons.len(), seasons.first().unwrap(), seasons.last().unwrap(),
                self.record(&v, team, Venue::Either).line()
            )
            .unwrap();
        }
        out
    }

    pub fn derbies_text(&self, f: &Filter, limit: usize) -> String {
        let ms: Vec<&Match> = self
            .find_matches(f)
            .into_iter()
            .filter(|m| derby_name(&m.home_key, &m.away_key).is_some())
            .collect();
        if ms.is_empty() {
            return format!("No derby matches found [{}].", self.scope(f));
        }
        let mut out = format!("Derby matches between traditional rivals [{}] - {} found:\n", self.scope(f), ms.len());
        for m in ms.iter().take(limit) {
            writeln!(out, "- {} - {}", self.format_match(m), derby_name(&m.home_key, &m.away_key).unwrap()).unwrap();
        }
        if ms.len() > limit {
            writeln!(out, "- ... ({} more)", ms.len() - limit).unwrap();
        }
        out
    }

    // ---------- players ----------

    pub fn find_players(&self, q: &PlayerQuery) -> Vec<&Player> {
        let name_toks: Vec<String> = q.name.as_deref().map(fold).unwrap_or_default().split(' ').filter(|t| !t.is_empty()).map(String::from).collect();
        let nat = q.nationality.as_deref().map(|n| match fold(n).as_str() {
            "brazilian" | "brasil" | "brasileiro" => "brazil".to_string(),
            o => o.to_string(),
        });
        let club = q.club.as_deref().map(|c| (team_key(c, None), fold(c)));
        let club_exact = club.as_ref().map_or(false, |(k, f)| {
            self.players.iter().any(|p| p.club_key == *k || fold(&p.club) == *f)
        });
        let mut v: Vec<&Player> = self
            .players
            .iter()
            .filter(|p| {
                let n = fold(&p.name);
                name_toks.iter().all(|t| n.contains(t.as_str()))
            })
            .filter(|p| nat.as_ref().map_or(true, |n| fold(&p.nationality) == *n))
            .filter(|p| {
                club.as_ref().map_or(true, |(k, f)| {
                    if club_exact {
                        p.club_key == *k || fold(&p.club) == *f
                    } else {
                        fold(&p.club).contains(f.as_str()) || (!k.is_empty() && p.club_key.contains(k.as_str()))
                    }
                })
            })
            .filter(|p| q.position.as_deref().map_or(true, |pos| position_matches(&p.position, pos)))
            .filter(|p| q.min_overall.map_or(true, |m| p.overall >= m))
            .filter(|p| q.max_age.map_or(true, |m| p.age <= m))
            .collect();
        v.sort_by(|a, b| b.overall.cmp(&a.overall).then(b.potential.cmp(&a.potential)).then(a.name.cmp(&b.name)));
        v
    }

    pub fn search_players_text(&self, q: &PlayerQuery, limit: usize) -> String {
        let v = self.find_players(q);
        if v.is_empty() {
            return format!("No players found matching {}.", q.describe());
        }
        let mut out = format!("Players matching {} - {} found (sorted by overall rating):\n", q.describe(), v.len());
        for (i, p) in v.iter().take(limit).enumerate() {
            writeln!(out, "{}. {}", i + 1, player_line(p)).unwrap();
        }
        if v.len() > limit {
            writeln!(out, "... ({} more players)", v.len() - limit).unwrap();
        }
        let avg = v.iter().map(|p| p.overall as f64).sum::<f64>() / v.len() as f64;
        writeln!(out, "\nAverage overall rating: {avg:.1}").unwrap();
        out
    }

    pub fn player_details_text(&self, q: &str) -> String {
        let v: Vec<&Player> = match q.trim().parse::<u64>() {
            Ok(id) => self.players.iter().filter(|p| p.id == id).collect(),
            Err(_) => self.find_players(&PlayerQuery { name: Some(q.to_string()), ..Default::default() }),
        };
        let Some(p) = v.first() else {
            return format!("No player matching '{q}' found in the FIFA dataset.");
        };
        let or = |s: &str| if s.is_empty() { "n/a".to_string() } else { s.to_string() };
        let mut out = format!("{} (FIFA ID {}):\n", p.name, p.id);
        writeln!(out, "- Age: {}, Nationality: {}", p.age, p.nationality).unwrap();
        writeln!(out, "- Club: {}, Position: {}, Jersey: {}", or(&p.club), or(&p.position), or(&p.jersey)).unwrap();
        writeln!(out, "- Overall: {}, Potential: {}", p.overall, p.potential).unwrap();
        writeln!(out, "- Height: {}, Weight: {}, Preferred foot: {}", or(&p.height), or(&p.weight), or(&p.foot)).unwrap();
        writeln!(out, "- Value: {}, Wage: {}", or(&p.value), or(&p.wage)).unwrap();
        if !p.skills.is_empty() {
            let s: Vec<String> = p.skills.iter().map(|(n, v)| format!("{n} {v}")).collect();
            writeln!(out, "- Attributes: {}", s.join(", ")).unwrap();
        }
        if self.display.contains_key(&p.club_key) {
            let t = HashSet::from([p.club_key.clone()]);
            let ms = self.find_matches(&Filter { team: Some(t.clone()), ..Default::default() });
            writeln!(out, "- Club in match data: {} - {}", self.name(&p.club_key), self.record(&ms, &t, Venue::Either).line()).unwrap();
        }
        if v.len() > 1 {
            let others: Vec<String> = v.iter().skip(1).take(8).map(|p| format!("{} ({}, {})", p.name, p.club, p.overall)).collect();
            writeln!(out, "\nOther matches ({}): {}", v.len() - 1, others.join("; ")).unwrap();
        }
        out
    }

    /// Clubs that appear in the Brazilian league match data.
    fn is_brazilian_club(&self, club_key: &str) -> bool {
        !club_key.is_empty()
            && self.matches.iter().any(|m| {
                matches!(m.competition, Competition::SerieA | Competition::SerieB | Competition::SerieC)
                    && (m.home_key == club_key || m.away_key == club_key)
            })
    }

    pub fn players_by_club_text(&self, nationality: Option<&str>, brazilian_clubs_only: bool, limit: usize) -> String {
        let q = PlayerQuery { nationality: nationality.map(String::from), ..Default::default() };
        let mut groups: HashMap<&str, Vec<&Player>> = HashMap::new();
        let mut cache: HashMap<&str, bool> = HashMap::new();
        for p in self.find_players(&q) {
            if p.club.is_empty() {
                continue;
            }
            if brazilian_clubs_only && !*cache.entry(&p.club_key).or_insert_with(|| self.is_brazilian_club(&p.club_key)) {
                continue;
            }
            groups.entry(&p.club).or_default().push(p);
        }
        let mut rows: Vec<(&str, Vec<&Player>)> = groups.into_iter().collect();
        rows.sort_by(|a, b| b.1.len().cmp(&a.1.len()).then(a.0.cmp(b.0)));
        let who = nationality.map_or("All players".to_string(), |n| format!("Players with nationality '{n}'"));
        let mut out = format!("{who} by club{} - {} clubs:\n", if brazilian_clubs_only { " (Brazilian clubs only)" } else { "" }, rows.len());
        for (club, ps) in rows.iter().take(limit) {
            let avg = ps.iter().map(|p| p.overall as f64).sum::<f64>() / ps.len() as f64;
            writeln!(out, "- {}: {} players (avg rating: {:.0}, best: {} {})", club, ps.len(), avg, ps[0].name, ps[0].overall).unwrap();
        }
        if rows.len() > limit {
            writeln!(out, "- ... ({} more clubs)", rows.len() - limit).unwrap();
        }
        out
    }

    /// Cross-file view: match record plus FIFA squad for a club.
    pub fn team_profile_text(&self, query: &str) -> Result<String, String> {
        let team = self.resolve_team(query)?;
        let ms = self.find_matches(&Filter { team: Some(team.clone()), ..Default::default() });
        let mut out = format!("{} - team profile\n\nMatch data:\n", self.team_label(&team));
        out.push_str(&self.record(&ms, &team, Venue::Either).block());
        out.push('\n');
        out.push_str(&self.team_competitions_text(&team));
        let mut rivals: Vec<&str> = Vec::new();
        for (a, b, n) in DERBIES {
            if team.contains(*a) || team.contains(*b) {
                rivals.push(n);
            }
        }
        if !rivals.is_empty() {
            writeln!(out, "\nTraditional derbies: {}", rivals.join(", ")).unwrap();
        }
        if let Some(m) = ms.first() {
            writeln!(out, "Most recent match: {}", self.format_match(m)).unwrap();
        }
        let squad: Vec<&Player> = {
            let mut v: Vec<&Player> = self.players.iter().filter(|p| team.contains(&p.club_key)).collect();
            v.sort_by(|a, b| b.overall.cmp(&a.overall));
            v
        };
        if squad.is_empty() {
            out.push_str("\nFIFA player data: no players listed for this club.\n");
        } else {
            let avg = squad.iter().map(|p| p.overall as f64).sum::<f64>() / squad.len() as f64;
            writeln!(out, "\nFIFA player data: {} players (avg rating {avg:.1}). Top rated:", squad.len()).unwrap();
            for (i, p) in squad.iter().take(10).enumerate() {
                writeln!(out, "{}. {}", i + 1, player_line(p)).unwrap();
            }
        }
        Ok(out)
    }

    pub fn summary_text(&self) -> String {
        let mut out = String::from("Brazilian soccer knowledge base - loaded data:\n");
        for (f, n) in &self.loaded {
            writeln!(out, "- {f}: {n} rows").unwrap();
        }
        let unique: Vec<&Match> = self.matches.iter().filter(|m| !m.duplicate).collect();
        writeln!(out, "\nUnique matches after cross-file de-duplication: {} (of {})", unique.len(), self.matches.len()).unwrap();
        for c in Competition::ALL {
            let v: Vec<&&Match> = unique.iter().filter(|m| m.competition == c).collect();
            if let (Some(a), Some(b)) = (v.iter().map(|m| m.season).min(), v.iter().map(|m| m.season).max()) {
                writeln!(out, "- {}: {} matches, seasons {a}-{b}", c.name(), v.len()).unwrap();
            }
        }
        writeln!(out, "\nTeams: {}", self.display.len()).unwrap();
        let br = self.players.iter().filter(|p| p.nationality == "Brazil").count();
        writeln!(out, "Players: {} ({} Brazilian)", self.players.len(), br).unwrap();
        out
    }
}

#[derive(Debug, Clone, Default)]
pub struct PlayerQuery {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub min_overall: Option<u32>,
    pub max_age: Option<u32>,
}

impl PlayerQuery {
    fn describe(&self) -> String {
        let mut p = Vec::new();
        if let Some(v) = &self.name { p.push(format!("name '{v}'")) }
        if let Some(v) = &self.nationality { p.push(format!("nationality '{v}'")) }
        if let Some(v) = &self.club { p.push(format!("club '{v}'")) }
        if let Some(v) = &self.position { p.push(format!("position '{v}'")) }
        if let Some(v) = self.min_overall { p.push(format!("overall >= {v}")) }
        if let Some(v) = self.max_age { p.push(format!("age <= {v}")) }
        if p.is_empty() { "all players".into() } else { p.join(", ") }
    }
}

fn player_line(p: &Player) -> String {
    format!(
        "{} - Overall: {}, Position: {}, Club: {}, Age: {}, Nationality: {}",
        p.name,
        p.overall,
        if p.position.is_empty() { "n/a" } else { &p.position },
        if p.club.is_empty() { "n/a" } else { &p.club },
        p.age,
        p.nationality
    )
}

/// Match a FIFA position code against a code ("ST") or a group ("forwards").
pub fn position_matches(pos: &str, query: &str) -> bool {
    let q = fold(query);
    let group: &[&str] = match q.trim_end_matches('s') {
        "forward" | "attacker" | "striker" => &["ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"],
        "midfielder" | "midfield" => &["CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"],
        "defender" | "defense" | "defence" | "back" => &["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"],
        "goalkeeper" | "keeper" | "goalie" => &["GK"],
        _ => return pos.eq_ignore_ascii_case(query.trim()),
    };
    group.contains(&pos)
}
