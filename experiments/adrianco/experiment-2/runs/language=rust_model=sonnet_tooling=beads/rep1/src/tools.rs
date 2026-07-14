use crate::data::{DataStore, team_matches_query};

pub struct Tools<'a> {
    pub store: &'a DataStore,
}

impl<'a> Tools<'a> {
    pub fn new(store: &'a DataStore) -> Self {
        Tools { store }
    }

    /// Search for matches by team, season, competition.
    pub fn search_matches(&self, args: &serde_json::Value) -> String {
        let team1 = args["team1"].as_str().unwrap_or("");
        let team2 = args["team2"].as_str().unwrap_or("");
        let season = args["season"].as_i64();
        let competition = args["competition"].as_str().unwrap_or("");
        let limit = args["limit"].as_i64().unwrap_or(20) as usize;

        if team1.is_empty() {
            return "Error: team1 is required".to_string();
        }

        let mut results: Vec<&crate::data::Match> = self
            .store
            .matches
            .iter()
            .filter(|m| {
                // team1 must be home or away
                let t1_matches = team_matches_query(&m.home_team, team1)
                    || team_matches_query(&m.away_team, team1);
                if !t1_matches {
                    return false;
                }
                // team2 if specified
                if !team2.is_empty() {
                    let t2_matches = team_matches_query(&m.home_team, team2)
                        || team_matches_query(&m.away_team, team2);
                    if !t2_matches {
                        return false;
                    }
                }
                // season filter
                if let Some(s) = season {
                    if m.season != s as i32 {
                        return false;
                    }
                }
                // competition filter
                if !competition.is_empty() {
                    if !m.competition.to_lowercase().contains(&competition.to_lowercase()) {
                        return false;
                    }
                }
                true
            })
            .collect();

        // Sort by date descending
        results.sort_by(|a, b| b.date.cmp(&a.date));

        let total = results.len();
        let showing = total.min(limit);

        let mut out = String::new();
        out.push_str(&format!(
            "Found {} matches, showing {}:\n\n",
            total, showing
        ));

        for m in results.iter().take(limit) {
            let extra = match (&m.round, &m.stage) {
                (Some(r), _) => format!(" | Round {}", r),
                (_, Some(s)) => format!(" | Stage: {}", s),
                _ => String::new(),
            };
            out.push_str(&format!(
                "{} | {} {}-{} {} ({}{} {})\n",
                m.date,
                m.home_team,
                m.home_goals,
                m.away_goals,
                m.away_team,
                m.competition,
                extra,
                m.season
            ));
        }

        // Head-to-head summary when 2 teams
        if !team2.is_empty() {
            let mut t1_wins = 0i32;
            let mut t2_wins = 0i32;
            let mut draws = 0i32;
            let mut t1_goals = 0i32;
            let mut t2_goals = 0i32;

            for m in &results {
                let t1_home = team_matches_query(&m.home_team, team1);
                let t1_away = team_matches_query(&m.away_team, team1);
                if t1_home {
                    t1_goals += m.home_goals;
                    t2_goals += m.away_goals;
                    if m.home_goals > m.away_goals {
                        t1_wins += 1;
                    } else if m.home_goals < m.away_goals {
                        t2_wins += 1;
                    } else {
                        draws += 1;
                    }
                } else if t1_away {
                    t1_goals += m.away_goals;
                    t2_goals += m.home_goals;
                    if m.away_goals > m.home_goals {
                        t1_wins += 1;
                    } else if m.away_goals < m.home_goals {
                        t2_wins += 1;
                    } else {
                        draws += 1;
                    }
                }
            }

            out.push_str(&format!(
                "\nHead-to-Head Summary:\n{} wins: {} | Draws: {} | {} wins: {}\nGoals: {} - {}\n",
                team1, t1_wins, draws, team2, t2_wins, t1_goals, t2_goals
            ));
        }

        out
    }

