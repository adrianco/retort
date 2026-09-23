//! Query engine: match search, team stats, standings, players and aggregates.

use crate::data::{fold, Competition, Dataset, Match, Player};
use std::collections::{HashMap, HashSet};
use std::fmt::Write;

#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    pub team: Option<String>,
    pub opponent: Option<String>,
    /// "home", "away" or anything else for either
    pub venue: Option<String>,
    pub competition: Option<Competition>,
    pub season: Option<i32>,
    pub date_from: Option<String>,
    pub date_to: Option<String>,
    /// Substring of round/stage, e.g. "final"
    pub round: Option<String>,
}

#[derive(Debug, Default, Clone, PartialEq)]
pub struct Record {
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
}

impl Record {
    pub fn add(&mut self, gf: u32, ga: u32) {
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
        if self.played == 0 { 0.0 } else { 100.0 * self.wins as f64 / self.played as f64 }
    }
}

pub struct Engine {
    pub data: Dataset,
    /// Indices of de-duplicated matches (the datasets overlap).
    unique: Vec<usize>,
}

pub struct StandingRow {
    pub team: String,
    pub record: Record,
}

impl Engine {
    pub fn new(data: Dataset) -> Engine {
        // The files overlap. For each (competition, season) keep only the
        // source with the most matches (earliest-loaded on ties), then drop
        // duplicate fixtures within that source.
        let mut counts: Vec<((&'static str, i32, &'static str), usize)> = Vec::new();
        for m in &data.matches {
            let k = (m.competition.name(), m.season, m.source);
            match counts.iter_mut().find(|(c, _)| *c == k) {
                Some((_, n)) => *n += 1,
                None => counts.push((k, 1)),
            }
        }
        let mut owner: HashMap<(&'static str, i32), (&'static str, usize)> = HashMap::new();
        for ((c, season, src), n) in counts {
            let e = owner.entry((c, season)).or_insert((src, n));
            if n > e.1 {
                *e = (src, n);
            }
        }
        let mut seen = HashSet::new();
        let mut unique = Vec::new();
        for (i, m) in data.matches.iter().enumerate() {
            if owner[&(m.competition.name(), m.season)].0 != m.source {
                continue;
            }
            let league = matches!(m.competition, Competition::Brasileirao | Competition::SerieB | Competition::SerieC);
            let k = if league {
                (m.competition.name(), m.season.to_string(), m.home_key.clone(), m.away_key.clone())
            } else {
                (m.competition.name(), m.date.clone(), m.home_key.clone(), m.away_key.clone())
            };
            if seen.insert(k) {
                unique.push(i);
            }
        }
        Engine { data, unique }
    }

    pub fn load(dir: &str) -> Result<Engine, String> {
        Ok(Engine::new(Dataset::load(dir)?))
    }

    pub fn all_matches(&self) -> impl Iterator<Item = &Match> {
        self.unique.iter().map(|&i| &self.data.matches[i])
    }

    fn team(&self, q: &str) -> Result<String, String> {
        self.data.resolve_team(q).ok_or_else(|| format!("Unknown team: {q}"))
    }

    pub fn find_matches(&self, f: &MatchFilter) -> Result<Vec<&Match>, String> {
        let team = f.team.as_deref().map(|t| self.team(t)).transpose()?;
        let opp = f.opponent.as_deref().map(|t| self.team(t)).transpose()?;
        let venue = f.venue.as_deref().map(fold).unwrap_or_default();
        let round = f.round.as_deref().map(fold);
        let mut out: Vec<&Match> = self
            .all_matches()
            .filter(|m| {
                if let Some(t) = &team {
                    let ok = match venue.as_str() {
                        "home" => &m.home_key == t,
                        "away" => &m.away_key == t,
                        _ => &m.home_key == t || &m.away_key == t,
                    };
                    if !ok {
                        return false;
                    }
                    if let Some(o) = &opp {
                        let other = if &m.home_key == t { &m.away_key } else { &m.home_key };
                        if other != o {
                            return false;
                        }
                    }
                } else if let Some(o) = &opp {
                    if &m.home_key != o && &m.away_key != o {
                        return false;
                    }
                }
                f.competition.map_or(true, |c| m.competition == c)
                    && f.season.map_or(true, |s| m.season == s)
                    && f.date_from.as_deref().map_or(true, |d| m.date.as_str() >= d)
                    && f.date_to.as_deref().map_or(true, |d| m.date.as_str() <= d)
                    && round.as_deref().map_or(true, |r| fold(&m.round).contains(r))
            })
            .collect();
        out.sort_by(|a, b| b.date.cmp(&a.date));
        Ok(out)
    }

