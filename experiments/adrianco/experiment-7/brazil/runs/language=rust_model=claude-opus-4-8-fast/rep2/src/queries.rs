// =============================================================================
// Context
// -----------------------------------------------------------------------------
// Module:  queries
// Purpose: The query engine. Pure functions over a loaded `Dataset` that
//          implement the five capability categories from the specification:
//            1. Match queries        (search_matches, head_to_head)
//            2. Team queries         (team_stats)
//            3. Player queries       (search_players)
//            4. Competition queries  (standings, list_competitions)
//            5. Statistical analysis (league_statistics, biggest_wins)
//
//          Each public function returns a ready-to-display Markdown/plain-text
//          String so the MCP layer can hand results straight back to the LLM.
//          All team/competition matching is accent- and suffix-insensitive via
//          the `normalize` module.
//
// Used by: mcp.rs (one tool per public function) and the BDD test suite.
// =============================================================================

use crate::data::{Dataset, Match};
use crate::normalize::{fold, team_matches};

/// Optional filters shared by match-oriented queries.
#[derive(Debug, Default, Clone)]
pub struct MatchFilter {
    pub team: Option<String>,
    pub team2: Option<String>,
    pub competition: Option<String>,
    pub season: Option<i32>,
}

fn competition_matches(comp: &str, query: &str) -> bool {
    let c = fold(comp);
    let q = fold(query);
    c.contains(&q) || q.contains(&c)
}

impl Dataset {
    /// All matches passing the given filter, sorted newest-first.
    pub fn filter_matches(&self, f: &MatchFilter) -> Vec<&Match> {
        let mut out: Vec<&Match> = self
            .matches
            .iter()
            .filter(|m| {
                if let Some(s) = f.season {
                    if m.season != s {
                        return false;
                    }
                }
                if let Some(c) = &f.competition {
                    if !competition_matches(&m.competition, c) {
                        return false;
                    }
                }
                if let Some(t) = &f.team {
                    let hit = team_matches(&m.home_team, t) || team_matches(&m.away_team, t);
                    if !hit {
                        return false;
                    }
                }
                if let Some(t2) = &f.team2 {
                    // When a second team is given, require BOTH teams present.
                    let pair = (team_matches(&m.home_team, f.team.as_deref().unwrap_or(""))
                        || team_matches(&m.away_team, f.team.as_deref().unwrap_or("")))
                        && (team_matches(&m.home_team, t2) || team_matches(&m.away_team, t2));
                    if !pair {
                        return false;
                    }
                }
                true
            })
            .collect();
        out.sort_by(|a, b| b.date.cmp(&a.date));
        out
    }

    /// Capability 1: list matches (optionally between two teams).
    pub fn search_matches(&self, f: &MatchFilter, limit: usize) -> String {
        let matches = self.filter_matches(f);
        if matches.is_empty() {
            return format!("No matches found{}.", describe_filter(f));
        }

        let mut out = String::new();
        out.push_str(&format!("Found {} match(es){}:\n", matches.len(), describe_filter(f)));

        for m in matches.iter().take(limit) {
            out.push_str(&format!("- {}\n", format_match(m)));
        }
        if matches.len() > limit {
            out.push_str(&format!("- ... ({} more not shown)\n", matches.len() - limit));
        }

        // If exactly two teams were requested, append the head-to-head summary.
        if let (Some(t1), Some(t2)) = (&f.team, &f.team2) {
            out.push('\n');
            out.push_str(&self.head_to_head(t1, t2));
        }
        out
    }

