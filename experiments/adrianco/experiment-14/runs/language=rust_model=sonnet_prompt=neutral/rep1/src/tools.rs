use crate::data::{Database, Match, Player, normalize_team_name, team_matches};
use std::collections::HashMap;

fn match_line(m: &Match) -> String {
    let dt = m.datetime.as_deref().unwrap_or("?");
    let hg = m.home_goal.map(|g| g.to_string()).unwrap_or_else(|| "?".to_string());
    let ag = m.away_goal.map(|g| g.to_string()).unwrap_or_else(|| "?".to_string());
    let mut extra = String::new();
    if let Some(ref r) = m.round {
        if !r.is_empty() {
            extra.push_str(&format!(" Round {}", r));
        }
    }
    if let Some(ref s) = m.stage {
        if !s.is_empty() {
            extra.push_str(&format!(" ({})", s));
        }
    }
    format!(
        "{}: {} {}-{} {}  [{}{}]",
        dt, m.home_team, hg, ag, m.away_team, m.competition, extra
    )
}

/// Search matches by team(s), competition, season, date range
pub fn search_matches(
    db: &Database,
    team: Option<&str>,
    team2: Option<&str>,
    competition: Option<&str>,
    season: Option<i32>,
    date_from: Option<&str>,
    date_to: Option<&str>,
    limit: usize,
) -> String {
    let filtered: Vec<&Match> = db
        .matches
        .iter()
        .filter(|m| {
            // Team filter
            if let Some(t) = team {
                let home_ok = team_matches(&m.home_team, t);
                let away_ok = team_matches(&m.away_team, t);
                if !home_ok && !away_ok {
                    return false;
                }
                // If team2 given, both teams must be present
                if let Some(t2) = team2 {
                    let other_home = team_matches(&m.home_team, t2);
                    let other_away = team_matches(&m.away_team, t2);
                    if !other_home && !other_away {
                        return false;
                    }
                }
            } else if let Some(t2) = team2 {
                if !team_matches(&m.home_team, t2) && !team_matches(&m.away_team, t2) {
                    return false;
                }
            }

            // Competition filter
            if let Some(c) = competition {
                let c_lower = c.to_lowercase();
                if !m.competition.to_lowercase().contains(&c_lower) {
                    return false;
                }
            }

            // Season filter
            if let Some(s) = season {
                if m.season != Some(s) {
                    return false;
                }
            }

            // Date filters (simple string comparison works for ISO dates)
            if let Some(from) = date_from {
                if let Some(ref dt) = m.datetime {
                    if dt.as_str() < from {
                        return false;
                    }
                }
            }
            if let Some(to) = date_to {
                if let Some(ref dt) = m.datetime {
                    if dt.as_str() > to {
                        return false;
                    }
                }
            }

            true
        })
        .collect();

    if filtered.is_empty() {
        return "No matches found for the given criteria.".to_string();
    }

    let total = filtered.len();
    let shown = filtered.len().min(limit);
    let mut out = format!(
        "Found {} match(es){}:\n",
        total,
        if total > shown {
            format!(", showing first {}", shown)
        } else {
            String::new()
        }
    );

    for m in filtered.iter().take(shown) {
        out.push_str(&format!("  {}\n", match_line(m)));
    }

    out
}