    pub fn fmt_match(&self, m: &Match) -> String {
        let mut s = format!(
            "{}: {} {}-{} {} ({}",
            m.date,
            self.data.display_name(&m.home_key),
            m.home_goals,
            m.away_goals,
            self.data.display_name(&m.away_key),
            m.competition.name()
        );
        if !m.round.is_empty() {
            let _ = write!(s, " {}", m.round);
        }
        s.push(')');
        if let Some(a) = &m.arena {
            let _ = write!(s, " @ {a}");
        }
        s
    }

    pub fn search_matches_text(&self, f: &MatchFilter, limit: usize) -> Result<String, String> {
        let ms = self.find_matches(f)?;
        let mut s = format!("Found {} matches", ms.len());
        if let Some(t) = &f.team {
            let _ = write!(s, " for {}", self.data.display_name(&self.team(t)?));
        }
        if let Some(o) = &f.opponent {
            let _ = write!(s, " vs {}", self.data.display_name(&self.team(o)?));
        }
        s.push_str(":\n");
        for m in ms.iter().take(limit) {
            let _ = writeln!(s, "- {}", self.fmt_match(m));
        }
        if ms.len() > limit {
            let _ = writeln!(s, "- ... ({} more matches in dataset)", ms.len() - limit);
        }
        Ok(s)
    }

    /// Head-to-head: (a wins, b wins, draws, a goals, b goals, matches).
    pub fn head_to_head(&self, a: &str, b: &str, comp: Option<Competition>) -> Result<(Record, Vec<&Match>), String> {
        let ka = self.team(a)?;
        let f = MatchFilter { team: Some(a.into()), opponent: Some(b.into()), competition: comp, ..Default::default() };
        let ms = self.find_matches(&f)?;
        let mut r = Record::default();
        for m in &ms {
            if m.home_key == ka { r.add(m.home_goals, m.away_goals) } else { r.add(m.away_goals, m.home_goals) }
        }
        Ok((r, ms))
    }

    pub fn head_to_head_text(&self, a: &str, b: &str, comp: Option<Competition>, limit: usize) -> Result<String, String> {
        let (r, ms) = self.head_to_head(a, b, comp)?;
        let (na, nb) = (self.data.display_name(&self.team(a)?), self.data.display_name(&self.team(b)?));
        let mut s = format!("{na} vs {nb} ({} matches):\n", ms.len());
        for m in ms.iter().take(limit) {
            let _ = writeln!(s, "- {}", self.fmt_match(m));
        }
        if ms.len() > limit {
            let _ = writeln!(s, "- ... ({} more matches in dataset)", ms.len() - limit);
        }
        let _ = write!(
            s,
            "\nHead-to-head in dataset: {na} {} wins, {nb} {} wins, {} draws (goals {}-{})",
            r.wins, r.losses, r.draws, r.goals_for, r.goals_against
        );
        Ok(s)
    }

    pub fn team_record(&self, team: &str, f: &MatchFilter) -> Result<Record, String> {
        let k = self.team(team)?;
        let mut f = f.clone();
        f.team = Some(team.into());
        let mut r = Record::default();
        for m in self.find_matches(&f)? {
            if m.home_key == k { r.add(m.home_goals, m.away_goals) } else { r.add(m.away_goals, m.home_goals) }
        }
        Ok(r)
    }

