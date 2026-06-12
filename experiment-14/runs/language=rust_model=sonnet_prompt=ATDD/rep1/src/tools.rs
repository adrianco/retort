use crate::data::{AppData, Match};
use crate::normalize::{normalize_team_name, teams_match};
use std::collections::HashMap;

/// find_matches: Find matches for a team, optionally filtered by team2, competition, season, limit
pub fn find_matches(data: &AppData, args: &serde_json::Value) -> String {
    let team = args["team"].as_str().unwrap_or("").trim().to_string();
    let team2 = args["team2"].as_str().unwrap_or("").trim().to_string();
    let competition = args["competition"]
        .as_str()
        .unwrap_or("")
        .trim()
        .to_lowercase();
    let season = args["season"].as_i64().unwrap_or(0) as i32;
    let limit = args["limit"].as_u64().unwrap_or(20) as usize;

    let filtered: Vec<&Match> = data
        .matches
        .iter()
        .filter(|m| {
            // Team filter
            if !team.is_empty() {
                let involves_team =
                    teams_match(&m.home_team, &team) || teams_match(&m.away_team, &team);
                if !involves_team {
                    return false;
                }
            }
            // Team2 filter (for head-to-head within find_matches)
            if !team2.is_empty() {
                let involves_team2 =
                    teams_match(&m.home_team, &team2) || teams_match(&m.away_team, &team2);
                if !involves_team2 {
                    return false;
                }
            }
            // Competition filter
            if !competition.is_empty() {
                let comp_match = match competition.as_str() {
                    "brasileirao" | "serie a" | "serie_a" => {
                        m.competition == "brasileirao"
                    }
                    "copa" | "copa_brasil" | "copa do brasil" => {
                        m.competition == "copa_brasil"
                    }
                    "libertadores" => m.competition == "libertadores",
                    _ => m.competition.contains(&competition),
                };
                if !comp_match {
                    return false;
                }
            }
            // Season filter
            if season != 0 && m.season != season {
                return false;
            }
            true
        })
        .collect();

    if filtered.is_empty() {
        return format!(
            "No matches found{}{}{}{}.",
            if !team.is_empty() {
                format!(" for {}", team)
            } else {
                String::new()
            },
            if !team2.is_empty() {
                format!(" vs {}", team2)
            } else {
                String::new()
            },
            if !competition.is_empty() {
                format!(" in {}", competition)
            } else {
                String::new()
            },
            if season != 0 {
                format!(" season {}", season)
            } else {
                String::new()
            }
        );
    }

    let total = filtered.len();
    let shown: Vec<&Match> = filtered.into_iter().take(limit).collect();

    let mut out = String::new();
    out.push_str(&format!(
        "Found {} matches (showing {}):\n\n",
        total,
        shown.len()
    ));

    for m in &shown {
        let home_norm = normalize_team_name(&m.home_team);
        let away_norm = normalize_team_name(&m.away_team);
        let result_str = format!("{} - {}", m.home_goal, m.away_goal);
        out.push_str(&format!(
            "{} | {} {} {} | {} | Season {}\n",
            m.datetime.get(..10).unwrap_or(&m.datetime),
            home_norm,
            result_str,
            away_norm,
            m.competition,
            m.season
        ));
    }

    out
}