    /// Capability 1/5: head-to-head record between two teams.
    pub fn head_to_head(&self, team1: &str, team2: &str) -> String {
        let f = MatchFilter {
            team: Some(team1.to_string()),
            team2: Some(team2.to_string()),
            ..Default::default()
        };
        let matches = self.filter_matches(&f);
        if matches.is_empty() {
            return format!("No head-to-head matches found between {team1} and {team2}.");
        }

        let (mut w1, mut w2, mut draws) = (0, 0, 0);
        let (mut g1, mut g2) = (0, 0);
        for m in &matches {
            let one_is_home = team_matches(&m.home_team, team1);
            let (gs1, gs2) = if one_is_home {
                (m.home_goal, m.away_goal)
            } else {
                (m.away_goal, m.home_goal)
            };
            g1 += gs1;
            g2 += gs2;
            match gs1.cmp(&gs2) {
                std::cmp::Ordering::Greater => w1 += 1,
                std::cmp::Ordering::Less => w2 += 1,
                std::cmp::Ordering::Equal => draws += 1,
            }
        }

        format!(
            "Head-to-head in dataset ({} matches):\n- {team1}: {w1} wins\n- {team2}: {w2} wins\n- Draws: {draws}\n- Goals: {team1} {g1} - {g2} {team2}",
            matches.len()
        )
    }

    /// Capability 2: aggregate record for a team. `venue` may be
    /// "home", "away" or anything else (treated as "all").
    pub fn team_stats(
        &self,
        team: &str,
        season: Option<i32>,
        competition: Option<&str>,
        venue: &str,
    ) -> String {
        let venue = venue.to_lowercase();
        let f = MatchFilter {
            team: Some(team.to_string()),
            competition: competition.map(|s| s.to_string()),
            season,
            ..Default::default()
        };
        let matches = self.filter_matches(&f);

        let (mut wins, mut draws, mut losses) = (0, 0, 0);
        let (mut gf, mut ga, mut count) = (0, 0, 0);
        for m in &matches {
            let is_home = team_matches(&m.home_team, team);
            match venue.as_str() {
                "home" if !is_home => continue,
                "away" if is_home => continue,
                _ => {}
            }
            count += 1;
            let (scored, conceded) = if is_home {
                (m.home_goal, m.away_goal)
            } else {
                (m.away_goal, m.home_goal)
            };
            gf += scored;
            ga += conceded;
            match scored.cmp(&conceded) {
                std::cmp::Ordering::Greater => wins += 1,
                std::cmp::Ordering::Less => losses += 1,
                std::cmp::Ordering::Equal => draws += 1,
            }
        }

        // Describe only the season/competition scope; the team is already named.
        let scope_filter = MatchFilter { team: None, ..f.clone() };
        if count == 0 {
            return format!("No matches found for {team}{}.", describe_filter(&scope_filter));
        }

        let win_rate = 100.0 * wins as f64 / count as f64;
        let scope = match venue.as_str() {
            "home" => " home",
            "away" => " away",
            _ => "",
        };
        format!(
            "{team}{scope} record{}:\n- Matches: {count}\n- Wins: {wins}, Draws: {draws}, Losses: {losses}\n- Goals For: {gf}, Goals Against: {ga} (diff {:+})\n- Win rate: {:.1}%",
            describe_filter(&scope_filter),
            gf - ga,
            win_rate
        )
    }