    pub fn team_stats_text(&self, team: &str, f: &MatchFilter) -> Result<String, String> {
        let name = self.data.display_name(&self.team(team)?);
        let r = self.team_record(team, f)?;
        let mut scope = Vec::new();
        if let Some(v) = &f.venue { scope.push(format!("{v} record")); } else { scope.push("record".into()); }
        let mut ctx = Vec::new();
        if let Some(s) = f.season { ctx.push(s.to_string()); }
        if let Some(c) = f.competition { ctx.push(c.name().to_string()); }
        let mut s = format!("{name} {}", scope.join(" "));
        if !ctx.is_empty() { let _ = write!(s, " ({})", ctx.join(" ")); }
        let _ = write!(
            s,
            ":\n- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {}\n- Win rate: {:.1}%",
            r.played, r.wins, r.draws, r.losses, r.goals_for, r.goals_against, r.win_rate()
        );
        if f.competition.is_none() {
            s.push_str("\n\nBy competition:");
            for c in [Competition::Brasileirao, Competition::SerieB, Competition::SerieC, Competition::CopaDoBrasil, Competition::Libertadores] {
                let mut g = f.clone();
                g.competition = Some(c);
                let rc = self.team_record(team, &g)?;
                if rc.played > 0 {
                    let _ = write!(s, "\n- {}: {}P {}W {}D {}L, GF {} GA {}", c.name(), rc.played, rc.wins, rc.draws, rc.losses, rc.goals_for, rc.goals_against);
                }
            }
        }
        Ok(s)
    }

    /// Per-team records for all matches that pass the filter (team fields ignored).
    pub fn table(&self, f: &MatchFilter) -> Result<Vec<StandingRow>, String> {
        let mut f = f.clone();
        f.team = None;
        f.opponent = None;
        let mut map: HashMap<String, Record> = HashMap::new();
        for m in self.find_matches(&f)? {
            map.entry(m.home_key.clone()).or_default().add(m.home_goals, m.away_goals);
            map.entry(m.away_key.clone()).or_default().add(m.away_goals, m.home_goals);
        }
        let mut rows: Vec<StandingRow> = map
            .into_iter()
            .map(|(k, record)| StandingRow { team: self.data.display_name(&k), record })
            .collect();
        rows.sort_by(|a, b| {
            (b.record.points(), b.record.wins, b.record.goal_diff(), b.record.goals_for)
                .cmp(&(a.record.points(), a.record.wins, a.record.goal_diff(), a.record.goals_for))
                .then(a.team.cmp(&b.team))
        });
        Ok(rows)
    }

    pub fn standings(&self, season: i32, comp: Competition) -> Result<Vec<StandingRow>, String> {
        self.table(&MatchFilter { season: Some(season), competition: Some(comp), ..Default::default() })
    }

    pub fn standings_text(&self, season: i32, comp: Competition, limit: usize) -> Result<String, String> {
        let rows = self.standings(season, comp)?;
        if rows.is_empty() {
            return Ok(format!("No {} matches found for {season}.", comp.name()));
        }
        let mut s = format!("{season} {} Final Standings (calculated from matches):\n", comp.name());
        let n = rows.len();
        let league = matches!(comp, Competition::Brasileirao | Competition::SerieB | Competition::SerieC);
        for (i, r) in rows.iter().enumerate().take(limit.max(1)) {
            let rc = &r.record;
            let _ = write!(s, "{}. {} - {} pts ({}W, {}D, {}L, GD {:+}, {} played)", i + 1, r.team, rc.points(), rc.wins, rc.draws, rc.losses, rc.goal_diff(), rc.played);
            if i == 0 && league { s.push_str(" - Champion"); }
            if league && n >= 16 && i >= n - 4 { s.push_str(" - Relegated"); }
            s.push('\n');
        }
        if league && n >= 16 {
            let rel: Vec<&str> = rows[n - 4..].iter().map(|r| r.team.as_str()).collect();
            let _ = write!(s, "\nRelegation zone (bottom 4): {}", rel.join(", "));
        }
        Ok(s)
    }