/// get_team_stats: Stats for a team in a competition/season
pub fn get_team_stats(data: &AppData, args: &serde_json::Value) -> String {
    let team = args["team"].as_str().unwrap_or("").trim().to_string();
    if team.is_empty() {
        return "Error: 'team' parameter is required.".to_string();
    }
    let competition = args["competition"]
        .as_str()
        .unwrap_or("")
        .trim()
        .to_lowercase();
    let season = args["season"].as_i64().unwrap_or(0) as i32;

    let team_matches: Vec<&Match> = data
        .matches
        .iter()
        .filter(|m| {
            let involves = teams_match(&m.home_team, &team) || teams_match(&m.away_team, &team);
            if !involves {
                return false;
            }
            if !competition.is_empty() {
                let comp_match = match competition.as_str() {
                    "brasileirao" | "serie a" | "serie_a" => {
                        m.competition == "brasileirao"
                    }
                    "copa" | "copa_brasil" | "copa do brasil" => {
                        m.competition == "copa_brasil"
                    }
                    "libertadores" => m.competition == "libertadores",
                    _ => m.competition.contains(&competition),
                };
                if !comp_match {
                    return false;
                }
            }
            if season != 0 && m.season != season {
                return false;
            }
            true
        })
        .collect();

    if team_matches.is_empty() {
        return format!(
            "No matches found for {}{}{}.",
            team,
            if !competition.is_empty() {
                format!(" in {}", competition)
            } else {
                String::new()
            },
            if season != 0 {
                format!(" season {}", season)
            } else {
                String::new()
            }
        );
    }

    let mut wins = 0i32;
    let mut draws = 0i32;
    let mut losses = 0i32;
    let mut goals_for = 0i32;
    let mut goals_against = 0i32;

    for m in &team_matches {
        let is_home = teams_match(&m.home_team, &team);
        let (gf, ga) = if is_home {
            (m.home_goal, m.away_goal)
        } else {
            (m.away_goal, m.home_goal)
        };
        goals_for += gf;
        goals_against += ga;
        if gf > ga {
            wins += 1;
        } else if gf == ga {
            draws += 1;
        } else {
            losses += 1;
        }
    }

    let played = team_matches.len() as i32;
    let points = wins * 3 + draws;
    let goal_diff = goals_for - goals_against;

    let mut out = String::new();
    out.push_str(&format!("Stats for {}", team));
    if !competition.is_empty() {
        out.push_str(&format!(" | {}", competition));
    }
    if season != 0 {
        out.push_str(&format!(" | Season {}", season));
    }
    out.push('\n');
    out.push_str(&format!(
        "Played: {} | Wins: {} | Draws: {} | Losses: {}\n",
        played, wins, draws, losses
    ));
    out.push_str(&format!(
        "Points: {} | Goals For: {} | Goals Against: {} | Goal Diff: {:+}\n",
        points, goals_for, goals_against, goal_diff
    ));
    out.push_str(&format!(
        "Win Rate: {:.1}%\n",
        if played > 0 {
            (wins as f64 / played as f64) * 100.0
        } else {
            0.0
        }
    ));

    out
}

/// find_players: Find players by name, nationality, club, position, min_rating, max_age
pub fn find_players(data: &AppData, args: &serde_json::Value) -> String {
    let name_filter = args["name"]
        .as_str()
        .unwrap_or("")
        .to_lowercase();
    let nationality = args["nationality"]
        .as_str()
        .unwrap_or("")
        .to_lowercase();
    let club = args["club"].as_str().unwrap_or("").to_lowercase();
    let position = args["position"].as_str().unwrap_or("").to_lowercase();
    let min_rating = args["min_rating"].as_u64().unwrap_or(0) as u32;
    let max_age = args["max_age"].as_u64().unwrap_or(u64::MAX) as u32;
    let limit = args["limit"].as_u64().unwrap_or(20) as usize;

    if data.players.is_empty() {
        return "No player data loaded.".to_string();
    }

    let filtered: Vec<_> = data
        .players
        .iter()
        .filter(|p| {
            if !name_filter.is_empty() && !p.name.to_lowercase().contains(&name_filter) {
                return false;
            }
            if !nationality.is_empty() && !p.nationality.to_lowercase().contains(&nationality) {
                return false;
            }
            if !club.is_empty() && !p.club.to_lowercase().contains(&club) {
                return false;
            }
            if !position.is_empty() && !p.position.to_lowercase().contains(&position) {
                return false;
            }
            if min_rating > 0 && p.overall < min_rating {
                return false;
            }
            if max_age < u32::MAX && p.age > max_age {
                return false;
            }
            true
        })
        .collect();

    if filtered.is_empty() {
        return format!(
            "No players found matching the criteria{}{}{}{}{}.",
            if !name_filter.is_empty() {
                format!(" name:{}", name_filter)
            } else {
                String::new()
            },
            if !nationality.is_empty() {
                format!(" nationality:{}", nationality)
            } else {
                String::new()
            },
            if !club.is_empty() {
                format!(" club:{}", club)
            } else {
                String::new()
            },
            if min_rating > 0 {
                format!(" min_rating:{}", min_rating)
            } else {
                String::new()
            },
            if max_age < u32::MAX {
                format!(" max_age:{}", max_age)
            } else {
                String::new()
            }
        );
    }

    // Sort by overall rating descending
    let mut sorted = filtered.clone();
    sorted.sort_by(|a, b| b.overall.cmp(&a.overall).then(a.name.cmp(&b.name)));

    let total = sorted.len();
    let shown: Vec<_> = sorted.into_iter().take(limit).collect();

    let mut out = String::new();
    out.push_str(&format!(
        "Found {} players (showing {}):\n\n",
        total,
        shown.len()
    ));
    out.push_str(&format!(
        "{:<25} {:>4} {:>5} {:>3} {:>6} {:<20} {:<10}\n",
        "Name", "Age", "OVR", "POT", "Value", "Club", "Position"
    ));
    out.push_str(&"-".repeat(80));
    out.push('\n');

    for p in &shown {
        out.push_str(&format!(
            "{:<25} {:>4} {:>5} {:>3} {:>6} {:<20} {:<10}\n",
            truncate(&p.name, 25),
            p.age,
            p.overall,
            p.potential,
            truncate(&p.value, 6),
            truncate(&p.club, 20),
            truncate(&p.position, 10)
        ));
    }

    out
}

