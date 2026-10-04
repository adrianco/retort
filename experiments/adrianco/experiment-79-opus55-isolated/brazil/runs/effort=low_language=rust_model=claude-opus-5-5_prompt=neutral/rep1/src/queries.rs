//! Query layer: every public method answers one family of questions and
//! returns a formatted, human readable text block.

use crate::data::{Competition, Database, Match, Player, Source};
use crate::normalize::{canonical, fold, is_known_club, parse_date, DERBIES};
use std::collections::{BTreeMap, HashMap};
use std::fmt::Write;

pub type QResult = Result<String, String>;

#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub enum Venue {
    Home,
    Away,
    #[default]
    Either,
}

impl Venue {
    pub fn parse(s: &str) -> Result<Venue, String> {
        match fold(s).as_str() {
            "home" | "casa" | "mandante" => Ok(Venue::Home),
            "away" | "fora" | "visitante" => Ok(Venue::Away),
            "either" | "both" | "all" | "any" | "" => Ok(Venue::Either),
            _ => Err(format!("Unknown venue '{s}'. Use home, away or either.")),
        }
    }

    fn label(self) -> &'static str {
        match self {
            Venue::Home => "home ",
            Venue::Away => "away ",
            Venue::Either => "",
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct MatchFilter {
    pub team: Option<String>,
    pub opponent: Option<String>,
    pub venue: Venue,
    pub competition: Option<Competition>,
    pub season: Option<u16>,
    pub date_from: Option<String>,
    pub date_to: Option<String>,
    /// Substring of the stage ("final", "semifinals") or an exact round number.
    pub stage: Option<String>,
    /// Restrict to one CSV file instead of the de-duplicated primary view.
    pub source: Option<Source>,
}

#[derive(Debug, Clone, Default)]
pub struct PlayerFilter {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    /// Position code (ST, GK...) or group: forward, midfielder, defender, goalkeeper.
    pub position: Option<String>,
    pub min_overall: Option<u32>,
}

#[derive(Debug, Clone, Copy, Default, PartialEq)]
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
}

fn pct(n: u32, d: u32) -> f64 {
    if d == 0 { 0.0 } else { n as f64 * 100.0 / d as f64 }
}

fn position_group(pos: &str) -> &'static str {
    match pos {
        "GK" => "goalkeeper",
        "ST" | "CF" | "LF" | "RF" | "LS" | "RS" | "LW" | "RW" => "forward",
        "CB" | "LB" | "RB" | "LCB" | "RCB" | "LWB" | "RWB" => "defender",
        "" => "",
        _ => "midfielder",
    }
}

fn derby_name(a: &str, b: &str) -> Option<&'static str> {
    DERBIES
        .iter()
        .find(|(x, y, _)| (fold(x) == a && fold(y) == b) || (fold(x) == b && fold(y) == a))
        .map(|d| d.2)
}

pub fn format_match(m: &Match) -> String {
    let date = m.date.as_deref().unwrap_or("date unknown");
    let mut ctx = format!("{} {}", m.competition.name(), m.season);
    if let Some(s) = &m.stage {
        let _ = write!(ctx, ", {s}");
    } else if let Some(r) = &m.round {
        let _ = write!(ctx, ", Round {r}");
    }
    if let Some(a) = &m.arena {
        let _ = write!(ctx, ", {a}");
    }
    let mut line = match m.score() {
        Some((h, a)) => format!("{date}: {} {h}-{a} {} ({ctx})", m.home, m.away),
        None => format!("{date}: {} vs {} ({ctx}; no score recorded)", m.home, m.away),
    };
    if let Some(e) = &m.extra {
        let pair = |a: Option<u32>, b: Option<u32>| Some(format!("{}-{}", a?, b?));
        let parts: Vec<String> = [
            pair(e.home_corner, e.away_corner).map(|p| format!("corners {p}")),
            pair(e.home_shots, e.away_shots).map(|p| format!("shots {p}")),
            pair(e.home_attack, e.away_attack).map(|p| format!("attacks {p}")),
        ]
        .into_iter()
        .flatten()
        .collect();
        if !parts.is_empty() {
            let _ = write!(line, " [{}]", parts.join(", "));
        }
    }
    line
}

fn format_player(p: &Player) -> String {
    format!(
        "{} - Overall: {}, Position: {}, Club: {}",
        p.name,
        p.overall,
        if p.position.is_empty() { "n/a" } else { &p.position },
        if p.club.is_empty() { "n/a" } else { &p.club }
    )
}

fn record_block(r: &Record) -> String {
    format!(
        "- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {} (diff {:+})\n- Points (3/1/0): {}\n- Win rate: {:.1}%\n",
        r.played, r.wins, r.draws, r.losses, r.goals_for, r.goals_against, r.goal_diff(), r.points(), r.win_rate()
    )
}

impl Database {
    /// Resolve a user supplied team name to one or more team keys.
    pub fn resolve_team(&self, query: &str) -> Result<Vec<String>, String> {
        let id = canonical(query);
        let key = self.remap.get(&id.key).unwrap_or(&id.key);
        if self.teams.contains_key(key) {
            return Ok(vec![key.clone()]);
        }
        let f = fold(query);
        let hits: Vec<String> =
            if f.is_empty() { vec![] } else { self.teams.keys().filter(|k| k.contains(&f)).cloned().collect() };
        if hits.is_empty() {
            Err(format!("No team matching '{query}' found in the match data."))
        } else {
            Ok(hits)
        }
    }