    /// Get statistics for a team.
    pub fn get_team_stats(&self, args: &serde_json::Value) -> String {
        let team = args["team"].as_str().unwrap_or("");
        let season = args["season"].as_i64();
        let competition = args["competition"].as_str().unwrap_or("");

        if team.is_empty() {
            return "Error: team is required".to_string();
        }

        let matches: Vec<&crate::data::Match> = self
            .store
            .matches
            .iter()
            .filter(|m| {
                let in_match = team_matches_query(&m.home_team, team)
                    || team_matches_query(&m.away_team, team);
                if !in_match {
                    return false;
                }
                if let Some(s) = season {
                    if m.season != s as i32 {
                        return false;
                    }
                }
                if !competition.is_empty() {
                    if !m.competition.to_lowercase().contains(&competition.to_lowercase()) {
                        return false;
                    }
                }
                true
            })
            .collect();

        if matches.is_empty() {
            return format!("No matches found for team '{}'", team);
        }

        let mut played = 0;
        let mut wins = 0;
        let mut draws = 0;
        let mut losses = 0;
        let mut goals_for = 0i32;
        let mut goals_against = 0i32;
        let mut home_wins = 0;
        let mut home_draws = 0;
        let mut home_losses = 0;
        let mut away_wins = 0;
        let mut away_draws = 0;
        let mut away_losses = 0;

        for m in &matches {
            let is_home = team_matches_query(&m.home_team, team);
            played += 1;
            if is_home {
                goals_for += m.home_goals;
                goals_against += m.away_goals;
                if m.home_goals > m.away_goals {
                    wins += 1;
                    home_wins += 1;
                } else if m.home_goals == m.away_goals {
                    draws += 1;
                    home_draws += 1;
                } else {
                    losses += 1;
                    home_losses += 1;
                }
            } else {
                goals_for += m.away_goals;
                goals_against += m.home_goals;
                if m.away_goals > m.home_goals {
                    wins += 1;
                    away_wins += 1;
                } else if m.away_goals == m.home_goals {
                    draws += 1;
                    away_draws += 1;
                } else {
                    losses += 1;
                    away_losses += 1;
                }
            }
        }

        let points = wins * 3 + draws;
        let gd = goals_for - goals_against;

        let filter_desc = {
            let mut parts = Vec::new();
            if let Some(s) = season {
                parts.push(format!("Season: {}", s));
            }
            if !competition.is_empty() {
                parts.push(format!("Competition: {}", competition));
            }
            if parts.is_empty() {
                "All competitions, all seasons".to_string()
            } else {
                parts.join(", ")
            }
        };

        format!(
            "Stats for {} ({})\n\
            Matches: {} | W: {} D: {} L: {} | Points: {}\n\
            Goals For: {} | Goals Against: {} | Goal Difference: {}\n\
            Home Record: {}W {}D {}L\n\
            Away Record: {}W {}D {}L\n",
            team,
            filter_desc,
            played,
            wins,
            draws,
            losses,
            points,
            goals_for,
            goals_against,
            gd,
            home_wins,
            home_draws,
            home_losses,
            away_wins,
            away_draws,
            away_losses
        )
    }