    pub fn biggest_wins_text(&self, f: &MatchFilter, limit: usize) -> Result<String, String> {
        let mut ms = self.find_matches(f)?;
        ms.sort_by(|a, b| {
            let d = |m: &Match| (m.home_goals as i64 - m.away_goals as i64).abs();
            d(b).cmp(&d(a)).then((b.home_goals + b.away_goals).cmp(&(a.home_goals + a.away_goals))).then(b.date.cmp(&a.date))
        });
        let mut s = String::from("Biggest victories in dataset:\n");
        for (i, m) in ms.iter().take(limit).enumerate() {
            let _ = writeln!(s, "{}. {}", i + 1, self.fmt_match(m));
        }
        Ok(s)
    }

    pub fn league_stats_text(&self, f: &MatchFilter) -> Result<String, String> {
        let ms = self.find_matches(f)?;
        if ms.is_empty() {
            return Ok("No matches match the filter.".into());
        }
        let n = ms.len() as f64;
        let goals: u32 = ms.iter().map(|m| m.home_goals + m.away_goals).sum();
        let hw = ms.iter().filter(|m| m.home_goals > m.away_goals).count() as f64;
        let aw = ms.iter().filter(|m| m.home_goals < m.away_goals).count() as f64;
        let mut s = format!(
            "Statistics for {} matches:\n- Total goals: {goals}\n- Average goals per match: {:.2}\n- Home win rate: {:.1}%\n- Away win rate: {:.1}%\n- Draw rate: {:.1}%",
            ms.len(), goals as f64 / n, 100.0 * hw / n, 100.0 * aw / n, 100.0 * (n - hw - aw) / n
        );
        let ex: Vec<[f64; 6]> = ms.iter().filter_map(|m| m.extra).collect();
        if !ex.is_empty() {
            let k = ex.len() as f64;
            let avg = |i: usize, j: usize| ex.iter().map(|e| e[i] + e[j]).sum::<f64>() / k;
            let _ = write!(s, "\n- Extended stats ({} matches): avg corners {:.1}, avg shots {:.1}, avg attacks {:.1}", ex.len(), avg(0, 1), avg(4, 5), avg(2, 3));
        }
        let mut by_season: HashMap<i32, (u32, u32)> = HashMap::new();
        for m in &ms {
            let e = by_season.entry(m.season).or_default();
            e.0 += 1;
            e.1 += m.home_goals + m.away_goals;
        }
        if by_season.len() > 1 {
            let mut v: Vec<_> = by_season.into_iter().collect();
            v.sort();
            s.push_str("\n\nBy season:");
            for (season, (c, g)) in v {
                let _ = write!(s, "\n- {season}: {c} matches, {:.2} goals/match", g as f64 / c as f64);
            }
        }
        Ok(s)
    }

    /// Rank teams by a metric: "goals", "home", "away", "win_rate", "defense".
    pub fn rank_teams_text(&self, f: &MatchFilter, metric: &str, min_matches: u32, limit: usize) -> Result<String, String> {
        let mut g = f.clone();
        g.venue = None;
        let venue = fold(f.venue.as_deref().unwrap_or(match metric { "home" | "away" => metric, _ => "" }));
        let mut map: HashMap<String, Record> = HashMap::new();
        for m in self.find_matches(&MatchFilter { team: None, opponent: None, ..g })? {
            if venue != "away" {
                map.entry(m.home_key.clone()).or_default().add(m.home_goals, m.away_goals);
            }
            if venue != "home" {
                map.entry(m.away_key.clone()).or_default().add(m.away_goals, m.home_goals);
            }
        }
        let mut rows: Vec<(String, Record)> = map.into_iter().filter(|(_, r)| r.played >= min_matches).collect();
        let metric = fold(metric);
        rows.sort_by(|a, b| {
            let key = |r: &Record| -> (i64, i64) {
                match metric.as_str() {
                    "goals" => (r.goals_for as i64, r.goal_diff()),
                    "defense" => (-(r.goals_against as i64 * 1000 / r.played.max(1) as i64), r.goal_diff()),
                    _ => ((r.win_rate() * 100.0) as i64, r.played as i64),
                }
            };
            key(&b.1).cmp(&key(&a.1)).then(a.0.cmp(&b.0))
        });
        let label = if venue.is_empty() { "overall" } else { venue.as_str() };
        let mut s = format!("Teams ranked by {metric} ({label} matches, min {min_matches} played):\n");
        for (i, (k, r)) in rows.iter().take(limit).enumerate() {
            let _ = writeln!(s, "{}. {} - {}P {}W {}D {}L, GF {} GA {}, win rate {:.1}%", i + 1, self.data.display_name(k), r.played, r.wins, r.draws, r.losses, r.goals_for, r.goals_against, r.win_rate());
        }
        Ok(s)
    }