    fn team_label(&self, keys: &[String]) -> String {
        let names: Vec<&str> = keys.iter().take(4).map(|k| self.teams[k].as_str()).collect();
        let more = if keys.len() > 4 { format!(" (+{} more)", keys.len() - 4) } else { String::new() };
        format!("{}{}", names.join(" / "), more)
    }

    /// Matches satisfying the filter, most recent first.
    pub fn filter_matches(&self, f: &MatchFilter) -> Result<Vec<&Match>, String> {
        let team = f.team.as_deref().map(|t| self.resolve_team(t)).transpose()?;
        let opp = f.opponent.as_deref().map(|t| self.resolve_team(t)).transpose()?;
        let norm = |d: &Option<String>| -> Result<Option<String>, String> {
            d.as_deref()
                .map(|d| parse_date(d).ok_or_else(|| format!("Invalid date '{d}'. Use YYYY-MM-DD or DD/MM/YYYY.")))
                .transpose()
        };
        let (from, to) = (norm(&f.date_from)?, norm(&f.date_to)?);
        let stage = f.stage.as_deref().map(fold);
        let has = |keys: &Option<Vec<String>>, k: &String| keys.as_ref().map_or(true, |v| v.contains(k));

        let mut out: Vec<&Match> = self
            .matches
            .iter()
            .filter(|m| match f.source {
                Some(s) => m.source == s,
                None => m.primary,
            })
            .filter(|m| f.competition.map_or(true, |c| m.competition == c))
            .filter(|m| f.season.map_or(true, |s| m.season == s))
            .filter(|m| {
                let as_home = has(&team, &m.home_key) && has(&opp, &m.away_key);
                let as_away = has(&team, &m.away_key) && has(&opp, &m.home_key);
                match (f.venue, team.is_some() || opp.is_some()) {
                    (_, false) => true,
                    (Venue::Home, _) => as_home,
                    (Venue::Away, _) => as_away,
                    (Venue::Either, _) => as_home || as_away,
                }
            })
            .filter(|m| {
                (from.is_none() && to.is_none())
                    || m.date.as_ref().map_or(false, |d| {
                        from.as_ref().map_or(true, |f| d >= f) && to.as_ref().map_or(true, |t| d <= t)
                    })
            })
            .filter(|m| {
                stage.as_ref().map_or(true, |s| {
                    m.stage.as_ref().map_or(false, |st| fold(st).contains(s.as_str()))
                        || m.round.as_deref() == Some(s.as_str())
                })
            })
            .collect();
        out.sort_by(|a, b| b.date.cmp(&a.date));
        Ok(out)
    }

    fn describe_filter(&self, f: &MatchFilter) -> String {
        let mut parts = Vec::new();
        if let Some(c) = f.competition {
            parts.push(c.name().to_string());
        }
        if let Some(s) = f.season {
            parts.push(s.to_string());
        }
        if let Some(s) = &f.stage {
            parts.push(format!("stage/round '{s}'"));
        }
        if let Some(d) = &f.date_from {
            parts.push(format!("from {d}"));
        }
        if let Some(d) = &f.date_to {
            parts.push(format!("until {d}"));
        }
        if let Some(s) = f.source {
            parts.push(format!("source {}", s.file()));
        }
        if parts.is_empty() { "all competitions".into() } else { parts.join(", ") }
    }

    /// Record of `keys` over `matches` from the team's point of view.
    fn record(keys: &[String], matches: &[&Match], venue: Venue) -> Record {
        let mut r = Record::default();
        for m in matches {
            let Some((h, a)) = m.score() else { continue };
            if venue != Venue::Away && keys.contains(&m.home_key) {
                r.add(h, a);
            } else if venue != Venue::Home && keys.contains(&m.away_key) {
                r.add(a, h);
            }
        }
        r
    }

    // ---------------------------------------------------------------- matches

    pub fn search_matches(&self, f: &MatchFilter, limit: usize) -> QResult {
        let ms = self.filter_matches(f)?;
        let mut title = match (&f.team, &f.opponent) {
            (Some(t), Some(o)) => {
                format!("{} vs {}", self.team_label(&self.resolve_team(t)?), self.team_label(&self.resolve_team(o)?))
            }
            (Some(t), None) | (None, Some(t)) => {
                format!("{} {}matches", self.team_label(&self.resolve_team(t)?), f.venue.label())
            }
            (None, None) => "Matches".to_string(),
        };
        let _ = write!(title, " ({})", self.describe_filter(f));
        if ms.is_empty() {
            return Ok(format!("{title}:\nNo matches found in the dataset."));
        }
        let mut out = format!("{title}: {} found\n", ms.len());
        for m in ms.iter().take(limit) {
            let _ = writeln!(out, "- {}", format_match(m));
        }
        if ms.len() > limit {
            let _ = writeln!(out, "- ... ({} more matches in dataset)", ms.len() - limit);
        }
        if let Some(t) = &f.team {
            let keys = self.resolve_team(t)?;
            let r = Self::record(&keys, &ms, f.venue);
            let _ = write!(
                out,
                "\n{} record in these matches: {} wins, {} draws, {} losses, goals {}-{}\n",
                self.team_label(&keys), r.wins, r.draws, r.losses, r.goals_for, r.goals_against
            );
        }
        Ok(out)
    }