    /// Capability 4: league standings calculated from match results
    /// (3 points for a win, 1 for a draw). Best for round-robin leagues.
    pub fn standings(&self, competition: &str, season: i32) -> String {
        let f = MatchFilter {
            competition: Some(competition.to_string()),
            season: Some(season),
            ..Default::default()
        };
        let matches = self.filter_matches(&f);
        if matches.is_empty() {
            return format!("No matches found for {competition} in {season}.");
        }

        use std::collections::HashMap;
        #[derive(Default, Clone)]
        struct Row {
            // Display name (shortest raw seen for this identity) so that
            // "Grêmio"/"Gremio-RS" or "Flamengo"/"Flamengo-RJ" collapse to one
            // row while distinct clubs (Atlético-MG vs Atlético-PR) stay apart.
            display: String,
            played: i32,
            w: i32,
            d: i32,
            l: i32,
            gf: i32,
            ga: i32,
        }
        // Keyed by the data-derived canonical team identity.
        let mut table: HashMap<String, Row> = HashMap::new();

        let set_display = |row: &mut Row, name: &str| {
            if row.display.is_empty() || name.chars().count() < row.display.chars().count() {
                row.display = name.to_string();
            }
        };

        for m in &matches {
            let h = table.entry(self.canon.key(&m.home_raw)).or_default();
            set_display(h, &m.home_raw);
            h.played += 1;
            h.gf += m.home_goal;
            h.ga += m.away_goal;
            match m.result() {
                "Home" => h.w += 1,
                "Draw" => h.d += 1,
                _ => h.l += 1,
            }
            let a = table.entry(self.canon.key(&m.away_raw)).or_default();
            set_display(a, &m.away_raw);
            a.played += 1;
            a.gf += m.away_goal;
            a.ga += m.home_goal;
            match m.result() {
                "Away" => a.w += 1,
                "Draw" => a.d += 1,
                _ => a.l += 1,
            }
        }

        let mut rows: Vec<(String, Row, i32)> = table
            .into_values()
            .map(|r| {
                let pts = r.w * 3 + r.d;
                (r.display.clone(), r, pts)
            })
            .collect();
        // Sort by points, then goal difference, then goals for.
        rows.sort_by(|a, b| {
            b.2.cmp(&a.2)
                .then((b.1.gf - b.1.ga).cmp(&(a.1.gf - a.1.ga)))
                .then(b.1.gf.cmp(&a.1.gf))
                .then(a.0.cmp(&b.0))
        });

        let mut out = format!(
            "{competition} {season} standings (calculated from {} matches, 3pts/win):\n",
            matches.len()
        );
        for (i, (name, r, pts)) in rows.iter().enumerate() {
            let tag = if i == 0 { "  <- Champion" } else { "" };
            out.push_str(&format!(
                "{:>2}. {} - {} pts ({}W {}D {}L, GF {} GA {}, GD {:+}){}\n",
                i + 1,
                name,
                pts,
                r.w,
                r.d,
                r.l,
                r.gf,
                r.ga,
                r.gf - r.ga,
                tag
            ));
        }
        out
    }

    /// Capability 5: league-wide aggregate statistics.
    pub fn league_statistics(&self, competition: Option<&str>, season: Option<i32>) -> String {
        let f = MatchFilter {
            competition: competition.map(|s| s.to_string()),
            season,
            ..Default::default()
        };
        let matches = self.filter_matches(&f);
        if matches.is_empty() {
            return format!("No matches found{}.", describe_filter(&f));
        }
        let n = matches.len() as f64;
        let total_goals: i32 = matches.iter().map(|m| m.total_goals()).sum();
        let home_wins = matches.iter().filter(|m| m.result() == "Home").count();
        let away_wins = matches.iter().filter(|m| m.result() == "Away").count();
        let draws = matches.iter().filter(|m| m.result() == "Draw").count();

        format!(
            "Statistics{}:\n- Matches: {}\n- Total goals: {}\n- Average goals per match: {:.2}\n- Home wins: {} ({:.1}%)\n- Away wins: {} ({:.1}%)\n- Draws: {} ({:.1}%)",
            describe_filter(&f),
            matches.len(),
            total_goals,
            total_goals as f64 / n,
            home_wins,
            100.0 * home_wins as f64 / n,
            away_wins,
            100.0 * away_wins as f64 / n,
            draws,
            100.0 * draws as f64 / n,
        )
    }

    /// Capability 5: the biggest victories (by goal margin) matching a filter.
    pub fn biggest_wins(&self, f: &MatchFilter, limit: usize) -> String {
        let mut matches = self.filter_matches(f);
        if matches.is_empty() {
            return format!("No matches found{}.", describe_filter(f));
        }
        matches.sort_by(|a, b| {
            (b.home_goal - b.away_goal)
                .abs()
                .cmp(&(a.home_goal - a.away_goal).abs())
                .then(b.total_goals().cmp(&a.total_goals()))
        });
        let mut out = format!("Biggest victories{}:\n", describe_filter(f));
        for (i, m) in matches.iter().take(limit).enumerate() {
            out.push_str(&format!("{:>2}. {}\n", i + 1, format_match(m)));
        }
        out
    }