fn truncate(s: &str, max: usize) -> &str {
    if s.len() <= max {
        s
    } else {
        &s[..max]
    }
}

/// get_head_to_head: H2H record between two teams
pub fn get_head_to_head(data: &AppData, args: &serde_json::Value) -> String {
    let team1 = args["team1"].as_str().unwrap_or("").trim().to_string();
    let team2 = args["team2"].as_str().unwrap_or("").trim().to_string();
    if team1.is_empty() || team2.is_empty() {
        return "Error: 'team1' and 'team2' parameters are required.".to_string();
    }
    let competition = args["competition"]
        .as_str()
        .unwrap_or("")
        .trim()
        .to_lowercase();
    let season = args["season"].as_i64().unwrap_or(0) as i32;
    let limit = args["limit"].as_u64().unwrap_or(10) as usize;

    let h2h: Vec<&Match> = data
        .matches
        .iter()
        .filter(|m| {
            let t1_home = teams_match(&m.home_team, &team1);
            let t1_away = teams_match(&m.away_team, &team1);
            let t2_home = teams_match(&m.home_team, &team2);
            let t2_away = teams_match(&m.away_team, &team2);

            let valid = (t1_home && t2_away) || (t1_away && t2_home);
            if !valid {
                return false;
            }
            if !competition.is_empty() {
                let comp_match = match competition.as_str() {
                    "brasileirao" | "serie a" | "serie_a" => {
                        m.competition == "brasileirao"
                    }
                    "copa" | "copa_brasil" => m.competition == "copa_brasil",
                    "libertadores" => m.competition == "libertadores",
                    _ => m.competition.contains(&competition),
                };
                if !comp_match {
                    return false;
                }
            }
            if season != 0 && m.season != season {
                return false;
            }
            true
        })
        .collect();

    if h2h.is_empty() {
        return format!(
            "No head-to-head matches found between {} and {}.",
            team1, team2
        );
    }

    let mut t1_wins = 0i32;
    let mut t2_wins = 0i32;
    let mut draws = 0i32;
    let mut t1_goals = 0i32;
    let mut t2_goals = 0i32;

    for m in &h2h {
        let t1_is_home = teams_match(&m.home_team, &team1);
        let (g1, g2) = if t1_is_home {
            (m.home_goal, m.away_goal)
        } else {
            (m.away_goal, m.home_goal)
        };
        t1_goals += g1;
        t2_goals += g2;
        if g1 > g2 {
            t1_wins += 1;
        } else if g1 == g2 {
            draws += 1;
        } else {
            t2_wins += 1;
        }
    }

    let mut out = String::new();
    out.push_str(&format!("Head-to-Head: {} vs {}\n", team1, team2));
    if !competition.is_empty() {
        out.push_str(&format!("Competition: {}\n", competition));
    }
    out.push_str(&format!("Total matches: {}\n", h2h.len()));
    out.push_str(&format!(
        "{} wins: {} | Draws: {} | {} wins: {}\n",
        team1, t1_wins, draws, team2, t2_wins
    ));
    out.push_str(&format!(
        "Goals: {} {} - {} {}\n\n",
        team1, t1_goals, t2_goals, team2
    ));

    // Show recent matches
    let recent: Vec<_> = h2h.iter().rev().take(limit).collect();
    out.push_str(&format!("Last {} matches:\n", recent.len()));
    for m in recent {
        let home_norm = normalize_team_name(&m.home_team);
        let away_norm = normalize_team_name(&m.away_team);
        out.push_str(&format!(
            "  {} | {} {}-{} {} | {} | {}\n",
            m.datetime.get(..10).unwrap_or(&m.datetime),
            home_norm,
            m.home_goal,
            m.away_goal,
            away_norm,
            m.competition,
            m.season
        ));
    }

    out
}