    pub fn head_to_head(&self, a: &str, b: &str, competition: Option<Competition>, season: Option<u16>, limit: usize) -> QResult {
        let (ka, kb) = (self.resolve_team(a)?, self.resolve_team(b)?);
        let f = MatchFilter {
            team: Some(a.into()),
            opponent: Some(b.into()),
            competition,
            season,
            ..Default::default()
        };
        let ms = self.filter_matches(&f)?;
        let (la, lb) = (self.team_label(&ka), self.team_label(&kb));
        let derby = match (ka.as_slice(), kb.as_slice()) {
            ([x], [y]) => derby_name(x, y).map(|d| format!(" ({d} derby)")).unwrap_or_default(),
            _ => String::new(),
        };
        let mut out = format!("{la} vs {lb}{derby} - {}:\n", self.describe_filter(&f));
        if ms.is_empty() {
            out.push_str("No matches between these teams in the dataset.\n");
            return Ok(out);
        }
        for m in ms.iter().take(limit) {
            let _ = writeln!(out, "- {}", format_match(m));
        }
        if ms.len() > limit {
            let _ = writeln!(out, "- ... ({} more matches in dataset)", ms.len() - limit);
        }
        let r = Self::record(&ka, &ms, Venue::Either);
        let home = Self::record(&ka, &ms, Venue::Home);
        let away = Self::record(&ka, &ms, Venue::Away);
        let _ = write!(
            out,
            "\nHead-to-head in dataset ({} matches with a score): {la} {} wins, {lb} {} wins, {} draws\nGoals: {la} {}, {lb} {}\n{la} at home: {}W {}D {}L | {la} away: {}W {}D {}L\n",
            r.played, r.wins, r.losses, r.draws, r.goals_for, r.goals_against,
            home.wins, home.draws, home.losses, away.wins, away.draws, away.losses
        );
        Ok(out)
    }

    // ------------------------------------------------------------------ teams

    pub fn team_stats(&self, team: &str, f: &MatchFilter) -> QResult {
        let keys = self.resolve_team(team)?;
        let f = MatchFilter { team: Some(team.into()), ..f.clone() };
        let ms = self.filter_matches(&f)?;
        let label = self.team_label(&keys);
        let mut out = format!("{label} {}record ({}):\n", f.venue.label(), self.describe_filter(&f));
        let r = Self::record(&keys, &ms, f.venue);
        if r.played == 0 {
            out.push_str("No played matches found in the dataset.\n");
            return Ok(out);
        }
        out.push_str(&record_block(&r));
        if f.venue == Venue::Either {
            let (h, a) = (Self::record(&keys, &ms, Venue::Home), Self::record(&keys, &ms, Venue::Away));
            let _ = writeln!(
                out,
                "- Home: {}W {}D {}L ({:.1}% wins) | Away: {}W {}D {}L ({:.1}% wins)",
                h.wins, h.draws, h.losses, h.win_rate(), a.wins, a.draws, a.losses, a.win_rate()
            );
        }
        if f.competition.is_none() {
            out.push_str("\nBy competition:\n");
            for c in Competition::ALL {
                let sub: Vec<&Match> = ms.iter().copied().filter(|m| m.competition == c).collect();
                let r = Self::record(&keys, &sub, f.venue);
                if r.played > 0 {
                    let _ = writeln!(
                        out,
                        "- {}: {} matches, {}W {}D {}L, goals {}-{}",
                        c.name(), r.played, r.wins, r.draws, r.losses, r.goals_for, r.goals_against
                    );
                }
            }
        }
        Ok(out)
    }

    /// Cross-file view: match history per competition plus FIFA squad.
    pub fn team_profile(&self, team: &str) -> QResult {
        let keys = self.resolve_team(team)?;
        let label = self.team_label(&keys);
        let f = MatchFilter { team: Some(team.into()), ..Default::default() };
        let ms = self.filter_matches(&f)?;
        let mut out = format!("{label} - profile across all datasets\n\nCompetitions played:\n");
        for c in Competition::ALL {
            let sub: Vec<&Match> = ms.iter().copied().filter(|m| m.competition == c).collect();
            if sub.is_empty() {
                continue;
            }
            let (lo, hi) = (sub.iter().map(|m| m.season).min().unwrap(), sub.iter().map(|m| m.season).max().unwrap());
            let r = Self::record(&keys, &sub, Venue::Either);
            let _ = writeln!(
                out,
                "- {} ({lo}-{hi}): {} matches, {}W {}D {}L, goals {}-{}",
                c.name(), r.played, r.wins, r.draws, r.losses, r.goals_for, r.goals_against
            );
        }
        let files: Vec<String> = Source::ALL
            .into_iter()
            .filter_map(|s| {
                let n = self
                    .matches
                    .iter()
                    .filter(|m| m.source == s && (keys.contains(&m.home_key) || keys.contains(&m.away_key)))
                    .count();
                (n > 0).then(|| format!("{} ({n})", s.file()))
            })
            .collect();
        let _ = writeln!(out, "\nRaw rows per file: {}", files.join(", "));
        if let Some(m) = ms.iter().find(|m| m.score().is_some()) {
            let _ = writeln!(out, "Most recent result: {}", format_match(m));
        }
        let mut squad: Vec<&Player> = self.players.iter().filter(|p| keys.contains(&p.club_key)).collect();
        squad.sort_by(|a, b| b.overall.cmp(&a.overall));
        if squad.is_empty() {
            out.push_str("\nFIFA player data: no players listed for this club (many Brazilian clubs are unlicensed in the FIFA dataset).\n");
        } else {
            let avg = squad.iter().map(|p| p.overall as f64).sum::<f64>() / squad.len() as f64;
            let _ = writeln!(out, "\nFIFA squad: {} players (avg rating: {avg:.1}). Top rated:", squad.len());
            for (i, p) in squad.iter().take(10).enumerate() {
                let _ = writeln!(out, "{}. {}", i + 1, format_player(p));
            }
        }
        Ok(out)
    }

