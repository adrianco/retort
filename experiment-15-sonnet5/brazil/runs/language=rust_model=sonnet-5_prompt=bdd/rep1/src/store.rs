//! In-memory knowledge base over all six datasets, with the query
//! operations the MCP tools expose.

use std::collections::HashMap;

use chrono::NaiveDate;
use schemars::JsonSchema;
use serde::Serialize;

use crate::model::{Competition, MatchOutcome, MatchRecord, PlayerRecord, Venue};
use crate::normalize::normalize_team_name;

/// Criteria for [`KnowledgeBase::find_matches`].
#[derive(Debug, Clone, Default)]
pub struct MatchFilter<'a> {
    pub team: Option<&'a str>,
    pub venue: Venue,
    pub opponent: Option<&'a str>,
    pub competition: Option<Competition>,
    pub season: Option<i32>,
    pub season_from: Option<i32>,
    pub season_to: Option<i32>,
    pub date_from: Option<NaiveDate>,
    pub date_to: Option<NaiveDate>,
}

impl MatchFilter<'_> {
    fn matches(&self, m: &MatchRecord) -> bool {
        if let Some(competition) = self.competition
            && m.competition != competition
        {
            return false;
        }
        if let Some(season) = self.season
            && m.season != season
        {
            return false;
        }
        if let Some(from) = self.season_from
            && m.season < from
        {
            return false;
        }
        if let Some(to) = self.season_to
            && m.season > to
        {
            return false;
        }
        if let Some(from) = self.date_from {
            match m.date {
                Some(d) if d >= from => {}
                _ => return false,
            }
        }
        if let Some(to) = self.date_to {
            match m.date {
                Some(d) if d <= to => {}
                _ => return false,
            }
        }
        if let Some(team) = self.team {
            let key = normalize_team_name(team);
            let home_match = crate::normalize::keys_match(&m.home_team_key, &key);
            let away_match = crate::normalize::keys_match(&m.away_team_key, &key);
            let team_side_ok = match self.venue {
                Venue::Either => home_match || away_match,
                Venue::Home => home_match,
                Venue::Away => away_match,
            };
            if !team_side_ok {
                return false;
            }
            if let Some(opponent) = self.opponent {
                let opp_key = normalize_team_name(opponent);
                let opponent_ok = if home_match {
                    crate::normalize::keys_match(&m.away_team_key, &opp_key)
                } else {
                    crate::normalize::keys_match(&m.home_team_key, &opp_key)
                };
                if !opponent_ok {
                    return false;
                }
            }
        } else if let Some(opponent) = self.opponent {
            // Opponent given without a primary team: treat as "either side".
            let opp_key = normalize_team_name(opponent);
            let ok = crate::normalize::keys_match(&m.home_team_key, &opp_key)
                || crate::normalize::keys_match(&m.away_team_key, &opp_key);
            if !ok {
                return false;
            }
        }
        true
    }
}

/// Result of [`KnowledgeBase::find_matches`]: the (possibly truncated) list
/// plus the total number of matches that satisfied the filter.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct FindMatchesResult {
    pub matches: Vec<MatchRecord>,
    pub total_count: usize,
}

#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct HeadToHeadResult {
    pub team_a: String,
    pub team_b: String,
    pub team_a_wins: u32,
    pub team_b_wins: u32,
    pub draws: u32,
    pub team_a_goals: u32,
    pub team_b_goals: u32,
    pub matches_considered: usize,
    pub matches: Vec<MatchRecord>,
}

#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TeamRecordResult {
    pub team: String,
    pub matches_played: usize,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
    pub win_rate_pct: f64,
}

#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct StandingRow {
    pub position: usize,
    pub team: String,
    pub played: u32,
    pub wins: u32,
    pub draws: u32,
    pub losses: u32,
    pub goals_for: u32,
    pub goals_against: u32,
    pub goal_difference: i32,
    pub points: u32,
}

#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct MatchStats {
    pub matches_considered: usize,
    pub average_total_goals: f64,
    pub average_home_goals: f64,
    pub average_away_goals: f64,
    pub home_win_rate_pct: f64,
    pub draw_rate_pct: f64,
    pub away_win_rate_pct: f64,
}