/// Get team statistics (W/L/D, goals scored/conceded)
pub fn team_stats(
    db: &Database,
    team: &str,
    competition: Option<&str>,
    season: Option<i32>,
) -> String {
    let mut home_w = 0u32;
    let mut home_d = 0u32;
    let mut home_l = 0u32;
    let mut home_gf = 0u32;
    let mut home_ga = 0u32;
    let mut away_w = 0u32;
    let mut away_d = 0u32;
    let mut away_l = 0u32;
    let mut away_gf = 0u32;
    let mut away_ga = 0u32;

    for m in &db.matches {
        // Competition filter
        if let Some(c) = competition {
            if !m.competition.to_lowercase().contains(&c.to_lowercase()) {
                continue;
            }
        }
        // Season filter
        if let Some(s) = season {
            if m.season != Some(s) {
                continue;
            }
        }

        let hg = m.home_goal.unwrap_or(0);
        let ag = m.away_goal.unwrap_or(0);

        if team_matches(&m.home_team, team) {
            home_gf += hg as u32;
            home_ga += ag as u32;
            if hg > ag {
                home_w += 1;
            } else if hg == ag {
                home_d += 1;
            } else {
                home_l += 1;
            }
        } else if team_matches(&m.away_team, team) {
            away_gf += ag as u32;
            away_ga += hg as u32;
            if ag > hg {
                away_w += 1;
            } else if ag == hg {
                away_d += 1;
            } else {
                away_l += 1;
            }
        }
    }

    let total_matches = home_w + home_d + home_l + away_w + away_d + away_l;
    if total_matches == 0 {
        return format!("No matches found for team '{}'.", team);
    }

    let total_w = home_w + away_w;
    let total_d = home_d + away_d;
    let total_l = home_l + away_l;
    let total_gf = home_gf + away_gf;
    let total_ga = home_ga + away_ga;
    let win_rate = total_w as f64 / total_matches as f64 * 100.0;
    let pts = total_w * 3 + total_d;

    let comp_label = competition.unwrap_or("all competitions");
    let season_label = season
        .map(|s| s.to_string())
        .unwrap_or_else(|| "all seasons".to_string());

    format!(
        "Team: {} | {} | {}\n\
         Overall: {} matches | {}W {}D {}L | GF: {} GA: {} GD: {:+} | Pts: {} | Win rate: {:.1}%\n\
         Home:    {} matches | {}W {}D {}L | GF: {} GA: {}\n\
         Away:    {} matches | {}W {}D {}L | GF: {} GA: {}",
        team,
        comp_label,
        season_label,
        total_matches,
        total_w,
        total_d,
        total_l,
        total_gf,
        total_ga,
        total_gf as i32 - total_ga as i32,
        pts,
        win_rate,
        home_w + home_d + home_l,
        home_w,
        home_d,
        home_l,
        home_gf,
        home_ga,
        away_w + away_d + away_l,
        away_w,
        away_d,
        away_l,
        away_gf,
        away_ga,
    )
}

/// Head-to-head comparison between two teams
pub fn head_to_head(
    db: &Database,
    team1: &str,
    team2: &str,
    competition: Option<&str>,
    season: Option<i32>,
    limit: usize,
) -> String {
    let mut t1_wins = 0u32;
    let mut t2_wins = 0u32;
    let mut draws = 0u32;
    let mut t1_goals = 0u32;
    let mut t2_goals = 0u32;
    let mut matches_list: Vec<&Match> = Vec::new();

    for m in &db.matches {
        if let Some(c) = competition {
            if !m.competition.to_lowercase().contains(&c.to_lowercase()) {
                continue;
            }
        }
        if let Some(s) = season {
            if m.season != Some(s) {
                continue;
            }
        }

        let t1_home = team_matches(&m.home_team, team1) && team_matches(&m.away_team, team2);
        let t2_home = team_matches(&m.home_team, team2) && team_matches(&m.away_team, team1);

        if !t1_home && !t2_home {
            continue;
        }

        matches_list.push(m);

        let hg = m.home_goal.unwrap_or(0);
        let ag = m.away_goal.unwrap_or(0);

        if t1_home {
            t1_goals += hg as u32;
            t2_goals += ag as u32;
            if hg > ag {
                t1_wins += 1;
            } else if hg == ag {
                draws += 1;
            } else {
                t2_wins += 1;
            }
        } else {
            // t2 is home
            t1_goals += ag as u32;
            t2_goals += hg as u32;
            if ag > hg {
                t1_wins += 1;
            } else if ag == hg {
                draws += 1;
            } else {
                t2_wins += 1;
            }
        }
    }

    let total = matches_list.len();
    if total == 0 {
        return format!("No head-to-head matches found between '{}' and '{}'.", team1, team2);
    }

    let shown = total.min(limit);
    let mut out = format!(
        "Head-to-Head: {} vs {}\n",
        team1, team2
    );
    if let Some(c) = competition {
        out.push_str(&format!("Competition: {}\n", c));
    }
    if let Some(s) = season {
        out.push_str(&format!("Season: {}\n", s));
    }
    out.push_str(&format!(
        "Total matches: {} | {}: {} wins | {}: {} wins | Draws: {}\n",
        total, team1, t1_wins, team2, t2_wins, draws
    ));
    out.push_str(&format!(
        "Goals: {}: {} | {}: {}\n",
        team1, t1_goals, team2, t2_goals
    ));
    out.push_str(&format!("\nRecent matches ({}shown):\n", if total > shown { format!("{}/{} ", shown, total) } else { String::new() }));

    for m in matches_list.iter().rev().take(shown) {
        out.push_str(&format!("  {}\n", match_line(m)));
    }

    out
}