    // ---------------------------------------------------------- competitions

    /// League table rows sorted by points, wins, goal difference, goals scored.
    pub fn table(&self, competition: Competition, season: u16, venue: Venue) -> Vec<(String, Record)> {
        let mut map: HashMap<&str, Record> = HashMap::new();
        for m in self.matches.iter().filter(|m| m.primary && m.competition == competition && m.season == season) {
            let Some((h, a)) = m.score() else { continue };
            if venue != Venue::Away {
                map.entry(&m.home_key).or_default().add(h, a);
            }
            if venue != Venue::Home {
                map.entry(&m.away_key).or_default().add(a, h);
            }
        }
        let mut rows: Vec<(String, Record)> = map.into_iter().map(|(k, r)| (self.teams[k].clone(), r)).collect();
        rows.sort_by(|a, b| {
            (b.1.points(), b.1.wins, b.1.goal_diff(), b.1.goals_for)
                .cmp(&(a.1.points(), a.1.wins, a.1.goal_diff(), a.1.goals_for))
                .then_with(|| a.0.cmp(&b.0))
        });
        rows
    }

    fn season_source(&self, competition: Competition, season: u16) -> Option<Source> {
        self.matches.iter().find(|m| m.primary && m.competition == competition && m.season == season).map(|m| m.source)
    }

    fn seasons_available(&self, competition: Competition) -> String {
        let mut s: Vec<u16> = self.matches.iter().filter(|m| m.competition == competition).map(|m| m.season).collect();
        s.sort();
        s.dedup();
        match (s.first(), s.last()) {
            (Some(a), Some(b)) => format!("{a}-{b}"),
            _ => "none".into(),
        }
    }

    /// A double round-robin is complete when every team played 2*(n-1) matches.
    fn is_complete(rows: &[(String, Record)]) -> bool {
        let n = rows.len() as u32;
        n > 1 && rows.iter().all(|(_, r)| r.played == 2 * (n - 1))
    }

    pub fn standings(&self, competition: Competition, season: u16) -> QResult {
        if !competition.is_league() {
            return Err(format!(
                "{} is a knockout competition; use competition_summary for its results.",
                competition.name()
            ));
        }
        let rows = self.table(competition, season, Venue::Either);
        if rows.is_empty() {
            return Err(format!(
                "No {} matches for season {season} (available seasons: {}).",
                competition.name(),
                self.seasons_available(competition)
            ));
        }
        let complete = Self::is_complete(&rows);
        let mut out = format!("{season} {} Standings (calculated from matches):\n", competition.name());
        let n = rows.len();
        for (i, (name, r)) in rows.iter().enumerate() {
            let tag = if !complete {
                ""
            } else if i == 0 {
                " - Champion"
            } else if competition == Competition::SerieA && i + 4 >= n {
                " - Relegated"
            } else {
                ""
            };
            let _ = writeln!(
                out,
                "{}. {name} - {} pts ({}W, {}D, {}L), goals {}-{} ({:+}){tag}",
                i + 1, r.points(), r.wins, r.draws, r.losses, r.goals_for, r.goals_against, r.goal_diff()
            );
        }
        let src = self.season_source(competition, season).map(|s| s.file()).unwrap_or("?");
        let _ = write!(out, "\nSource: {src}. ");
        if complete {
            out.push_str("Table computed with 3 points per win; ties broken by wins, goal difference, goals scored. Official tables may differ where points were deducted. Relegation marks the bottom four (current Série A rule).\n");
        } else {
            out.push_str("Note: the season is incomplete or irregular in this dataset (teams have differing match counts), so no champion/relegation labels are shown.\n");
            if src == Source::BrFootball.file() {
                out.push_str("This file has no season column; matches are grouped by calendar year.\n");
            }
        }
        Ok(out)
    }