#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CompetitionOverview {
    pub competition: Competition,
    pub label: String,
    pub matches: usize,
    pub season_min: Option<i32>,
    pub season_max: Option<i32>,
}

/// Criteria for [`KnowledgeBase::search_players`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlayerSort {
    Overall,
    Potential,
    Age,
    Name,
}

#[derive(Debug, Clone, Default)]
pub struct PlayerFilter<'a> {
    pub name: Option<&'a str>,
    pub nationality: Option<&'a str>,
    pub club: Option<&'a str>,
    pub position: Option<&'a str>,
    pub min_overall: Option<u32>,
    pub limit: Option<usize>,
}

/// In-memory index over all loaded matches and players.
#[derive(Debug, Clone)]
pub struct KnowledgeBase {
    pub matches: Vec<MatchRecord>,
    pub players: Vec<PlayerRecord>,
    /// Normalized team key -> canonical display name (first one seen).
    team_display: HashMap<String, String>,
}

impl KnowledgeBase {
    pub fn new(matches: Vec<MatchRecord>, players: Vec<PlayerRecord>) -> Self {
        let mut team_display = HashMap::new();
        for m in &matches {
            team_display
                .entry(m.home_team_key.clone())
                .or_insert_with(|| m.home_team.clone());
            team_display
                .entry(m.away_team_key.clone())
                .or_insert_with(|| m.away_team.clone());
        }
        Self {
            matches,
            players,
            team_display,
        }
    }

    fn display_name_for(&self, query: &str) -> String {
        let key = normalize_team_name(query);
        self.team_display
            .get(&key)
            .cloned()
            .unwrap_or_else(|| query.to_string())
    }

    pub fn find_matches(&self, filter: &MatchFilter, limit: usize) -> FindMatchesResult {
        let mut found: Vec<&MatchRecord> =
            self.matches.iter().filter(|m| filter.matches(m)).collect();
        found.sort_by_key(|m| std::cmp::Reverse(m.date));
        let total_count = found.len();
        let matches = found.into_iter().take(limit).cloned().collect();
        FindMatchesResult {
            matches,
            total_count,
        }
    }

    pub fn head_to_head(
        &self,
        team_a: &str,
        team_b: &str,
        competition: Option<Competition>,
        season: Option<i32>,
        limit: usize,
    ) -> HeadToHeadResult {
        let filter = MatchFilter {
            team: Some(team_a),
            opponent: Some(team_b),
            competition,
            season,
            ..Default::default()
        };
        let mut found: Vec<&MatchRecord> =
            self.matches.iter().filter(|m| filter.matches(m)).collect();
        found.sort_by_key(|m| std::cmp::Reverse(m.date));

        let a_key = normalize_team_name(team_a);
        let mut team_a_wins = 0u32;
        let mut team_b_wins = 0u32;
        let mut draws = 0u32;
        let mut team_a_goals = 0u32;
        let mut team_b_goals = 0u32;
        for m in &found {
            let a_is_home = crate::normalize::keys_match(&m.home_team_key, &a_key);
            let (a_goals, b_goals) = if a_is_home {
                (m.home_goal, m.away_goal)
            } else {
                (m.away_goal, m.home_goal)
            };
            team_a_goals += a_goals;
            team_b_goals += b_goals;
            match a_goals.cmp(&b_goals) {
                std::cmp::Ordering::Greater => team_a_wins += 1,
                std::cmp::Ordering::Less => team_b_wins += 1,
                std::cmp::Ordering::Equal => draws += 1,
            }
        }

        HeadToHeadResult {
            team_a: self.display_name_for(team_a),
            team_b: self.display_name_for(team_b),
            team_a_wins,
            team_b_wins,
            draws,
            team_a_goals,
            team_b_goals,
            matches_considered: found.len(),
            matches: found.into_iter().take(limit).cloned().collect(),
        }
    }