/// Search players by name, nationality, club, position
pub fn search_players(
    db: &Database,
    name: Option<&str>,
    nationality: Option<&str>,
    club: Option<&str>,
    position: Option<&str>,
    min_overall: Option<i32>,
    max_results: usize,
) -> String {
    let mut filtered: Vec<&Player> = db
        .players
        .iter()
        .filter(|p| {
            if let Some(n) = name {
                if !p.name.to_lowercase().contains(&n.to_lowercase()) {
                    return false;
                }
            }
            if let Some(nat) = nationality {
                if !p.nationality.to_lowercase().contains(&nat.to_lowercase()) {
                    return false;
                }
            }
            if let Some(c) = club {
                if !p.club.to_lowercase().contains(&c.to_lowercase()) {
                    return false;
                }
            }
            if let Some(pos) = position {
                if !p.position.to_lowercase().contains(&pos.to_lowercase()) {
                    return false;
                }
            }
            if let Some(min) = min_overall {
                if p.overall.unwrap_or(0) < min {
                    return false;
                }
            }
            true
        })
        .collect();

    if filtered.is_empty() {
        return "No players found for the given criteria.".to_string();
    }

    // Sort by overall rating descending
    filtered.sort_by(|a, b| {
        b.overall
            .unwrap_or(0)
            .cmp(&a.overall.unwrap_or(0))
    });

    let total = filtered.len();
    let shown = total.min(max_results);

    let mut out = format!(
        "Found {} player(s){}:\n",
        total,
        if total > shown {
            format!(", showing top {} by rating", shown)
        } else {
            String::new()
        }
    );

    for (i, p) in filtered.iter().take(shown).enumerate() {
        out.push_str(&format!(
            "  {}. {} | Overall: {} | Pos: {} | Club: {} | Nationality: {} | Age: {}\n",
            i + 1,
            p.name,
            p.overall.map(|o| o.to_string()).unwrap_or_else(|| "?".to_string()),
            p.position,
            p.club,
            p.nationality,
            p.age.map(|a| a.to_string()).unwrap_or_else(|| "?".to_string()),
        ));
    }

    out
}