/// get_standings: Compute standings for a competition/season
pub fn get_standings(data: &AppData, args: &serde_json::Value) -> String {
    let competition = args["competition"]
        .as_str()
        .unwrap_or("brasileirao")
        .trim()
        .to_lowercase();
    let season = args["season"].as_i64().unwrap_or(0) as i32;
    let limit = args["limit"].as_u64().unwrap_or(20) as usize;

    let comp_filter = match competition.as_str() {
        "brasileirao" | "serie a" | "serie_a" => "brasileirao",
        "copa" | "copa_brasil" | "copa do brasil" => "copa_brasil",
        "libertadores" => "libertadores",
        _ => &competition,
    };

    let filtered: Vec<&Match> = data
        .matches
        .iter()
        .filter(|m| {
            let comp_ok = m.competition == comp_filter
                || (comp_filter == "brasileirao" && m.competition == "brasileirao");
            if !comp_ok {
                return false;
            }
            if season != 0 && m.season != season {
                return false;
            }
            true
        })
        .collect();

    if filtered.is_empty() {
        return format!(
            "No matches found for {} {}.",
            competition,
            if season != 0 {
                season.to_string()
            } else {
                "all seasons".to_string()
            }
        );
    }

    // Build standings
    let mut table: HashMap<String, TeamRecord> = HashMap::new();

    for m in &filtered {
        let home = normalize_team_name(&m.home_team);
        let away = normalize_team_name(&m.away_team);

        let home_entry = table.entry(home.clone()).or_insert_with(TeamRecord::new);
        home_entry.played += 1;
        home_entry.goals_for += m.home_goal;
        home_entry.goals_against += m.away_goal;
        if m.home_goal > m.away_goal {
            home_entry.wins += 1;
        } else if m.home_goal == m.away_goal {
            home_entry.draws += 1;
        } else {
            home_entry.losses += 1;
        }

        let away_entry = table.entry(away.clone()).or_insert_with(TeamRecord::new);
        away_entry.played += 1;
        away_entry.goals_for += m.away_goal;
        away_entry.goals_against += m.home_goal;
        if m.away_goal > m.home_goal {
            away_entry.wins += 1;
        } else if m.away_goal == m.home_goal {
            away_entry.draws += 1;
        } else {
            away_entry.losses += 1;
        }
    }

    // Sort by points, then goal_diff, then goals_for
    let mut standings: Vec<(String, TeamRecord)> = table.into_iter().collect();
    standings.sort_by(|(_, a), (_, b)| {
        let pa = a.wins * 3 + a.draws;
        let pb = b.wins * 3 + b.draws;
        let gda = a.goals_for - a.goals_against;
        let gdb = b.goals_for - b.goals_against;
        pb.cmp(&pa)
            .then(gdb.cmp(&gda))
            .then(b.goals_for.cmp(&a.goals_for))
    });

    let total_teams = standings.len();
    let shown: Vec<_> = standings.into_iter().take(limit).collect();

    let mut out = String::new();
    let season_str = if season != 0 {
        season.to_string()
    } else {
        "All Seasons".to_string()
    };
    out.push_str(&format!(
        "Standings: {} | Season: {}\n",
        competition, season_str
    ));
    out.push_str(&format!("Total teams: {}\n\n", total_teams));
    out.push_str(&format!(
        "{:>3} {:<22} {:>4} {:>4} {:>4} {:>4} {:>4} {:>4} {:>4}\n",
        "#", "Team", "P", "W", "D", "L", "GF", "GA", "Pts"
    ));
    out.push_str(&"-".repeat(60));
    out.push('\n');

    for (i, (team, rec)) in shown.iter().enumerate() {
        let pts = rec.wins * 3 + rec.draws;
        out.push_str(&format!(
            "{:>3} {:<22} {:>4} {:>4} {:>4} {:>4} {:>4} {:>4} {:>4}\n",
            i + 1,
            truncate(team, 22),
            rec.played,
            rec.wins,
            rec.draws,
            rec.losses,
            rec.goals_for,
            rec.goals_against,
            pts
        ));
    }

    out
}