    pub fn team_record(
        &self,
        team: &str,
        competition: Option<Competition>,
        season: Option<i32>,
        venue: Venue,
    ) -> TeamRecordResult {
        let filter = MatchFilter {
            team: Some(team),
            venue,
            competition,
            season,
            ..Default::default()
        };
        let key = normalize_team_name(team);
        let mut wins = 0u32;
        let mut draws = 0u32;
        let mut losses = 0u32;
        let mut goals_for = 0u32;
        let mut goals_against = 0u32;
        let mut matches_played = 0usize;

        for m in self.matches.iter().filter(|m| filter.matches(m)) {
            let is_home = crate::normalize::keys_match(&m.home_team_key, &key);
            let (gf, ga) = if is_home {
                (m.home_goal, m.away_goal)
            } else {
                (m.away_goal, m.home_goal)
            };
            goals_for += gf;
            goals_against += ga;
            matches_played += 1;
            match gf.cmp(&ga) {
                std::cmp::Ordering::Greater => wins += 1,
                std::cmp::Ordering::Less => losses += 1,
                std::cmp::Ordering::Equal => draws += 1,
            }
        }

        let win_rate_pct = if matches_played > 0 {
            (wins as f64 / matches_played as f64) * 100.0
        } else {
            0.0
        };

        TeamRecordResult {
            team: self.display_name_for(team),
            matches_played,
            wins,
            draws,
            losses,
            goals_for,
            goals_against,
            win_rate_pct,
        }
    }

    pub fn standings(&self, competition: Competition, season: i32) -> Vec<StandingRow> {
        struct Acc {
            display: String,
            played: u32,
            wins: u32,
            draws: u32,
            losses: u32,
            goals_for: u32,
            goals_against: u32,
        }

        let mut table: HashMap<String, Acc> = HashMap::new();

        fn record_side(
            table: &mut HashMap<String, Acc>,
            key: &str,
            display: &str,
            gf: u32,
            ga: u32,
        ) {
            let entry = table.entry(key.to_string()).or_insert_with(|| Acc {
                display: display.to_string(),
                played: 0,
                wins: 0,
                draws: 0,
                losses: 0,
                goals_for: 0,
                goals_against: 0,
            });
            entry.played += 1;
            entry.goals_for += gf;
            entry.goals_against += ga;
            match gf.cmp(&ga) {
                std::cmp::Ordering::Greater => entry.wins += 1,
                std::cmp::Ordering::Less => entry.losses += 1,
                std::cmp::Ordering::Equal => entry.draws += 1,
            }
        }

        for m in self
            .matches
            .iter()
            .filter(|m| m.competition == competition && m.season == season)
        {
            record_side(
                &mut table,
                &m.home_team_key,
                &m.home_team,
                m.home_goal,
                m.away_goal,
            );
            record_side(
                &mut table,
                &m.away_team_key,
                &m.away_team,
                m.away_goal,
                m.home_goal,
            );
        }

        let mut rows: Vec<StandingRow> = table
            .into_values()
            .map(|acc| StandingRow {
                position: 0,
                team: acc.display,
                played: acc.played,
                wins: acc.wins,
                draws: acc.draws,
                losses: acc.losses,
                goals_for: acc.goals_for,
                goals_against: acc.goals_against,
                goal_difference: acc.goals_for as i32 - acc.goals_against as i32,
                points: acc.wins * 3 + acc.draws,
            })
            .collect();

        // Tiebreak order follows official CBF (Brazilian league) criteria:
        // points, then wins, then goal difference, then goals scored.
        rows.sort_by(|a, b| {
            b.points
                .cmp(&a.points)
                .then(b.wins.cmp(&a.wins))
                .then(b.goal_difference.cmp(&a.goal_difference))
                .then(b.goals_for.cmp(&a.goals_for))
                .then(a.team.cmp(&b.team))
        });
        for (i, row) in rows.iter_mut().enumerate() {
            row.position = i + 1;
        }
        rows
    }