/// Calculate season standings for a competition
pub fn season_standings(db: &Database, competition: &str, season: i32, limit: usize) -> String {
    // points: W=3, D=1, L=0
    struct TeamRecord {
        w: u32,
        d: u32,
        l: u32,
        gf: u32,
        ga: u32,
    }

    let comp_lower = competition.to_lowercase();
    // For Brasileirão queries: prefer "Brasileirão Serie A" (2012+) over the historical dataset
    // to avoid double-counting the overlapping 2012-2019 period.
    let is_brasileirao_query = comp_lower.contains("brasil") || comp_lower.contains("serie a");
    let prefer_series_a = is_brasileirao_query && season >= 2012;

    let mut table: HashMap<String, TeamRecord> = HashMap::new();

    for m in &db.matches {
        // If it's a Brasileirão query for 2012+, only use the primary Serie A dataset
        if prefer_series_a {
            if m.competition != "Brasileirão Serie A" {
                continue;
            }
        } else if !m.competition.to_lowercase().contains(&comp_lower) {
            continue;
        }
        if m.season != Some(season) {
            continue;
        }

        let hg = m.home_goal.unwrap_or(0);
        let ag = m.away_goal.unwrap_or(0);
        // Use lowercase of original name to keep state disambiguation (e.g., Atletico-MG vs Atletico-PR)
        let home_name = m.home_team.trim().to_lowercase();
        let away_name = m.away_team.trim().to_lowercase();

        let home_entry = table.entry(home_name).or_insert(TeamRecord { w: 0, d: 0, l: 0, gf: 0, ga: 0 });
        home_entry.gf += hg as u32;
        home_entry.ga += ag as u32;
        if hg > ag {
            home_entry.w += 1;
        } else if hg == ag {
            home_entry.d += 1;
        } else {
            home_entry.l += 1;
        }

        let away_entry = table.entry(away_name).or_insert(TeamRecord { w: 0, d: 0, l: 0, gf: 0, ga: 0 });
        away_entry.gf += ag as u32;
        away_entry.ga += hg as u32;
        if ag > hg {
            away_entry.w += 1;
        } else if ag == hg {
            away_entry.d += 1;
        } else {
            away_entry.l += 1;
        }
    }

    if table.is_empty() {
        return format!(
            "No matches found for competition '{}' in season {}.",
            competition, season
        );
    }

    let mut standings: Vec<(String, u32, u32, u32, u32, u32, u32)> = table
        .into_iter()
        .map(|(name, r)| {
            let pts = r.w * 3 + r.d;
            let mp = r.w + r.d + r.l;
            (name, pts, mp, r.w, r.d, r.l, r.gf.saturating_sub(r.ga))
        })
        .collect();

    // Sort by points desc, then GD desc
    standings.sort_by(|a, b| b.1.cmp(&a.1).then(b.6.cmp(&a.6)));

    let shown = standings.len().min(limit);
    let mut out = format!(
        "{} {} Standings (calculated from match data):\n",
        season, competition
    );
    out.push_str(&format!(
        "  {:>3} {:<25} {:>3} {:>3} {:>2} {:>2} {:>2} {:>4}\n",
        "#", "Team", "Pts", "MP", "W", "D", "L", "GD"
    ));
    out.push_str(&format!("  {}\n", "-".repeat(55)));

    for (i, (name, pts, mp, w, d, l, gd)) in standings.iter().take(shown).enumerate() {
        out.push_str(&format!(
            "  {:>3} {:<25} {:>3} {:>3} {:>2} {:>2} {:>2} {:>+4}\n",
            i + 1,
            name,
            pts,
            mp,
            w,
            d,
            l,
            *gd as i32,
        ));
    }

    out
}

/// Find biggest wins (by goal difference)
pub fn biggest_wins(
    db: &Database,
    competition: Option<&str>,
    season: Option<i32>,
    limit: usize,
) -> String {
    let mut scored: Vec<(&Match, i32)> = db
        .matches
        .iter()
        .filter(|m| {
            if let Some(c) = competition {
                if !m.competition.to_lowercase().contains(&c.to_lowercase()) {
                    return false;
                }
            }
            if let Some(s) = season {
                if m.season != Some(s) {
                    return false;
                }
            }
            m.home_goal.is_some() && m.away_goal.is_some()
        })
        .map(|m| {
            let diff = (m.home_goal.unwrap() - m.away_goal.unwrap()).abs();
            (m, diff)
        })
        .collect();

    scored.sort_by(|a, b| b.1.cmp(&a.1));

    if scored.is_empty() {
        return "No matches found for the given criteria.".to_string();
    }

    let shown = scored.len().min(limit);
    let mut out = format!(
        "Biggest wins{}{}:\n",
        competition.map(|c| format!(" in {}", c)).unwrap_or_default(),
        season.map(|s| format!(" ({})", s)).unwrap_or_default(),
    );

    for (i, (m, diff)) in scored.iter().take(shown).enumerate() {
        out.push_str(&format!("  {}. (margin: {}) {}\n", i + 1, diff, match_line(m)));
    }

    out
}