#[derive(Debug, Default)]
struct TeamRecord {
    played: i32,
    wins: i32,
    draws: i32,
    losses: i32,
    goals_for: i32,
    goals_against: i32,
}

impl TeamRecord {
    fn new() -> Self {
        Self::default()
    }
}

/// get_statistical_summary: Overall stats for a competition
pub fn get_statistical_summary(data: &AppData, args: &serde_json::Value) -> String {
    let competition = args["competition"]
        .as_str()
        .unwrap_or("")
        .trim()
        .to_lowercase();
    let season = args["season"].as_i64().unwrap_or(0) as i32;

    let comp_filter: &str = match competition.as_str() {
        "brasileirao" | "serie a" | "serie_a" => "brasileirao",
        "copa" | "copa_brasil" | "copa do brasil" => "copa_brasil",
        "libertadores" => "libertadores",
        "" => "",
        _ => &competition,
    };

    let filtered: Vec<&Match> = data
        .matches
        .iter()
        .filter(|m| {
            if !comp_filter.is_empty() && m.competition != comp_filter {
                return false;
            }
            if season != 0 && m.season != season {
                return false;
            }
            true
        })
        .collect();

    if filtered.is_empty() {
        return format!("No matches found for {}.", competition);
    }

    let total_matches = filtered.len();
    let total_goals: i32 = filtered.iter().map(|m| m.home_goal + m.away_goal).sum();
    let home_wins = filtered
        .iter()
        .filter(|m| m.home_goal > m.away_goal)
        .count();
    let draws = filtered
        .iter()
        .filter(|m| m.home_goal == m.away_goal)
        .count();
    let away_wins = filtered
        .iter()
        .filter(|m| m.away_goal > m.home_goal)
        .count();

    let avg_goals = if total_matches > 0 {
        total_goals as f64 / total_matches as f64
    } else {
        0.0
    };

    // Season breakdown
    let mut seasons: Vec<i32> = filtered.iter().map(|m| m.season).collect();
    seasons.sort();
    seasons.dedup();

    let max_score = filtered.iter().max_by_key(|m| m.home_goal + m.away_goal);

    let mut out = String::new();
    out.push_str(&format!(
        "Statistical Summary: {}\n",
        if competition.is_empty() {
            "All Competitions"
        } else {
            &competition
        }
    ));
    if season != 0 {
        out.push_str(&format!("Season: {}\n", season));
    }
    out.push('\n');
    out.push_str(&format!("Total matches: {}\n", total_matches));
    out.push_str(&format!("Total goals: {}\n", total_goals));
    out.push_str(&format!("Average goals per match: {:.2}\n", avg_goals));
    out.push_str(&format!(
        "Home wins: {} ({:.1}%)\n",
        home_wins,
        if total_matches > 0 {
            home_wins as f64 / total_matches as f64 * 100.0
        } else {
            0.0
        }
    ));
    out.push_str(&format!(
        "Draws: {} ({:.1}%)\n",
        draws,
        if total_matches > 0 {
            draws as f64 / total_matches as f64 * 100.0
        } else {
            0.0
        }
    ));
    out.push_str(&format!(
        "Away wins: {} ({:.1}%)\n",
        away_wins,
        if total_matches > 0 {
            away_wins as f64 / total_matches as f64 * 100.0
        } else {
            0.0
        }
    ));

    if !seasons.is_empty() {
        out.push_str(&format!(
            "Seasons covered: {} to {}\n",
            seasons.first().unwrap(),
            seasons.last().unwrap()
        ));
    }

    if let Some(m) = max_score {
        out.push_str(&format!(
            "Highest scoring: {} {}-{} {} ({})\n",
            normalize_team_name(&m.home_team),
            m.home_goal,
            m.away_goal,
            normalize_team_name(&m.away_team),
            m.season
        ));
    }

    out
}