    /// Compare two teams head-to-head.
    pub fn head_to_head(&self, args: &serde_json::Value) -> String {
        let team1 = args["team1"].as_str().unwrap_or("");
        let team2 = args["team2"].as_str().unwrap_or("");
        let competition = args["competition"].as_str().unwrap_or("");

        if team1.is_empty() || team2.is_empty() {
            return "Error: team1 and team2 are required".to_string();
        }

        let mut results: Vec<&crate::data::Match> = self
            .store
            .matches
            .iter()
            .filter(|m| {
                let t1_home = team_matches_query(&m.home_team, team1);
                let t1_away = team_matches_query(&m.away_team, team1);
                let t2_home = team_matches_query(&m.home_team, team2);
                let t2_away = team_matches_query(&m.away_team, team2);

                let valid = (t1_home && t2_away) || (t1_away && t2_home);
                if !valid {
                    return false;
                }
                if !competition.is_empty() {
                    if !m.competition.to_lowercase().contains(&competition.to_lowercase()) {
                        return false;
                    }
                }
                true
            })
            .collect();

        results.sort_by(|a, b| b.date.cmp(&a.date));

        let total = results.len();
        if total == 0 {
            return format!("No matches found between {} and {}", team1, team2);
        }

        let mut t1_wins = 0i32;
        let mut t2_wins = 0i32;
        let mut draws = 0i32;
        let mut t1_goals = 0i32;
        let mut t2_goals = 0i32;

        for m in &results {
            let t1_home = team_matches_query(&m.home_team, team1);
            if t1_home {
                t1_goals += m.home_goals;
                t2_goals += m.away_goals;
                if m.home_goals > m.away_goals {
                    t1_wins += 1;
                } else if m.home_goals < m.away_goals {
                    t2_wins += 1;
                } else {
                    draws += 1;
                }
            } else {
                t1_goals += m.away_goals;
                t2_goals += m.home_goals;
                if m.away_goals > m.home_goals {
                    t1_wins += 1;
                } else if m.away_goals < m.home_goals {
                    t2_wins += 1;
                } else {
                    draws += 1;
                }
            }
        }

        let mut out = String::new();
        out.push_str(&format!(
            "Head-to-Head: {} vs {}\n\
            Total Matches: {}\n\
            {} wins: {} | Draws: {} | {} wins: {}\n\
            Goals: {} {} - {} {}\n\n\
            Last {} matches:\n",
            team1,
            team2,
            total,
            team1,
            t1_wins,
            draws,
            team2,
            t2_wins,
            team1,
            t1_goals,
            t2_goals,
            team2,
            total.min(10)
        ));

        for m in results.iter().take(10) {
            let extra = match (&m.round, &m.stage) {
                (Some(r), _) => format!(" Round {}", r),
                (_, Some(s)) => format!(" {}", s),
                _ => String::new(),
            };
            out.push_str(&format!(
                "{} | {} {}-{} {} ({}{} {})\n",
                m.date,
                m.home_team,
                m.home_goals,
                m.away_goals,
                m.away_team,
                m.competition,
                extra,
                m.season
            ));
        }

        out
    }

    /// Search FIFA players.
    pub fn search_players(&self, args: &serde_json::Value) -> String {
        let name = args["name"].as_str().unwrap_or("");
        let nationality = args["nationality"].as_str().unwrap_or("");
        let club = args["club"].as_str().unwrap_or("");
        let position = args["position"].as_str().unwrap_or("");
        let min_overall = args["min_overall"].as_i64().unwrap_or(0) as i32;
        let limit = args["limit"].as_i64().unwrap_or(20) as usize;

        let mut results: Vec<&crate::data::Player> = self
            .store
            .players
            .iter()
            .filter(|p| {
                if !name.is_empty()
                    && !p.name.to_lowercase().contains(&name.to_lowercase())
                {
                    return false;
                }
                if !nationality.is_empty()
                    && p.nationality.to_lowercase() != nationality.to_lowercase()
                {
                    return false;
                }
                if !club.is_empty()
                    && !p.club.to_lowercase().contains(&club.to_lowercase())
                {
                    return false;
                }
                if !position.is_empty()
                    && p.position.to_lowercase() != position.to_lowercase()
                {
                    return false;
                }
                if p.overall < min_overall {
                    return false;
                }
                true
            })
            .collect();

        // Sort by overall descending
        results.sort_by(|a, b| b.overall.cmp(&a.overall));

        let total = results.len();
        let showing = total.min(limit);

        let mut out = format!("Found {} players, showing {}:\n\n", total, showing);

        for p in results.iter().take(limit) {
            let age_str = p
                .age
                .map(|a| a.to_string())
                .unwrap_or_else(|| "?".to_string());
            out.push_str(&format!(
                "{} | {} | Age: {} | {}/{} | Club: {} | Pos: {} | Value: {} | Wage: {}\n",
                p.name,
                p.nationality,
                age_str,
                p.overall,
                p.potential,
                p.club,
                p.position,
                p.value,
                p.wage
            ));
        }

        out
    }