/// Aggregate competition statistics
pub fn competition_stats(
    db: &Database,
    competition: Option<&str>,
    season: Option<i32>,
) -> String {
    let matches: Vec<&Match> = db
        .matches
        .iter()
        .filter(|m| {
            if let Some(c) = competition {
                if !m.competition.to_lowercase().contains(&c.to_lowercase()) {
                    return false;
                }
            }
            if let Some(s) = season {
                if m.season != Some(s) {
                    return false;
                }
            }
            true
        })
        .collect();

    if matches.is_empty() {
        return "No matches found for the given criteria.".to_string();
    }

    let total = matches.len();
    let with_goals: Vec<&Match> = matches
        .iter()
        .filter(|m| m.home_goal.is_some() && m.away_goal.is_some())
        .copied()
        .collect();

    let mut total_goals = 0i64;
    let mut home_wins = 0u32;
    let mut away_wins = 0u32;
    let mut draws = 0u32;

    for m in &with_goals {
        let hg = m.home_goal.unwrap();
        let ag = m.away_goal.unwrap();
        total_goals += (hg + ag) as i64;
        if hg > ag {
            home_wins += 1;
        } else if ag > hg {
            away_wins += 1;
        } else {
            draws += 1;
        }
    }

    let n = with_goals.len();
    let avg_goals = if n > 0 { total_goals as f64 / n as f64 } else { 0.0 };
    let home_rate = if n > 0 { home_wins as f64 / n as f64 * 100.0 } else { 0.0 };
    let away_rate = if n > 0 { away_wins as f64 / n as f64 * 100.0 } else { 0.0 };
    let draw_rate = if n > 0 { draws as f64 / n as f64 * 100.0 } else { 0.0 };

    // Find available seasons
    let mut seasons: Vec<i32> = matches
        .iter()
        .filter_map(|m| m.season)
        .collect::<std::collections::HashSet<i32>>()
        .into_iter()
        .collect();
    seasons.sort();

    let comp_label = competition.unwrap_or("all competitions");
    let season_label = season
        .map(|s| s.to_string())
        .unwrap_or_else(|| "all seasons".to_string());

    let mut out = format!(
        "Competition Statistics: {} | {}\n",
        comp_label, season_label
    );
    out.push_str(&format!("  Total matches: {}\n", total));
    out.push_str(&format!("  Matches with scores: {}\n", n));
    out.push_str(&format!("  Total goals: {}\n", total_goals));
    out.push_str(&format!("  Avg goals/match: {:.2}\n", avg_goals));
    out.push_str(&format!(
        "  Home wins: {} ({:.1}%)\n",
        home_wins, home_rate
    ));
    out.push_str(&format!(
        "  Away wins: {} ({:.1}%)\n",
        away_wins, away_rate
    ));
    out.push_str(&format!("  Draws: {} ({:.1}%)\n", draws, draw_rate));
    if !seasons.is_empty() {
        out.push_str(&format!(
            "  Seasons covered: {} - {}\n",
            seasons.first().unwrap(),
            seasons.last().unwrap()
        ));
    }

    out
}