    /// Capability 4: which competitions and seasons are available.
    pub fn list_competitions(&self) -> String {
        use std::collections::BTreeMap;
        let mut map: BTreeMap<String, (i32, i32, usize)> = BTreeMap::new();
        for m in &self.matches {
            let e = map.entry(m.competition.clone()).or_insert((i32::MAX, i32::MIN, 0));
            if m.season > 0 {
                e.0 = e.0.min(m.season);
                e.1 = e.1.max(m.season);
            }
            e.2 += 1;
        }
        let mut out = String::from("Available competitions:\n");
        for (comp, (min, max, count)) in map {
            let range = if min == i32::MAX {
                "n/a".to_string()
            } else {
                format!("{min}-{max}")
            };
            out.push_str(&format!("- {comp}: {count} matches (seasons {range})\n"));
        }
        out
    }

    /// Capability 3: search players by name / nationality / club / position.
    pub fn search_players(
        &self,
        name: Option<&str>,
        nationality: Option<&str>,
        club: Option<&str>,
        position: Option<&str>,
        limit: usize,
    ) -> String {
        let mut hits: Vec<&crate::data::Player> = self
            .players
            .iter()
            .filter(|p| {
                if let Some(n) = name {
                    if !fold(&p.name).contains(&fold(n)) {
                        return false;
                    }
                }
                if let Some(nat) = nationality {
                    if fold(&p.nationality) != fold(nat) {
                        return false;
                    }
                }
                if let Some(c) = club {
                    if !team_matches(&p.club, c) {
                        return false;
                    }
                }
                if let Some(pos) = position {
                    if fold(&p.position) != fold(pos) {
                        return false;
                    }
                }
                true
            })
            .collect();

        if hits.is_empty() {
            return "No players found matching the given criteria.".to_string();
        }
        hits.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));

        let total = hits.len();
        let mut out = format!("Found {total} player(s):\n");
        for (i, p) in hits.iter().take(limit).enumerate() {
            let club = if p.club.is_empty() { "Free agent" } else { &p.club };
            out.push_str(&format!(
                "{:>2}. {} - Overall: {}, Potential: {}, Pos: {}, Club: {}, Nat: {}\n",
                i + 1,
                p.name,
                p.overall,
                p.potential,
                if p.position.is_empty() { "?" } else { &p.position },
                club,
                p.nationality,
            ));
        }
        if total > limit {
            out.push_str(&format!("... ({} more not shown)\n", total - limit));
        }
        out
    }
}

/// Render a single match line, e.g.
/// "2019-10-27: Flamengo 5-0 Grêmio (Brasileirão Série A, Round 30)".
fn format_match(m: &Match) -> String {
    let date = if m.date.is_empty() { "????-??-??" } else { &m.date };
    let mut ctx = m.competition.clone();
    if let Some(r) = &m.round {
        if !r.is_empty() {
            ctx.push_str(&format!(", Round {r}"));
        }
    }
    if let Some(s) = &m.stage {
        if !s.is_empty() {
            ctx.push_str(&format!(", {s}"));
        }
    }
    format!(
        "{date}: {} {}-{} {} ({ctx})",
        m.home_team, m.home_goal, m.away_goal, m.away_team
    )
}

/// Human-readable description of the active filter, for message headers.
fn describe_filter(f: &MatchFilter) -> String {
    let mut parts = Vec::new();
    if let Some(t) = &f.team {
        parts.push(format!("for {t}"));
    }
    if let Some(t2) = &f.team2 {
        parts.push(format!("vs {t2}"));
    }
    if let Some(c) = &f.competition {
        parts.push(format!("in {c}"));
    }
    if let Some(s) = &f.season {
        parts.push(format!("({s})"));
    }
    if parts.is_empty() {
        String::new()
    } else {
        format!(" {}", parts.join(" "))
    }
}