    pub fn competition_summary(&self, competition: Competition, season: u16) -> QResult {
        let f = MatchFilter { competition: Some(competition), season: Some(season), ..Default::default() };
        let mut ms = self.filter_matches(&f)?;
        if ms.is_empty() {
            return Err(format!(
                "No {} matches for season {season} (available seasons: {}).",
                competition.name(),
                self.seasons_available(competition)
            ));
        }
        ms.reverse(); // chronological
        let mut out = format!("{} {season} - summary\n{}", competition.name(), self.stats_block(&ms));
        if competition.is_league() {
            let rows = self.table(competition, season, Venue::Either);
            let complete = Self::is_complete(&rows);
            if complete {
                let _ = writeln!(out, "Champion: {} ({} pts)", rows[0].0, rows[0].1.points());
                if competition == Competition::SerieA {
                    let rel: Vec<&str> = rows[rows.len() - 4..].iter().map(|r| r.0.as_str()).collect();
                    let _ = writeln!(out, "Relegated (bottom four): {}", rel.join(", "));
                }
            } else {
                let _ = writeln!(out, "Leader (season incomplete in dataset): {} ({} pts)", rows[0].0, rows[0].1.points());
            }
            let top = rows.iter().max_by_key(|r| r.1.goals_for).unwrap();
            let best_def = rows.iter().min_by_key(|r| r.1.goals_against).unwrap();
            let _ = writeln!(out, "Most goals scored: {} ({})", top.0, top.1.goals_for);
            let _ = writeln!(out, "Fewest goals conceded: {} ({})", best_def.0, best_def.1.goals_against);
            out.push_str("Top 5:\n");
            for (i, (n, r)) in rows.iter().take(5).enumerate() {
                let _ = writeln!(out, "{}. {n} - {} pts ({}W, {}D, {}L)", i + 1, r.points(), r.wins, r.draws, r.losses);
            }
            return Ok(out);
        }

        // Knockout competitions: group by stage / round.
        let mut stages: Vec<(String, Vec<&Match>)> = Vec::new();
        for m in &ms {
            let name = match (&m.stage, &m.round) {
                (Some(s), _) => s.clone(),
                (None, Some(r)) => format!("round {r}"),
                (None, None) => "stage not recorded".to_string(),
            };
            match stages.iter_mut().find(|(n, _)| *n == name) {
                Some((_, v)) => v.push(m),
                None => stages.push((name, vec![m])),
            }
        }
        let order = |n: &str| match n {
            "group stage" => 0,
            "round of 16" => 101,
            "quarterfinals" => 102,
            "semifinals" => 103,
            "final" => 104,
            other => other.strip_prefix("round ").and_then(|r| r.parse::<u32>().ok()).unwrap_or(50),
        };
        stages.sort_by_key(|(n, _)| order(n));
        out.push_str("\nBracket / results by stage:\n");
        for (name, list) in &stages {
            if list.len() > 16 {
                let _ = writeln!(out, "{name}: {} matches (use search_matches with stage='{}' to list them)", list.len(), name.trim_start_matches("round "));
                continue;
            }
            let _ = writeln!(out, "{name}:");
            for m in list {
                let _ = writeln!(out, "  - {}", format_match(m));
            }
        }
        if let Some((_, fin)) = stages.iter().find(|(n, _)| n == "final") {
            let mut agg: BTreeMap<&str, u32> = BTreeMap::new();
            let mut scored = true;
            for m in fin {
                match m.score() {
                    Some((h, a)) => {
                        *agg.entry(&m.home).or_default() += h;
                        *agg.entry(&m.away).or_default() += a;
                    }
                    None => scored = false,
                }
            }
            let v: Vec<(&str, u32)> = agg.into_iter().collect();
            if scored && v.len() == 2 {
                if v[0].1 == v[1].1 {
                    let _ = writeln!(out, "\nFinal: {} {}-{} {} on aggregate - decided by a tie-breaker (away goals/penalties) not recorded in the dataset.", v[0].0, v[0].1, v[1].1, v[1].0);
                } else {
                    let (w, l) = if v[0].1 > v[1].1 { (v[0], v[1]) } else { (v[1], v[0]) };
                    let _ = writeln!(out, "\nChampion: {} (final aggregate {}-{} over {})", w.0, w.1, l.1, l.0);
                }
            } else {
                out.push_str("\nFinal has no recorded score in the dataset.\n");
            }
        }
        Ok(out)
    }

    // ------------------------------------------------------------- statistics

    fn stats_block(&self, ms: &[&Match]) -> String {
        let played: Vec<(&Match, u32, u32)> = ms.iter().filter_map(|m| m.score().map(|(h, a)| (*m, h, a))).collect();
        let n = played.len() as u32;
        if n == 0 {
            return format!("Matches: {} (none with a recorded score)\n", ms.len());
        }
        let goals: u32 = played.iter().map(|(_, h, a)| h + a).sum();
        let hg: u32 = played.iter().map(|(_, h, _)| h).sum();
        let hw = played.iter().filter(|(_, h, a)| h > a).count() as u32;
        let dr = played.iter().filter(|(_, h, a)| h == a).count() as u32;
        let aw = n - hw - dr;
        let top = played.iter().max_by_key(|(_, h, a)| h + a).unwrap().0;
        format!(
            "Matches played: {n}\nTotal goals: {goals}\nAverage goals per match: {:.2} (home {:.2}, away {:.2})\nHome win rate: {:.1}%\nDraw rate: {:.1}%\nAway win rate: {:.1}%\nHighest scoring match: {}\n",
            goals as f64 / n as f64,
            hg as f64 / n as f64,
            (goals - hg) as f64 / n as f64,
            pct(hw, n), pct(dr, n), pct(aw, n),
            format_match(top)
        )
    }

    pub fn league_stats(&self, f: &MatchFilter) -> QResult {
        let ms = self.filter_matches(f)?;
        if ms.is_empty() {
            return Ok(format!("Statistics ({}):\nNo matches found in the dataset.", self.describe_filter(f)));
        }
        let team = match &f.team {
            Some(t) => format!("{} - ", self.team_label(&self.resolve_team(t)?)),
            None => String::new(),
        };
        Ok(format!("Statistics ({team}{}):\n{}", self.describe_filter(f), self.stats_block(&ms)))
    }