    pub fn biggest_wins(
        &self,
        competition: Option<Competition>,
        season: Option<i32>,
        limit: usize,
    ) -> Vec<MatchRecord> {
        let filter = MatchFilter {
            competition,
            season,
            ..Default::default()
        };
        let mut found: Vec<&MatchRecord> =
            self.matches.iter().filter(|m| filter.matches(m)).collect();
        found.sort_by(|a, b| {
            b.goal_difference()
                .abs()
                .cmp(&a.goal_difference().abs())
                .then(b.total_goals().cmp(&a.total_goals()))
        });
        found.into_iter().take(limit).cloned().collect()
    }

    pub fn match_stats(&self, competition: Option<Competition>, season: Option<i32>) -> MatchStats {
        let filter = MatchFilter {
            competition,
            season,
            ..Default::default()
        };
        let found: Vec<&MatchRecord> = self.matches.iter().filter(|m| filter.matches(m)).collect();
        let n = found.len();
        if n == 0 {
            return MatchStats {
                matches_considered: 0,
                average_total_goals: 0.0,
                average_home_goals: 0.0,
                average_away_goals: 0.0,
                home_win_rate_pct: 0.0,
                draw_rate_pct: 0.0,
                away_win_rate_pct: 0.0,
            };
        }
        let total_home: u32 = found.iter().map(|m| m.home_goal).sum();
        let total_away: u32 = found.iter().map(|m| m.away_goal).sum();
        let home_wins = found
            .iter()
            .filter(|m| m.outcome() == MatchOutcome::Home)
            .count();
        let away_wins = found
            .iter()
            .filter(|m| m.outcome() == MatchOutcome::Away)
            .count();
        let draws = n - home_wins - away_wins;

        MatchStats {
            matches_considered: n,
            average_total_goals: (total_home + total_away) as f64 / n as f64,
            average_home_goals: total_home as f64 / n as f64,
            average_away_goals: total_away as f64 / n as f64,
            home_win_rate_pct: home_wins as f64 / n as f64 * 100.0,
            draw_rate_pct: draws as f64 / n as f64 * 100.0,
            away_win_rate_pct: away_wins as f64 / n as f64 * 100.0,
        }
    }

    pub fn list_teams(&self, competition: Option<Competition>, season: Option<i32>) -> Vec<String> {
        let mut names: Vec<String> = self
            .matches
            .iter()
            .filter(|m| {
                competition.is_none_or(|c| m.competition == c)
                    && season.is_none_or(|s| m.season == s)
            })
            .flat_map(|m| [m.home_team.clone(), m.away_team.clone()])
            .collect();
        names.sort();
        names.dedup();
        names
    }

    pub fn competitions_overview(&self) -> Vec<CompetitionOverview> {
        let all = [
            Competition::Brasileirao,
            Competition::CopaDoBrasil,
            Competition::Libertadores,
            Competition::ExtendedStats,
            Competition::HistoricalBrasileirao,
        ];
        all.into_iter()
            .map(|competition| {
                let rows: Vec<&MatchRecord> = self
                    .matches
                    .iter()
                    .filter(|m| m.competition == competition)
                    .collect();
                let season_min = rows.iter().map(|m| m.season).min();
                let season_max = rows.iter().map(|m| m.season).max();
                CompetitionOverview {
                    competition,
                    label: competition.label().to_string(),
                    matches: rows.len(),
                    season_min,
                    season_max,
                }
            })
            .collect()
    }