    /// Calculate league standings for a season.
    pub fn get_standings(&self, args: &serde_json::Value) -> String {
        let season = match args["season"].as_i64() {
            Some(s) => s as i32,
            None => return "Error: season is required".to_string(),
        };
        let competition = args["competition"].as_str().unwrap_or("Brasileirão");

        // table: team -> (points, wins, draws, losses, gf, ga)
        let mut table: std::collections::HashMap<String, (i32, i32, i32, i32, i32, i32)> =
            std::collections::HashMap::new();

        let matches: Vec<&crate::data::Match> = self
            .store
            .matches
            .iter()
            .filter(|m| {
                m.season == season
                    && m.competition
                        .to_lowercase()
                        .contains(&competition.to_lowercase())
            })
            .collect();

        if matches.is_empty() {
            return format!(
                "No matches found for {} in season {}",
                competition, season
            );
        }

        for m in &matches {
            let home = crate::data::normalize_team(&m.home_team);
            let away = crate::data::normalize_team(&m.away_team);

            let he = table.entry(home.clone()).or_insert((0, 0, 0, 0, 0, 0));
            he.4 += m.home_goals;
            he.5 += m.away_goals;
            if m.home_goals > m.away_goals {
                he.0 += 3;
                he.1 += 1;
            } else if m.home_goals == m.away_goals {
                he.0 += 1;
                he.2 += 1;
            } else {
                he.3 += 1;
            }

            let ae = table.entry(away.clone()).or_insert((0, 0, 0, 0, 0, 0));
            ae.4 += m.away_goals;
            ae.5 += m.home_goals;
            if m.away_goals > m.home_goals {
                ae.0 += 3;
                ae.1 += 1;
            } else if m.away_goals == m.home_goals {
                ae.0 += 1;
                ae.2 += 1;
            } else {
                ae.3 += 1;
            }
        }

        let mut standings: Vec<(String, i32, i32, i32, i32, i32, i32)> = table
            .into_iter()
            .map(|(team, (pts, w, d, l, gf, ga))| (team, pts, w, d, l, gf, ga))
            .collect();

        // Sort by points desc, GD desc, GF desc
        standings.sort_by(|a, b| {
            let gd_a = a.5 - a.6;
            let gd_b = b.5 - b.6;
            b.1.cmp(&a.1)
                .then(gd_b.cmp(&gd_a))
                .then(b.5.cmp(&a.5))
                .then(a.0.cmp(&b.0))
        });

        let mut out = format!("{} {} Standings\n\n", competition, season);
        out.push_str(&format!(
            "{:<4} {:<25} {:>4} {:>3} {:>3} {:>3} {:>4} {:>4} {:>4}\n",
            "Pos", "Team", "Pts", "W", "D", "L", "GF", "GA", "GD"
        ));
        out.push_str(&"-".repeat(60));
        out.push('\n');

        for (i, (team, pts, w, d, l, gf, ga)) in standings.iter().enumerate() {
            let gd = gf - ga;
            let gd_str = if gd >= 0 {
                format!("+{}", gd)
            } else {
                gd.to_string()
            };
            out.push_str(&format!(
                "{:<4} {:<25} {:>4} {:>3} {:>3} {:>3} {:>4} {:>4} {:>4}\n",
                i + 1,
                team,
                pts,
                w,
                d,
                l,
                gf,
                ga,
                gd_str
            ));
        }

        out
    }