    pub fn team_competitions_text(&self, team: &str) -> Result<String, String> {
        let k = self.team(team)?;
        let mut map: HashMap<&'static str, (u32, i32, i32, HashSet<&'static str>)> = HashMap::new();
        for m in self.data.matches.iter().filter(|m| m.home_key == k || m.away_key == k) {
            let e = map.entry(m.competition.name()).or_insert((0, i32::MAX, i32::MIN, HashSet::new()));
            e.0 += 1;
            e.1 = e.1.min(m.season);
            e.2 = e.2.max(m.season);
            e.3.insert(m.source);
        }
        let mut v: Vec<_> = map.into_iter().collect();
        v.sort_by(|a, b| b.1 .0.cmp(&a.1 .0));
        let mut s = format!("Competitions played by {} in the dataset:\n", self.data.display_name(&k));
        for (c, (n, lo, hi, srcs)) in v {
            let mut srcs: Vec<_> = srcs.into_iter().collect();
            srcs.sort();
            let _ = writeln!(s, "- {c}: {n} match records, seasons {lo}-{hi} (sources: {})", srcs.join(", "));
        }
        Ok(s)
    }

    pub fn derbies_text(&self, season: Option<i32>, limit: usize) -> Result<String, String> {
        let mut s = String::from("Derby matches:\n");
        let mut total = 0;
        for (a, b, name) in DERBIES {
            let f = MatchFilter { team: Some(a.to_string()), opponent: Some(b.to_string()), season, ..Default::default() };
            let ms = self.find_matches(&f)?;
            if ms.is_empty() { continue; }
            total += ms.len();
            let _ = writeln!(s, "\n{name} ({} matches):", ms.len());
            for m in ms.iter().take(limit) {
                let _ = writeln!(s, "- {}", self.fmt_match(m));
            }
        }
        if total == 0 { s.push_str("No derby matches found."); }
        Ok(s)
    }

    // ---------------- players ----------------

    pub fn find_players(&self, name: Option<&str>, nationality: Option<&str>, club: Option<&str>, position: Option<&str>, min_overall: Option<u32>) -> Vec<&Player> {
        let name = name.map(fold);
        let nat = nationality.map(|n| {
            let f = fold(n);
            if f == "brazilian" { "brazil".to_string() } else { f }
        });
        let club_q = club.map(|c| (fold(c), crate::data::team_key(c)));
        let pos = position.map(|p| p.to_ascii_uppercase());
        let fwd = ["ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"];
        let mid = ["CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"];
        let def = ["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"];
        let mut v: Vec<&Player> = self
            .data
            .players
            .iter()
            .filter(|p| name.as_ref().map_or(true, |n| fold(&p.name).contains(n.as_str())))
            .filter(|p| nat.as_ref().map_or(true, |n| fold(&p.nationality) == *n))
            .filter(|p| club_q.as_ref().map_or(true, |(f, k)| !p.club.is_empty() && (p.club_key == *k || fold(&p.club).contains(f.as_str()))))
            .filter(|p| {
                pos.as_deref().map_or(true, |q| match q {
                    "FORWARD" | "FORWARDS" | "ATTACKER" => fwd.contains(&p.position.as_str()),
                    "MIDFIELDER" | "MIDFIELDERS" => mid.contains(&p.position.as_str()),
                    "DEFENDER" | "DEFENDERS" => def.contains(&p.position.as_str()),
                    "GOALKEEPER" | "KEEPER" => p.position == "GK",
                    q => p.position == q,
                })
            })
            .filter(|p| min_overall.map_or(true, |m| p.overall >= m))
            .collect();
        v.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));
        v
    }

    pub fn fmt_player(p: &Player, detailed: bool) -> String {
        let mut s = format!("{} - Overall: {}, Position: {}, Club: {}, Nationality: {}, Age: {}", p.name, p.overall, p.position, if p.club.is_empty() { "(none)" } else { &p.club }, p.nationality, p.age);
        if detailed {
            let _ = write!(s, "\n    Potential: {}, Jersey: {}, Height: {}, Weight: {}, Value: {}", p.potential, p.jersey, p.height, p.weight, p.value);
            let sk: Vec<String> = p.skills.iter().map(|(n, v)| format!("{n} {v}")).collect();
            let _ = write!(s, "\n    Skills: {}", sk.join(", "));
        }
        s
    }

    pub fn players_text(&self, ps: &[&Player], limit: usize) -> String {
        let mut s = format!("Found {} players:\n", ps.len());
        let detailed = ps.len() <= 3;
        for (i, p) in ps.iter().take(limit).enumerate() {
            let _ = writeln!(s, "{}. {}", i + 1, Self::fmt_player(p, detailed));
        }
        if ps.len() > limit {
            let _ = writeln!(s, "... ({} more)", ps.len() - limit);
        }
        s
    }

    /// Cross-file query: players at clubs that appear in Brazilian match data.
    pub fn brazilian_clubs_players_text(&self, nationality: Option<&str>) -> String {
        let keys = self.data.brazilian_team_keys();
        let nat = nationality.map(fold);
        let mut map: HashMap<&str, (u32, u32, &str)> = HashMap::new();
        for p in &self.data.players {
            if p.club.is_empty() || !keys.contains(p.club_key.as_str()) { continue; }
            if let Some(n) = &nat { if fold(&p.nationality) != *n { continue; } }
            let e = map.entry(p.club_key.as_str()).or_insert((0, 0, p.club.as_str()));
            e.0 += 1;
            e.1 += p.overall;
        }
        let mut v: Vec<_> = map.into_iter().collect();
        v.sort_by(|a, b| (b.1 .1 / b.1 .0).cmp(&(a.1 .1 / a.1 .0)).then(a.0.cmp(b.0)));
        let mut s = String::from("Players at Brazilian clubs (FIFA data joined with match data):\n");
        for (k, (n, sum, club)) in v {
            let r = self.team_record(k, &MatchFilter::default()).unwrap_or_default();
            let _ = writeln!(s, "- {club}: {n} players (avg rating: {:.0}); {} matches in dataset, win rate {:.1}%", sum as f64 / n as f64, r.played, r.win_rate());
        }
        s
    }

    pub fn dataset_summary(&self) -> String {
        let mut s = String::from("Loaded datasets:\n");
        for (f, n) in &self.data.file_counts {
            let _ = writeln!(s, "- {f}: {n} rows");
        }
        let _ = write!(s, "Unique matches after de-duplication: {}\nTeams: {}", self.unique.len(), self.data.display.len());
        s
    }
}

pub const DERBIES: &[(&str, &str, &str)] = &[
    ("Flamengo", "Fluminense", "Fla-Flu"),
    ("Flamengo", "Vasco", "Clássico dos Milhões"),
    ("Corinthians", "Palmeiras", "Derby Paulista"),
    ("Corinthians", "São Paulo", "Majestoso"),
    ("Palmeiras", "São Paulo", "Choque-Rei"),
    ("Santos", "Corinthians", "Clássico Alvinegro"),
    ("Santos", "Palmeiras", "Clássico da Saudade"),
    ("Santos", "São Paulo", "San-São"),
    ("Grêmio", "Internacional", "Grenal"),
    ("Atlético Mineiro", "Cruzeiro", "Clássico Mineiro"),
    ("Botafogo", "Flamengo", "Clássico da Rivalidade"),
    ("Fluminense", "Vasco", "Clássico dos Gigantes"),
    ("Bahia", "Vitória", "Ba-Vi"),
    ("Athletico Paranaense", "Coritiba", "Atletiba"),
    ("Sport", "Náutico", "Clássico dos Clássicos"),
];