    pub fn search_players(
        &self,
        filter: &PlayerFilter,
        sort_by: PlayerSort,
        descending: bool,
    ) -> (Vec<PlayerRecord>, usize) {
        let name_key = filter.name.map(normalize_team_name);
        let nationality_key = filter.nationality.map(normalize_team_name);
        let club_key = filter.club.map(normalize_team_name);
        let position_lower = filter.position.map(|p| p.to_lowercase());

        let mut found: Vec<&PlayerRecord> = self
            .players
            .iter()
            .filter(|p| {
                if let Some(nk) = &name_key
                    && !p.name_key.contains(nk.as_str())
                {
                    return false;
                }
                if let Some(nat) = &nationality_key
                    && !crate::normalize::keys_match(&p.nationality_key, nat)
                {
                    return false;
                }
                if let Some(club) = &club_key
                    && !crate::normalize::keys_match(&p.club_key, club)
                {
                    return false;
                }
                if let Some(pos) = &position_lower {
                    match &p.position {
                        Some(actual) if actual.to_lowercase().contains(pos.as_str()) => {}
                        _ => return false,
                    }
                }
                if let Some(min_overall) = filter.min_overall {
                    match p.overall {
                        Some(overall) if overall >= min_overall => {}
                        _ => return false,
                    }
                }
                true
            })
            .collect();

        found.sort_by(|a, b| {
            let ordering = match sort_by {
                PlayerSort::Overall => a.overall.cmp(&b.overall),
                PlayerSort::Potential => a.potential.cmp(&b.potential),
                PlayerSort::Age => a.age.cmp(&b.age),
                PlayerSort::Name => b.name.cmp(&a.name), // reversed so `descending` flips to A-Z
            };
            if descending {
                ordering.reverse()
            } else {
                ordering
            }
        });

        let total_count = found.len();
        let limit = filter.limit.unwrap_or(20);
        (
            found.into_iter().take(limit).cloned().collect(),
            total_count,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::MatchRecord;

    fn make_match(
        competition: Competition,
        season: i32,
        date: &str,
        home: &str,
        away: &str,
        home_goal: u32,
        away_goal: u32,
    ) -> MatchRecord {
        MatchRecord {
            competition,
            tournament: None,
            date: NaiveDate::parse_from_str(date, "%Y-%m-%d").ok(),
            season,
            round: None,
            stage: None,
            home_team: home.to_string(),
            away_team: away.to_string(),
            home_team_key: normalize_team_name(home),
            away_team_key: normalize_team_name(away),
            home_goal,
            away_goal,
            venue: None,
            home_corners: None,
            away_corners: None,
            home_shots: None,
            away_shots: None,
        }
    }

    fn sample_kb() -> KnowledgeBase {
        let matches = vec![
            make_match(
                Competition::Brasileirao,
                2023,
                "2023-05-28",
                "Fluminense",
                "Flamengo",
                1,
                0,
            ),
            make_match(
                Competition::Brasileirao,
                2023,
                "2023-09-03",
                "Flamengo",
                "Fluminense",
                2,
                1,
            ),
            make_match(
                Competition::Brasileirao,
                2023,
                "2023-04-01",
                "Flamengo",
                "Palmeiras",
                3,
                0,
            ),
            make_match(
                Competition::Libertadores,
                2023,
                "2023-06-01",
                "Flamengo",
                "Fluminense",
                0,
                0,
            ),
        ];
        KnowledgeBase::new(matches, vec![])
    }

    // Given matches across two competitions for the same pair of teams
    // When finding matches filtered to one competition
    // Then only matches from that competition are returned
    #[test]
    fn test_given_matches_in_two_competitions_when_filtering_by_competition_then_only_that_competition_is_returned()
     {
        let kb = sample_kb();
        let filter = MatchFilter {
            team: Some("Flamengo"),
            opponent: Some("Fluminense"),
            competition: Some(Competition::Brasileirao),
            ..Default::default()
        };
        let result = kb.find_matches(&filter, 10);
        assert_eq!(result.total_count, 2);
        assert!(
            result
                .matches
                .iter()
                .all(|m| m.competition == Competition::Brasileirao)
        );
    }

    // Given matches for a team using a state-suffixed query name
    // When finding matches
    // Then results are returned in descending date order
    #[test]
    fn test_given_multiple_matches_when_finding_by_team_then_results_are_sorted_newest_first() {
        let kb = sample_kb();
        let filter = MatchFilter {
            team: Some("Flamengo"),
            ..Default::default()
        };
        let result = kb.find_matches(&filter, 10);
        assert_eq!(result.total_count, 4);
        assert_eq!(result.matches[0].date.unwrap().to_string(), "2023-09-03");
        assert_eq!(result.matches[1].date.unwrap().to_string(), "2023-06-01");
        assert_eq!(result.matches[2].date.unwrap().to_string(), "2023-05-28");
        assert_eq!(result.matches[3].date.unwrap().to_string(), "2023-04-01");
    }

    // Given a limit smaller than the number of matching results
    // When finding matches
    // Then the returned list is truncated but the total count reflects all matches
    #[test]
    fn test_given_limit_smaller_than_results_when_finding_matches_then_list_is_truncated_but_total_count_is_full()
     {
        let kb = sample_kb();
        let filter = MatchFilter {
            team: Some("Flamengo"),
            ..Default::default()
        };
        let result = kb.find_matches(&filter, 1);
        assert_eq!(result.matches.len(), 1);
        assert_eq!(result.total_count, 4);
    }

    // Given head-to-head history between two derby rivals
    // When computing head-to-head
    // Then wins/draws/goals are tallied from each team's own perspective
    #[test]
    fn test_given_derby_history_when_computing_head_to_head_then_wins_and_goals_are_tallied_correctly()
     {
        let kb = sample_kb();
        let h2h = kb.head_to_head("Flamengo", "Fluminense", None, None, 10);
        assert_eq!(h2h.matches_considered, 3);
        assert_eq!(h2h.team_a_wins, 1); // 2023-09-03 Flamengo 2-1
        assert_eq!(h2h.team_b_wins, 1); // 2023-05-28 Fluminense 1-0 Flamengo
        assert_eq!(h2h.draws, 1); // Libertadores 0-0
        assert_eq!(h2h.team_a_goals, 2);
        assert_eq!(h2h.team_b_goals, 2);
    }

    // Given a team with two wins and one loss across its Brasileirao matches
    // When computing its team record
    // Then the win rate and goal tallies are correct
    #[test]
    fn test_given_team_with_two_wins_and_a_loss_when_computing_record_then_win_rate_is_correct() {
        let kb = sample_kb();
        let record = kb.team_record(
            "Flamengo",
            Some(Competition::Brasileirao),
            Some(2023),
            Venue::Either,
        );
        assert_eq!(record.matches_played, 3);
        assert_eq!(record.wins, 2);
        assert_eq!(record.losses, 1);
        assert!((record.win_rate_pct - (2.0 / 3.0 * 100.0)).abs() < 1e-9);
    }

    // Given only home matches are requested
    // When computing a team's record with the home venue filter
    // Then away matches are excluded from the tally
    #[test]
    fn test_given_home_venue_filter_when_computing_team_record_then_away_matches_are_excluded() {
        let kb = sample_kb();
        let record = kb.team_record("Flamengo", None, None, Venue::Home);
        // Flamengo is home in 3 of its 4 matches, away in the other 1.
        assert_eq!(record.matches_played, 3);
    }

    // Given a season with three teams and known results
    // When computing standings
    // Then teams are ranked by points then goal difference
    #[test]
    fn test_given_season_results_when_computing_standings_then_teams_are_ranked_by_points() {
        let kb = sample_kb();
        let table = kb.standings(Competition::Brasileirao, 2023);
        assert_eq!(table[0].team, "Flamengo");
        assert_eq!(table[0].points, 6); // two wins
        assert_eq!(table[0].position, 1);
    }

    // Given matches with varying goal differences
    // When finding the biggest wins
    // Then they are sorted by absolute goal difference descending
    #[test]
    fn test_given_matches_with_varying_margins_when_finding_biggest_wins_then_largest_margin_is_first()
     {
        let kb = sample_kb();
        let wins = kb.biggest_wins(None, None, 1);
        assert_eq!(wins[0].goal_difference().abs(), 3);
    }

    // Given four matches with a mix of home/away/draw outcomes
    // When computing aggregate match stats
    // Then the averages and rates are computed over all matches
    #[test]
    fn test_given_mixed_outcomes_when_computing_match_stats_then_averages_are_correct() {
        let kb = sample_kb();
        let stats = kb.match_stats(None, None);
        assert_eq!(stats.matches_considered, 4);
        // Fluminense 1-0 Flamengo, Flamengo 2-1 Fluminense, Flamengo 3-0 Palmeiras, Flamengo 0-0 Fluminense
        let total_goals: u32 = 1 + 3 + 3;
        assert!((stats.average_total_goals - (total_goals as f64 / 4.0)).abs() < 1e-9);
    }

    // Given no matches satisfy a filter
    // When computing match stats
    // Then rates are zero rather than dividing by zero
    #[test]
    fn test_given_no_matching_matches_when_computing_match_stats_then_result_is_all_zero() {
        let kb = sample_kb();
        let stats = kb.match_stats(Some(Competition::CopaDoBrasil), None);
        assert_eq!(stats.matches_considered, 0);
        assert_eq!(stats.average_total_goals, 0.0);
    }

    fn sample_players() -> KnowledgeBase {
        let mut players = vec![
            crate::model::PlayerRecord {
                id: 1,
                name: "Gabriel Barbosa".into(),
                age: Some(26),
                nationality: "Brazil".into(),
                overall: Some(82),
                potential: Some(83),
                club: Some("Flamengo".into()),
                position: Some("ST".into()),
                jersey_number: Some(9),
                height: None,
                weight: None,
                nationality_key: normalize_team_name("Brazil"),
                club_key: normalize_team_name("Flamengo"),
                name_key: normalize_team_name("Gabriel Barbosa"),
            },
            crate::model::PlayerRecord {
                id: 2,
                name: "Everton Ribeiro".into(),
                age: Some(33),
                nationality: "Brazil".into(),
                overall: Some(78),
                potential: Some(78),
                club: Some("Flamengo".into()),
                position: Some("RM".into()),
                jersey_number: Some(7),
                height: None,
                weight: None,
                nationality_key: normalize_team_name("Brazil"),
                club_key: normalize_team_name("Flamengo"),
                name_key: normalize_team_name("Everton Ribeiro"),
            },
            crate::model::PlayerRecord {
                id: 3,
                name: "Lionel Messi".into(),
                age: Some(35),
                nationality: "Argentina".into(),
                overall: Some(93),
                potential: Some(93),
                club: Some("Paris Saint-Germain".into()),
                position: Some("RW".into()),
                jersey_number: Some(30),
                height: None,
                weight: None,
                nationality_key: normalize_team_name("Argentina"),
                club_key: normalize_team_name("Paris Saint-Germain"),
                name_key: normalize_team_name("Lionel Messi"),
            },
        ];
        players.sort_by_key(|p| p.id);
        KnowledgeBase::new(vec![], players)
    }

    // Given players from several clubs and nationalities
    // When searching players by club
    // Then only players from that club are returned, ranked by overall
    #[test]
    fn test_given_players_from_several_clubs_when_searching_by_club_then_only_that_club_is_returned()
     {
        let kb = sample_players();
        let filter = PlayerFilter {
            club: Some("Flamengo"),
            ..Default::default()
        };
        let (found, total) = kb.search_players(&filter, PlayerSort::Overall, true);
        assert_eq!(total, 2);
        assert_eq!(found[0].name, "Gabriel Barbosa"); // higher overall first
    }

    // Given players of different nationalities
    // When searching players by nationality
    // Then only players of that nationality are returned
    #[test]
    fn test_given_players_of_different_nationalities_when_searching_then_only_that_nationality_is_returned()
     {
        let kb = sample_players();
        let filter = PlayerFilter {
            nationality: Some("Brazil"),
            ..Default::default()
        };
        let (found, total) = kb.search_players(&filter, PlayerSort::Overall, true);
        assert_eq!(total, 2);
        assert!(found.iter().all(|p| p.nationality == "Brazil"));
    }

    // Given a minimum overall rating threshold
    // When searching players
    // Then players below the threshold are excluded
    #[test]
    fn test_given_min_overall_threshold_when_searching_players_then_lower_rated_players_are_excluded()
     {
        let kb = sample_players();
        let filter = PlayerFilter {
            min_overall: Some(90),
            ..Default::default()
        };
        let (found, total) = kb.search_players(&filter, PlayerSort::Overall, true);
        assert_eq!(total, 1);
        assert_eq!(found[0].name, "Lionel Messi");
    }
}