    pub fn biggest_wins(&self, f: &MatchFilter, limit: usize) -> QResult {
        let mut ms: Vec<(&Match, i64, u32)> = self
            .filter_matches(f)?
            .into_iter()
            .filter_map(|m| m.score().map(|(h, a)| (m, (h as i64 - a as i64).abs(), h + a)))
            .collect();
        ms.sort_by(|a, b| (b.1, b.2, &b.0.date).cmp(&(a.1, a.2, &a.0.date)));
        let mut out = format!("Biggest victories ({}):\n", self.describe_filter(f));
        if ms.is_empty() {
            out.push_str("No matches found in the dataset.\n");
        }
        for (i, (m, _, _)) in ms.iter().take(limit).enumerate() {
            let _ = writeln!(out, "{}. {}", i + 1, format_match(m));
        }
        Ok(out)
    }

    /// Rank teams by a metric: win_rate, points, points_per_game, goals_for,
    /// goals_against, goal_difference, wins.
    pub fn team_rankings(&self, metric: &str, f: &MatchFilter, min_matches: Option<u32>, limit: usize) -> QResult {
        let ms = self.filter_matches(&MatchFilter { team: None, opponent: None, ..f.clone() })?;
        let mut map: HashMap<&str, Record> = HashMap::new();
        for m in &ms {
            let Some((h, a)) = m.score() else { continue };
            if f.venue != Venue::Away {
                map.entry(&m.home_key).or_default().add(h, a);
            }
            if f.venue != Venue::Home {
                map.entry(&m.away_key).or_default().add(a, h);
            }
        }
        let min = min_matches.unwrap_or(if f.season.is_some() { 5 } else { 30 });
        let metric_f = fold(metric).replace(' ', "_");
        let (label, asc): (&str, bool) = match metric_f.as_str() {
            "win_rate" | "record" | "" => ("win rate", false),
            "points" => ("points", false),
            "points_per_game" | "ppg" => ("points per game", false),
            "goals_for" | "goals_scored" | "goals" => ("goals scored", false),
            "goals_against" | "goals_conceded" => ("goals conceded (fewest first)", true),
            "goal_difference" | "goal_diff" => ("goal difference", false),
            "wins" => ("wins", false),
            _ => return Err(format!("Unknown metric '{metric}'. Use win_rate, points, points_per_game, goals_for, goals_against, goal_difference or wins.")),
        };
        let value = |r: &Record| -> f64 {
            match label {
                "win rate" => r.win_rate(),
                "points" => r.points() as f64,
                "points per game" => r.points() as f64 / r.played as f64,
                "goals scored" => r.goals_for as f64,
                "goal difference" => r.goal_diff() as f64,
                "wins" => r.wins as f64,
                _ => r.goals_against as f64,
            }
        };
        let mut rows: Vec<(&str, Record, f64)> =
            map.into_iter().filter(|(_, r)| r.played >= min).map(|(k, r)| (self.teams[k].as_str(), r, value(&r))).collect();
        rows.sort_by(|a, b| {
            let o = b.2.partial_cmp(&a.2).unwrap().then(b.1.played.cmp(&a.1.played));
            let o = if asc { a.2.partial_cmp(&b.2).unwrap() } else { o };
            o.then_with(|| a.0.cmp(b.0))
        });
        let mut out = format!(
            "Team ranking by {}{label} ({}; minimum {min} matches):\n",
            f.venue.label(),
            self.describe_filter(f)
        );
        if rows.is_empty() {
            out.push_str("No teams meet the criteria.\n");
        }
        for (i, (name, r, v)) in rows.iter().take(limit).enumerate() {
            let shown = match label {
                "win rate" => format!("{v:.1}% wins"),
                "points per game" => format!("{v:.2} pts/game"),
                _ => format!("{v:.0} {}", label.split(' ').next().unwrap_or("")),
            };
            let _ = writeln!(
                out,
                "{}. {name} - {shown} ({} matches: {}W {}D {}L, goals {}-{})",
                i + 1, r.played, r.wins, r.draws, r.losses, r.goals_for, r.goals_against
            );
        }
        Ok(out)
    }

    pub fn compare_seasons(&self, competition: Competition, a: u16, b: u16) -> QResult {
        let mut out = format!("{} - season comparison {a} vs {b}\n", competition.name());
        for s in [a, b] {
            let f = MatchFilter { competition: Some(competition), season: Some(s), ..Default::default() };
            let ms = self.filter_matches(&f)?;
            let _ = writeln!(out, "\n{s}:");
            if ms.is_empty() {
                let _ = writeln!(out, "No matches in dataset (available seasons: {}).", self.seasons_available(competition));
                continue;
            }
            out.push_str(&self.stats_block(&ms));
            if competition.is_league() {
                let rows = self.table(competition, s, Venue::Either);
                if let Some((n, r)) = rows.first() {
                    let tag = if Self::is_complete(&rows) { "Champion" } else { "Leader (incomplete season)" };
                    let _ = writeln!(out, "{tag}: {n} ({} pts, {}W {}D {}L)", r.points(), r.wins, r.draws, r.losses);
                }
                if let Some((n, r)) = rows.iter().max_by_key(|r| r.1.goals_for) {
                    let _ = writeln!(out, "Best attack: {n} ({} goals)", r.goals_for);
                }
            }
        }
        Ok(out)
    }