    /// Find matches with biggest goal differences.
    pub fn get_biggest_wins(&self, args: &serde_json::Value) -> String {
        let competition = args["competition"].as_str().unwrap_or("");
        let season = args["season"].as_i64();
        let limit = args["limit"].as_i64().unwrap_or(10) as usize;

        let mut results: Vec<&crate::data::Match> = self
            .store
            .matches
            .iter()
            .filter(|m| {
                if !competition.is_empty() {
                    if !m.competition.to_lowercase().contains(&competition.to_lowercase()) {
                        return false;
                    }
                }
                if let Some(s) = season {
                    if m.season != s as i32 {
                        return false;
                    }
                }
                true
            })
            .collect();

        results.sort_by(|a, b| {
            let diff_a = (a.home_goals - a.away_goals).abs();
            let diff_b = (b.home_goals - b.away_goals).abs();
            diff_b.cmp(&diff_a).then(b.date.cmp(&a.date))
        });

        let total = results.len();
        let showing = total.min(limit);

        let mut out = format!("Biggest wins (showing {} of {}):\n\n", showing, total);

        for m in results.iter().take(limit) {
            let diff = (m.home_goals - m.away_goals).abs();
            let extra = match (&m.round, &m.stage) {
                (Some(r), _) => format!(" Round {}", r),
                (_, Some(s)) => format!(" {}", s),
                _ => String::new(),
            };
            out.push_str(&format!(
                "{} | {} {}-{} {} (diff: {}, {}{} {})\n",
                m.date,
                m.home_team,
                m.home_goals,
                m.away_goals,
                m.away_team,
                diff,
                m.competition,
                extra,
                m.season
            ));
        }

        out
    }

    /// Overall competition statistics.
    pub fn competition_stats(&self, args: &serde_json::Value) -> String {
        let competition = args["competition"].as_str().unwrap_or("");
        let season = args["season"].as_i64();

        let matches: Vec<&crate::data::Match> = self
            .store
            .matches
            .iter()
            .filter(|m| {
                if !competition.is_empty() {
                    if !m.competition.to_lowercase().contains(&competition.to_lowercase()) {
                        return false;
                    }
                }
                if let Some(s) = season {
                    if m.season != s as i32 {
                        return false;
                    }
                }
                true
            })
            .collect();

        if matches.is_empty() {
            return "No matches found for the given filters".to_string();
        }

        let total = matches.len();
        let mut total_goals = 0i32;
        let mut home_wins = 0;
        let mut away_wins = 0;
        let mut draws = 0;

        for m in &matches {
            total_goals += m.home_goals + m.away_goals;
            if m.home_goals > m.away_goals {
                home_wins += 1;
            } else if m.home_goals < m.away_goals {
                away_wins += 1;
            } else {
                draws += 1;
            }
        }

        let avg_goals = total_goals as f64 / total as f64;
        let home_rate = home_wins as f64 / total as f64 * 100.0;
        let draw_rate = draws as f64 / total as f64 * 100.0;
        let away_rate = away_wins as f64 / total as f64 * 100.0;

        let filter_desc = {
            let mut parts = Vec::new();
            if !competition.is_empty() {
                parts.push(format!("Competition: {}", competition));
            }
            if let Some(s) = season {
                parts.push(format!("Season: {}", s));
            }
            if parts.is_empty() {
                "All competitions, all seasons".to_string()
            } else {
                parts.join(", ")
            }
        };

        // Unique seasons
        let mut seasons: Vec<i32> = matches.iter().map(|m| m.season).collect();
        seasons.sort();
        seasons.dedup();
        let season_range = if seasons.len() == 1 {
            seasons[0].to_string()
        } else {
            format!("{}-{}", seasons.first().unwrap(), seasons.last().unwrap())
        };

        format!(
            "Competition Statistics ({})\n\
            Seasons: {}\n\
            Total Matches: {}\n\
            Total Goals: {} | Avg Goals/Match: {:.2}\n\
            Home Wins: {} ({:.1}%) | Draws: {} ({:.1}%) | Away Wins: {} ({:.1}%)\n",
            filter_desc,
            season_range,
            total,
            total_goals,
            avg_goals,
            home_wins,
            home_rate,
            draws,
            draw_rate,
            away_wins,
            away_rate
        )
    }
}