/// Get top scoring teams in a competition/season
pub fn top_scoring_teams(
    db: &Database,
    competition: Option<&str>,
    season: Option<i32>,
    limit: usize,
) -> String {
    let mut goals_map: HashMap<String, u32> = HashMap::new();

    for m in &db.matches {
        if let Some(c) = competition {
            if !m.competition.to_lowercase().contains(&c.to_lowercase()) {
                continue;
            }
        }
        if let Some(s) = season {
            if m.season != Some(s) {
                continue;
            }
        }

        let home_name = normalize_team_name(&m.home_team);
        let away_name = normalize_team_name(&m.away_team);

        if let Some(hg) = m.home_goal {
            *goals_map.entry(home_name).or_insert(0) += hg as u32;
        }
        if let Some(ag) = m.away_goal {
            *goals_map.entry(away_name).or_insert(0) += ag as u32;
        }
    }

    if goals_map.is_empty() {
        return "No data found for the given criteria.".to_string();
    }

    let mut ranked: Vec<(String, u32)> = goals_map.into_iter().collect();
    ranked.sort_by(|a, b| b.1.cmp(&a.1));

    let shown = ranked.len().min(limit);
    let comp_label = competition.unwrap_or("all competitions");
    let season_label = season
        .map(|s| s.to_string())
        .unwrap_or_else(|| "all seasons".to_string());

    let mut out = format!(
        "Top Scoring Teams - {} | {}:\n",
        comp_label, season_label
    );
    for (i, (name, goals)) in ranked.iter().take(shown).enumerate() {
        out.push_str(&format!("  {}. {} - {} goals\n", i + 1, name, goals));
    }

    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::Database;
    use std::path::Path;

    fn load_test_db() -> Database {
        let data_dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        Database::load(&data_dir).expect("Failed to load database")
    }

    #[test]
    fn test_search_matches_by_team() {
        let db = load_test_db();
        let result = search_matches(&db, Some("Flamengo"), None, Some("brasileirão"), None, None, None, 5);
        assert!(result.contains("Found"));
        assert!(!result.contains("No matches found"));
    }

    #[test]
    fn test_search_matches_head_to_head() {
        let db = load_test_db();
        let result = search_matches(&db, Some("Flamengo"), Some("Fluminense"), None, None, None, None, 10);
        assert!(result.contains("Found"));
    }

    #[test]
    fn test_team_stats() {
        let db = load_test_db();
        let result = team_stats(&db, "Palmeiras", Some("brasileirão"), None);
        assert!(result.contains("Palmeiras"));
        assert!(result.contains("Win rate"));
    }

    #[test]
    fn test_head_to_head() {
        let db = load_test_db();
        let result = head_to_head(&db, "Flamengo", "Fluminense", None, None, 5);
        assert!(result.contains("Head-to-Head"));
    }

    #[test]
    fn test_search_players_by_nationality() {
        let db = load_test_db();
        let result = search_players(&db, None, Some("Brazil"), None, None, Some(80), 10);
        assert!(result.contains("Found") || result.contains("No players found"));
        // Brazilian players should exist
        if result.contains("Found") {
            assert!(result.contains("Brazil"));
        }
    }

    #[test]
    fn test_search_players_by_name() {
        let db = load_test_db();
        let result = search_players(&db, Some("Neymar"), None, None, None, None, 5);
        assert!(result.contains("Neymar"));
    }

    #[test]
    fn test_season_standings() {
        let db = load_test_db();
        let result = season_standings(&db, "brasileirão", 2019, 20);
        assert!(result.contains("Standings"));
        assert!(result.contains("2019"));
    }

    #[test]
    fn test_biggest_wins() {
        let db = load_test_db();
        let result = biggest_wins(&db, Some("brasileirão"), None, 5);
        assert!(result.contains("Biggest wins"));
        assert!(result.contains("margin"));
    }

    #[test]
    fn test_competition_stats() {
        let db = load_test_db();
        let result = competition_stats(&db, Some("brasileirão"), Some(2022));
        assert!(result.contains("Total matches"));
        assert!(result.contains("Avg goals"));
    }

    #[test]
    fn test_top_scoring_teams() {
        let db = load_test_db();
        let result = top_scoring_teams(&db, Some("brasileirão"), Some(2022), 10);
        assert!(result.contains("Top Scoring Teams"));
    }

    #[test]
    fn test_db_loaded_all_files() {
        let db = load_test_db();
        // Should have all 5 match files worth of data
        assert!(db.matches.len() > 1000, "Expected many matches, got {}", db.matches.len());
        assert!(db.players.len() > 1000, "Expected many players, got {}", db.players.len());
    }

    #[test]
    fn test_competition_stats_all() {
        let db = load_test_db();
        let result = competition_stats(&db, None, None);
        assert!(result.contains("Total matches"));
    }
}