    pub fn derbies(&self, f: &MatchFilter, limit: usize) -> QResult {
        let ms: Vec<(&Match, &str)> = self
            .filter_matches(f)?
            .into_iter()
            .filter_map(|m| derby_name(&m.home_key, &m.away_key).map(|d| (m, d)))
            .collect();
        let mut out = format!("Derbies between traditional rivals ({}): {} found\n", self.describe_filter(f), ms.len());
        for (m, d) in ms.iter().take(limit) {
            let _ = writeln!(out, "- [{d}] {}", format_match(m));
        }
        if ms.len() > limit {
            let _ = writeln!(out, "- ... ({} more matches in dataset)", ms.len() - limit);
        }
        Ok(out)
    }

    // ---------------------------------------------------------------- players

    pub fn filter_players(&self, f: &PlayerFilter) -> Vec<&Player> {
        let nat = f.nationality.as_deref().map(|n| match fold(n).as_str() {
            "brazilian" | "brasil" | "brasileiro" => "brazil".to_string(),
            other => other.to_string(),
        });
        let club = f.club.as_deref().map(|c| (fold(c), canonical(c).key));
        let pos = f.position.as_deref().map(|p| fold(p).trim_end_matches('s').to_string());
        let known_club = club.as_ref().map_or(false, |(_, k)| is_known_club(k));
        let base = |tokens: Option<Vec<String>>| -> Vec<&Player> {
            self.players
                .iter()
                .filter(|p| tokens.as_ref().map_or(true, |t| {
                    let n = fold(&p.name);
                    t.iter().all(|tok| n.contains(tok.as_str()))
                }))
                .filter(|p| nat.as_ref().map_or(true, |n| fold(&p.nationality) == *n))
                .filter(|p| club.as_ref().map_or(true, |(f, k)| !p.club.is_empty() && (p.club_key == *k || (!known_club && fold(&p.club).contains(f.as_str())))))
                .filter(|p| pos.as_ref().map_or(true, |q| {
                    p.position.eq_ignore_ascii_case(q) || position_group(&p.position) == q || (q == "striker" && position_group(&p.position) == "forward")
                }))
                .filter(|p| f.min_overall.map_or(true, |m| p.overall >= m))
                .collect()
        };
        let tokens = f.name.as_deref().map(|n| fold(n).split(' ').map(String::from).collect::<Vec<_>>());
        let mut out = base(tokens);
        out.sort_by(|a, b| b.overall.cmp(&a.overall).then(b.potential.cmp(&a.potential)).then(a.name.cmp(&b.name)));
        out
    }

    pub fn search_players(&self, f: &PlayerFilter, limit: usize) -> QResult {
        let ps = self.filter_players(f);
        let mut crit = Vec::new();
        if let Some(n) = &f.name { crit.push(format!("name '{n}'")); }
        if let Some(n) = &f.nationality { crit.push(format!("nationality {n}")); }
        if let Some(n) = &f.club { crit.push(format!("club '{n}'")); }
        if let Some(n) = &f.position { crit.push(format!("position {n}")); }
        if let Some(n) = f.min_overall { crit.push(format!("overall >= {n}")); }
        let crit = if crit.is_empty() { "all players".to_string() } else { crit.join(", ") };
        if ps.is_empty() {
            let mut out = format!("Players ({crit}):\nNo players found in the FIFA dataset.\n");
            if let Some(n) = &f.name {
                out.push_str(&self.similar_players(n, f));
            }
            if f.club.is_some() {
                out.push_str("Note: several Brazilian clubs (e.g. Flamengo, Palmeiras, Corinthians, São Paulo) are not licensed in this FIFA dataset. Use brazilian_clubs_players to see which clubs are covered.\n");
            }
            return Ok(out);
        }
        let mut out = format!("Players ({crit}): {} found, sorted by overall rating\n", ps.len());
        for (i, p) in ps.iter().take(limit).enumerate() {
            let _ = writeln!(out, "{}. {}", i + 1, format_player(p));
        }
        if ps.len() > limit {
            let _ = writeln!(out, "... ({} more players in dataset)", ps.len() - limit);
        }
        let avg = ps.iter().map(|p| p.overall as f64).sum::<f64>() / ps.len() as f64;
        let _ = writeln!(out, "\nAverage overall rating: {avg:.1}");
        Ok(out)
    }

    /// Players sharing any word of `name`; the FIFA file often uses short
    /// names ("Gabriel") or initials ("G. Barbosa"), so offer candidates
    /// rather than guessing.
    fn similar_players(&self, name: &str, f: &PlayerFilter) -> String {
        let folded = fold(name);
        let mut seen: Vec<&Player> = Vec::new();
        for tok in folded.split(' ').filter(|t| t.len() > 2) {
            for p in self.filter_players(&PlayerFilter { name: Some(tok.to_string()), ..f.clone() }) {
                if !seen.iter().any(|q| q.id == p.id) {
                    seen.push(p);
                }
            }
        }
        if seen.is_empty() {
            return String::new();
        }
        seen.sort_by(|a, b| b.overall.cmp(&a.overall));
        let mut out = String::from("Players with a similar name:\n");
        for p in seen.iter().take(10) {
            let _ = writeln!(out, "- {} ({})", format_player(p), p.nationality);
        }
        out
    }

    pub fn player_details(&self, name: &str, club: Option<&str>) -> QResult {
        let f = PlayerFilter { name: Some(name.into()), club: club.map(String::from), ..Default::default() };
        let ps = self.filter_players(&f);
        let Some(p) = ps.first() else {
            return Ok(format!(
                "No player named '{name}' found in the FIFA dataset.\n{}",
                self.similar_players(name, &f)
            ));
        };
        let or_na = |s: &str| if s.is_empty() { "n/a".to_string() } else { s.to_string() };
        let mut out = format!(
            "{} (FIFA ID {})\n- Age: {}\n- Nationality: {}\n- Club: {}\n- Position: {} ({})\n- Jersey number: {}\n- Overall: {}, Potential: {}\n- Height: {}, Weight: {}\n- Preferred foot: {}\n- Value: {}, Wage: {}\n",
            p.name, p.id,
            p.age.map_or("n/a".into(), |a| a.to_string()),
            or_na(&p.nationality), or_na(&p.club), or_na(&p.position), or_na(position_group(&p.position)),
            or_na(&p.jersey), p.overall, p.potential, or_na(&p.height), or_na(&p.weight), or_na(&p.foot),
            or_na(&p.value), or_na(&p.wage)
        );
        if !p.skills.is_empty() {
            let s: Vec<String> = p.skills.iter().map(|(k, v)| format!("{k} {v}")).collect();
            let _ = writeln!(out, "- Skills: {}", s.join(", "));
        }
        if self.teams.contains_key(&p.club_key) && is_known_club(&p.club_key) {
            let keys = vec![p.club_key.clone()];
            let ms = self.filter_matches(&MatchFilter { team: Some(self.teams[&p.club_key].clone()), ..Default::default() })?;
            let r = Self::record(&keys, &ms, Venue::Either);
            let _ = writeln!(
                out,
                "- Club in match data: {} - {} matches, {}W {}D {}L",
                self.teams[&p.club_key], r.played, r.wins, r.draws, r.losses
            );
        }
        if ps.len() > 1 {
            let others: Vec<String> = ps.iter().skip(1).take(8).map(|p| format!("{} ({}, {})", p.name, p.club, p.overall)).collect();
            let _ = writeln!(out, "\nOther matches for '{name}': {}", others.join("; "));
        }
        Ok(out)
    }

    /// Players grouped by Brazilian club (clubs that also appear in the match data).
    pub fn brazilian_clubs_players(&self, nationality: Option<&str>) -> QResult {
        let f = PlayerFilter { nationality: nationality.map(String::from), ..Default::default() };
        let mut groups: BTreeMap<&str, Vec<&Player>> = BTreeMap::new();
        for p in self.filter_players(&f) {
            if is_known_club(&p.club_key) && self.teams.contains_key(&p.club_key) {
                groups.entry(self.teams[&p.club_key].as_str()).or_default().push(p);
            }
        }
        let who = nationality.map_or("Players".to_string(), |n| format!("{n} players"));
        let mut out = format!("{who} at Brazilian clubs (FIFA dataset):\n");
        let mut rows: Vec<(&str, usize, f64, &Player)> = groups
            .iter()
            .map(|(c, v)| (*c, v.len(), v.iter().map(|p| p.overall as f64).sum::<f64>() / v.len() as f64, v[0]))
            .collect();
        rows.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap());
        for (c, n, avg, best) in &rows {
            let _ = writeln!(out, "- {c}: {n} players (avg rating: {avg:.1}; best: {} {})", best.name, best.overall);
        }
        if rows.is_empty() {
            out.push_str("None found.\n");
        }
        out.push_str("\nNote: clubs such as Flamengo, Palmeiras, Corinthians and São Paulo are not licensed in this FIFA dataset.\n");
        Ok(out)
    }

    // ------------------------------------------------------------------- meta

    pub fn dataset_info(&self) -> QResult {
        let mut out = String::from("Brazilian soccer knowledge base\n\nFiles loaded:\n");
        for (f, n) in &self.file_rows {
            let _ = writeln!(out, "- {f}: {n} rows");
        }
        out.push_str("\nCompetition coverage (de-duplicated view):\n");
        for c in Competition::ALL {
            let n = self.matches.iter().filter(|m| m.primary && m.competition == c).count();
            let _ = writeln!(out, "- {}: seasons {}, {n} matches", c.name(), self.seasons_available(c));
        }
        let br = self.players.iter().filter(|p| p.nationality == "Brazil").count();
        let _ = write!(
            out,
            "\nTeams in match data: {}\nPlayers: {} ({br} Brazilian)\n\nOverlapping files are de-duplicated: each competition season is served by a single file (for leagues the first of novo_campeonato_brasileiro.csv, Brasileirao_Matches.csv, BR-Football-Dataset.csv holding a complete season, otherwise the file with most results). BR-Football-Dataset.csv has no season column, so its seasons are calendar years. Pass `source` to query one file directly.\n",
            self.teams.len(),
            self.players.len()
        );
        Ok(out)
    }

    pub fn list_teams(&self, query: Option<&str>, limit: usize) -> QResult {
        let q = query.map(fold).unwrap_or_default();
        let hits: Vec<&String> = self.teams.iter().filter(|(k, _)| k.contains(&q)).map(|(_, d)| d).collect();
        let mut out = format!("Teams in match data matching '{}': {}\n", query.unwrap_or(""), hits.len());
        for d in hits.iter().take(limit) {
            let _ = writeln!(out, "- {d}");
        }
        if hits.len() > limit {
            let _ = writeln!(out, "... ({} more)", hits.len() - limit);
        }
        Ok(out)
    }
}
