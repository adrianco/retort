//! Presentation layer: turns query results into the natural-language answers
//! the specification asks for, plus the machine-readable JSON that MCP clients
//! receive alongside the text.

use serde_json::{json, Map, Value};

use crate::graph::KnowledgeGraph;
use crate::model::*;
use crate::queries::*;

/// `2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)`
pub fn match_line(graph: &KnowledgeGraph, id: MatchId) -> String {
    let m = graph.match_by_id(id);
    let date = m
        .date
        .map(|d| d.to_string())
        .unwrap_or_else(|| format!("{} (date unknown)", m.season));
    let mut context = m.competition.name().to_string();
    if let Some(phase) = m.phase() {
        context.push_str(", ");
        context.push_str(&phase);
    }
    match (m.home_goals, m.away_goals) {
        (Some(h), Some(a)) => format!(
            "{date}: {} {h}-{a} {} ({context})",
            graph.team(m.home).name,
            graph.team(m.away).name
        ),
        // Rows such as the postponed 2022 Flamengo–Corinthians fixture carry
        // "NA" scores in the source file.
        _ => format!(
            "{date}: {} vs {} (no result recorded, {context})",
            graph.team(m.home).name,
            graph.team(m.away).name
        ),
    }
}

pub fn match_json(graph: &KnowledgeGraph, id: MatchId) -> Value {
    let m = graph.match_by_id(id);
    let mut value = json!({
        "id": m.id,
        "date": m.date.map(|d| d.to_string()),
        "season": m.season,
        "competition": m.competition.name(),
        "competition_id": m.competition.slug(),
        "home_team": graph.team(m.home).name,
        "away_team": graph.team(m.away).name,
        "home_team_key": graph.team(m.home).key,
        "away_team_key": graph.team(m.away).key,
        "home_goals": m.home_goals,
        "away_goals": m.away_goals,
        "source": m.source.file_name(),
        "canonical": m.canonical,
    });
    let object = value.as_object_mut().unwrap();
    if let Some(round) = &m.round {
        object.insert("round".into(), json!(round));
    }
    if let Some(stage) = &m.stage {
        object.insert("stage".into(), json!(stage));
    }
    if let Some(venue) = &m.venue {
        object.insert("venue".into(), json!(venue));
    }
    if let Some(time) = &m.time {
        object.insert("kickoff".into(), json!(time));
    }
    if let Some(stats) = &m.stats {
        object.insert(
            "statistics".into(),
            json!({
                "home_shots": stats.home_shots,
                "away_shots": stats.away_shots,
                "home_corners": stats.home_corners,
                "away_corners": stats.away_corners,
                "home_attacks": stats.home_attacks,
                "away_attacks": stats.away_attacks,
                "half_time_home": stats.half_time_home,
                "half_time_away": stats.half_time_away,
            }),
        );
    }
    value
}

pub fn record_json(record: &Record) -> Value {
    json!({
        "matches": record.matches,
        "wins": record.wins,
        "draws": record.draws,
        "losses": record.losses,
        "goals_for": record.goals_for,
        "goals_against": record.goals_against,
        "goal_difference": record.goal_difference(),
        "points": record.points(),
        "clean_sheets": record.clean_sheets,
        "win_rate_pct": round1(record.win_rate()),
    })
}

pub fn record_line(record: &Record) -> String {
    format!(
        "Matches: {}, W{} D{} L{}, GF {} GA {} (GD {:+}), Points {}, Win rate {:.1}%",
        record.matches,
        record.wins,
        record.draws,
        record.losses,
        record.goals_for,
        record.goals_against,
        record.goal_difference(),
        record.points(),
        record.win_rate()
    )
}

fn round1(value: f64) -> f64 {
    (value * 10.0).round() / 10.0
}

fn round2(value: f64) -> f64 {
    (value * 100.0).round() / 100.0
}

/// Renders a match search, including the head-to-head tally when two teams
/// were given (the format the specification illustrates for Fla-Flu).
pub fn match_search(graph: &KnowledgeGraph, search: &MatchSearch, title: &str) -> (String, Value) {
    let mut text = String::new();
    text.push_str(title);
    text.push('\n');
    if search.matches.is_empty() {
        text.push_str("No matches found for these filters.\n");
    }
    for id in &search.matches {
        text.push_str("- ");
        text.push_str(&match_line(graph, *id));
        text.push('\n');
    }
    if search.total > search.matches.len() {
        text.push_str(&format!(
            "... ({} more matches in the dataset)\n",
            search.total - search.matches.len()
        ));
    }
    if let Some(h2h) = &search.head_to_head {
        text.push('\n');
        text.push_str(&head_to_head_summary_line(graph, h2h));
        text.push('\n');
    }
    let value = json!({
        "total_matches": search.total,
        "returned": search.matches.len(),
        "matches": search.matches.iter().map(|id| match_json(graph, *id)).collect::<Vec<_>>(),
        "head_to_head": search.head_to_head.as_ref().map(|h| head_to_head_json(graph, h)),
    });
    (text, value)
}

fn head_to_head_summary_line(graph: &KnowledgeGraph, h2h: &HeadToHead) -> String {
    format!(
        "Head-to-head in dataset: {} {} wins, {} {} wins, {} draws (goals {}-{})",
        graph.team(h2h.team_a).name,
        h2h.record.wins,
        graph.team(h2h.team_b).name,
        h2h.record.losses,
        h2h.record.draws,
        h2h.record.goals_for,
        h2h.record.goals_against
    )
}

pub fn head_to_head_json(graph: &KnowledgeGraph, h2h: &HeadToHead) -> Value {
    json!({
        "team_a": graph.team(h2h.team_a).name,
        "team_b": graph.team(h2h.team_b).name,
        "matches_played": h2h.record.matches,
        "team_a_wins": h2h.record.wins,
        "team_b_wins": h2h.record.losses,
        "draws": h2h.record.draws,
        "team_a_goals": h2h.record.goals_for,
        "team_b_goals": h2h.record.goals_against,
        "by_competition": h2h.by_competition.iter().map(|(competition, record)| json!({
            "competition": competition.name(),
            "record": record_json(record),
        })).collect::<Vec<_>>(),
        "last_meeting": h2h.last_meeting.map(|id| match_json(graph, id)),
        "biggest_team_a_win": h2h.biggest_a.map(|id| match_json(graph, id)),
        "biggest_team_b_win": h2h.biggest_b.map(|id| match_json(graph, id)),
    })
}

pub fn head_to_head(graph: &KnowledgeGraph, h2h: &HeadToHead, recent: usize) -> (String, Value) {
    let team_a = graph.team(h2h.team_a);
    let team_b = graph.team(h2h.team_b);
    let mut text = format!("{} vs {} head-to-head:\n", team_a.name, team_b.name);
    if h2h.record.matches == 0 {
        text.push_str("These clubs never met in the provided datasets.\n");
    } else {
        text.push_str(&format!(
            "- Matches: {}\n- {} wins: {}\n- {} wins: {}\n- Draws: {}\n- Goals: {} {} - {} {}\n",
            h2h.record.matches,
            team_a.name,
            h2h.record.wins,
            team_b.name,
            h2h.record.losses,
            h2h.record.draws,
            team_a.name,
            h2h.record.goals_for,
            h2h.record.goals_against,
            team_b.name,
        ));
        if !h2h.by_competition.is_empty() {
            text.push_str("\nBy competition:\n");
            for (competition, record) in &h2h.by_competition {
                text.push_str(&format!(
                    "- {}: {} matches, {}W {}D {}L\n",
                    competition.name(),
                    record.matches,
                    record.wins,
                    record.draws,
                    record.losses
                ));
            }
        }
        if let Some(id) = h2h.last_meeting {
            text.push_str(&format!(
                "\nMost recent meeting: {}\n",
                match_line(graph, id)
            ));
        }
        if recent > 0 {
            text.push_str("\nRecent meetings:\n");
            for id in h2h.matches.iter().rev().take(recent) {
                text.push_str("- ");
                text.push_str(&match_line(graph, *id));
                text.push('\n');
            }
        }
    }
    let mut value = head_to_head_json(graph, h2h);
    value.as_object_mut().unwrap().insert(
        "matches".into(),
        json!(h2h
            .matches
            .iter()
            .rev()
            .take(recent.max(10))
            .map(|id| match_json(graph, *id))
            .collect::<Vec<_>>()),
    );
    (text, value)
}

/// Team statistics in the layout the specification shows for Corinthians.
pub fn team_stats(graph: &KnowledgeGraph, stats: &TeamStats) -> (String, Value) {
    let team = graph.team(stats.team);
    let scope = {
        let mut parts = Vec::new();
        if let Some(season) = stats.season {
            parts.push(season.to_string());
        }
        if let Some(competition) = stats.competition {
            parts.push(competition.name().to_string());
        }
        if parts.is_empty() {
            "all competitions and seasons".to_string()
        } else {
            parts.join(" ")
        }
    };
    let record = match stats.venue {
        Venue::All => &stats.overall,
        Venue::Home => &stats.home,
        Venue::Away => &stats.away,
    };
    let mut text = format!(
        "{} {} ({scope}):\n- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {}\n- Win rate: {:.1}%\n- Points (3-1-0): {} ({:.2} per match)\n",
        team.display(),
        match stats.venue {
            Venue::All => "record",
            Venue::Home => "home record",
            Venue::Away => "away record",
        },
        record.matches,
        record.wins,
        record.draws,
        record.losses,
        record.goals_for,
        record.goals_against,
        record.win_rate(),
        record.points(),
        record.points_per_match(),
    );

    if stats.venue == Venue::All && stats.overall.matches > 0 {
        text.push_str(&format!(
            "\nHome: {}\nAway: {}\n",
            record_line(&stats.home),
            record_line(&stats.away)
        ));
    }
    if stats.by_competition.len() > 1 {
        text.push_str("\nBy competition:\n");
        for (competition, record) in &stats.by_competition {
            text.push_str(&format!(
                "- {}: {} matches, {}W {}D {}L, {} GF, {} GA\n",
                competition.name(),
                record.matches,
                record.wins,
                record.draws,
                record.losses,
                record.goals_for,
                record.goals_against
            ));
        }
    }
    if stats.season.is_none() && stats.by_season.len() > 1 {
        text.push_str("\nBy season:\n");
        for (season, record) in &stats.by_season {
            text.push_str(&format!(
                "- {season}: {} matches, {}W {}D {}L ({} pts)\n",
                record.matches,
                record.wins,
                record.draws,
                record.losses,
                record.points()
            ));
        }
    }
    if let Some(id) = stats.biggest_win {
        text.push_str(&format!("\nBiggest win: {}\n", match_line(graph, id)));
    }
    if let Some(id) = stats.biggest_defeat {
        text.push_str(&format!("Heaviest defeat: {}\n", match_line(graph, id)));
    }

    let value = json!({
        "team": team.name,
        "team_key": team.key,
        "scope": scope,
        "venue": stats.venue.label(),
        "record": record_json(record),
        "home": record_json(&stats.home),
        "away": record_json(&stats.away),
        "by_competition": stats.by_competition.iter().map(|(competition, record)| json!({
            "competition": competition.name(),
            "record": record_json(record),
        })).collect::<Vec<_>>(),
        "by_season": stats.by_season.iter().map(|(season, record)| json!({
            "season": season,
            "record": record_json(record),
        })).collect::<Vec<_>>(),
        "biggest_win": stats.biggest_win.map(|id| match_json(graph, id)),
        "biggest_defeat": stats.biggest_defeat.map(|id| match_json(graph, id)),
    });
    (text, value)
}

/// League table, with champion and relegation annotations when the season is
/// complete.
pub fn standings(graph: &KnowledgeGraph, table: &Standings, limit: usize) -> (String, Value) {
    let mut text = format!(
        "{} {} table (calculated from {} matches in the dataset):\n",
        table.season,
        table.competition.name(),
        table.matches_counted
    );
    if table.rows.is_empty() {
        text.push_str("No matches for that competition and season.\n");
    }
    let relegation_positions: Vec<usize> =
        table.relegated().iter().map(|row| row.position).collect();
    for row in table
        .rows
        .iter()
        .take(if limit == 0 { usize::MAX } else { limit })
    {
        let team = graph.team(row.team);
        let mut annotation = String::new();
        if row.position == 1 && table.complete {
            annotation.push_str(" - Champion");
        }
        if relegation_positions.contains(&row.position) {
            annotation.push_str(" - Relegated");
        }
        text.push_str(&format!(
            "{:>2}. {} - {} pts ({}W, {}D, {}L) GF {} GA {} GD {:+}{}\n",
            row.position,
            team.name,
            row.record.points(),
            row.record.wins,
            row.record.draws,
            row.record.losses,
            row.record.goals_for,
            row.record.goals_against,
            row.record.goal_difference(),
            annotation
        ));
    }
    if table.complete && table.matches_counted < table.matches_expected {
        text.push_str(&format!(
            "\nNote: {} fixture(s) of the {} in a full double round-robin are missing from the source file.\n",
            table.matches_expected - table.matches_counted,
            table.matches_expected
        ));
    }
    if !table.complete && !table.rows.is_empty() {
        text.push_str(
            "\nNote: the dataset does not contain a full round-robin for this season, so the table is partial (no champion/relegation call).\n",
        );
    }
    if let Some(source) = table.source {
        text.push_str(&format!("Source file: {}\n", source.file_name()));
    }

    let value = json!({
        "competition": table.competition.name(),
        "season": table.season,
        "complete_season": table.complete,
        "matches_counted": table.matches_counted,
        "rounds_played": table.rounds_played,
        "source": table.source.map(|s| s.file_name()),
        "champion": table.champion().map(|row| graph.team(row.team).name.clone()),
        "relegated": table.relegated().iter().map(|row| graph.team(row.team).name.clone()).collect::<Vec<_>>(),
        "table": table.rows.iter().map(|row| json!({
            "position": row.position,
            "team": graph.team(row.team).name,
            "team_key": graph.team(row.team).key,
            "record": record_json(&row.record),
            "home": record_json(&row.home),
            "away": record_json(&row.away),
        })).collect::<Vec<_>>(),
    });
    (text, value)
}

/// Competition-wide averages, per season and in total.
pub fn competition_stats(graph: &KnowledgeGraph, stats: &CompetitionStats) -> (String, Value) {
    let total = &stats.total;
    let mut text = format!(
        "{} aggregate statistics ({} matches across {} seasons):\n- Goals: {} ({:.2} per match)\n- Home wins: {} ({:.1}%)\n- Draws: {} ({:.1}%)\n- Away wins: {} ({:.1}%)\n- Distinct clubs: {}\n",
        stats.competition.name(),
        total.matches,
        stats.seasons.len(),
        total.goals,
        total.goals_per_match(),
        total.home_wins,
        total.rate(total.home_wins),
        total.draws,
        total.rate(total.draws),
        total.away_wins,
        total.rate(total.away_wins),
        total.teams,
    );
    if stats.seasons.len() > 1 {
        text.push_str("\nPer season:\n");
        for season in &stats.seasons {
            text.push_str(&format!(
                "- {}: {} matches, {:.2} goals/match, home win rate {:.1}%\n",
                season.season,
                season.matches,
                season.goals_per_match(),
                season.rate(season.home_wins)
            ));
        }
    }
    if let Some(id) = stats.highest_scoring {
        text.push_str(&format!(
            "\nHighest scoring match: {}\n",
            match_line(graph, id)
        ));
    }
    if let Some(id) = stats.biggest_margin {
        text.push_str(&format!("Biggest margin: {}\n", match_line(graph, id)));
    }

    let value = json!({
        "competition": stats.competition.name(),
        "matches": total.matches,
        "goals": total.goals,
        "goals_per_match": round2(total.goals_per_match()),
        "home_win_pct": round1(total.rate(total.home_wins)),
        "draw_pct": round1(total.rate(total.draws)),
        "away_win_pct": round1(total.rate(total.away_wins)),
        "distinct_teams": total.teams,
        "seasons": stats.seasons.iter().map(|season| json!({
            "season": season.season,
            "matches": season.matches,
            "goals": season.goals,
            "goals_per_match": round2(season.goals_per_match()),
            "home_wins": season.home_wins,
            "draws": season.draws,
            "away_wins": season.away_wins,
            "home_win_pct": round1(season.rate(season.home_wins)),
            "teams": season.teams,
        })).collect::<Vec<_>>(),
        "highest_scoring_match": stats.highest_scoring.map(|id| match_json(graph, id)),
        "biggest_margin_match": stats.biggest_margin.map(|id| match_json(graph, id)),
    });
    (text, value)
}

pub fn rankings(
    graph: &KnowledgeGraph,
    ranked: &[RankedTeam],
    metric: Metric,
    title: &str,
) -> (String, Value) {
    let mut text = format!("{title}\n");
    if ranked.is_empty() {
        text.push_str("No teams matched those filters.\n");
    }
    for (idx, entry) in ranked.iter().enumerate() {
        text.push_str(&format!(
            "{:>2}. {} - {} {} ({} matches, {}W {}D {}L, GF {} GA {})\n",
            idx + 1,
            graph.team(entry.team).name,
            format_metric_value(metric, entry.value),
            metric.label(),
            entry.record.matches,
            entry.record.wins,
            entry.record.draws,
            entry.record.losses,
            entry.record.goals_for,
            entry.record.goals_against
        ));
    }
    let value = json!({
        "metric": metric.label(),
        "ranking": ranked.iter().enumerate().map(|(idx, entry)| json!({
            "rank": idx + 1,
            "team": graph.team(entry.team).name,
            "team_key": graph.team(entry.team).key,
            "value": round2(entry.value),
            "record": record_json(&entry.record),
        })).collect::<Vec<_>>(),
    });
    (text, value)
}

fn format_metric_value(metric: Metric, value: f64) -> String {
    match metric {
        Metric::WinRate => format!("{value:.1}%"),
        Metric::GoalsForPerMatch => format!("{value:.2}"),
        _ => format!("{}", value.round() as i64),
    }
}

pub fn player_line(graph: &KnowledgeGraph, id: PlayerId) -> String {
    let player = graph.player(id);
    let club = player
        .club_team
        .map(|team| graph.team(team).display())
        .or_else(|| player.club.clone())
        .unwrap_or_else(|| "no club".to_string());
    format!(
        "{} - Overall: {}, Position: {}, Club: {} ({}, age {})",
        player.name,
        player.overall,
        player.position.clone().unwrap_or_else(|| "?".into()),
        club,
        player.nationality,
        player
            .age
            .map(|a| a.to_string())
            .unwrap_or_else(|| "?".into())
    )
}

pub fn player_json(graph: &KnowledgeGraph, id: PlayerId) -> Value {
    let player = graph.player(id);
    json!({
        "fifa_id": player.fifa_id,
        "name": player.name,
        "age": player.age,
        "nationality": player.nationality,
        "overall": player.overall,
        "potential": player.potential,
        "club": player.club,
        "club_in_match_data": player.club_team.map(|team| graph.team(team).name.clone()),
        "position": player.position,
        "jersey_number": player.jersey_number,
        "value": player.value,
        "wage": player.wage,
        "height": player.height,
        "weight": player.weight,
        "preferred_foot": player.preferred_foot,
    })
}

pub fn player_search(
    graph: &KnowledgeGraph,
    search: &PlayerSearch,
    title: &str,
) -> (String, Value) {
    let mut text = format!("{title}\n");
    if search.players.is_empty() {
        text.push_str("No players matched those filters.\n");
    }
    for (idx, id) in search.players.iter().enumerate() {
        text.push_str(&format!("{}. {}\n", idx + 1, player_line(graph, *id)));
    }
    if search.total > search.players.len() {
        text.push_str(&format!(
            "... ({} more players match)\n",
            search.total - search.players.len()
        ));
    }
    if search.total > 0 {
        text.push_str(&format!(
            "Average FIFA overall across all {} matching players: {:.1}\n",
            search.total, search.average_overall
        ));
    }
    let value = json!({
        "total": search.total,
        "returned": search.players.len(),
        "average_overall": round1(search.average_overall),
        "players": search.players.iter().map(|id| player_json(graph, *id)).collect::<Vec<_>>(),
    });
    (text, value)
}

pub fn player_profile(graph: &KnowledgeGraph, id: PlayerId) -> (String, Value) {
    let player = graph.player(id);
    let mut text = format!(
        "{} ({}, age {})\n- FIFA overall: {} (potential {})\n- Position: {}{}\n- Club: {}\n",
        player.name,
        player.nationality,
        player
            .age
            .map(|a| a.to_string())
            .unwrap_or_else(|| "?".into()),
        player.overall,
        player.potential,
        player.position.clone().unwrap_or_else(|| "unknown".into()),
        player
            .jersey_number
            .map(|n| format!(", shirt #{n}"))
            .unwrap_or_default(),
        player.club.clone().unwrap_or_else(|| "free agent".into()),
    );
    if let (Some(value), Some(wage)) = (&player.value, &player.wage) {
        text.push_str(&format!("- Market value: {value}, wage: {wage}\n"));
    }
    if let (Some(height), Some(weight)) = (&player.height, &player.weight) {
        text.push_str(&format!("- Height: {height}, weight: {weight}\n"));
    }
    if let Some(foot) = &player.preferred_foot {
        text.push_str(&format!("- Preferred foot: {foot}\n"));
    }
    let top = player.top_attributes(6);
    if !top.is_empty() {
        text.push_str("- Best attributes: ");
        text.push_str(
            &top.iter()
                .map(|(name, value)| format!("{name} {value}"))
                .collect::<Vec<_>>()
                .join(", "),
        );
        text.push('\n');
    }
    if let Some(team) = player.club_team {
        let profile = team_profile_line(graph, team);
        text.push_str(&format!(
            "- Club in match data: {} ({profile})\n",
            graph.team(team).display()
        ));
    } else if player.club.is_some() {
        text.push_str("- This club does not appear in the Brazilian match datasets.\n");
    }

    let mut attributes = Map::new();
    for (name, value) in ATTRIBUTE_NAMES.iter().zip(player.attributes.iter()) {
        if *value > 0 {
            attributes.insert((*name).to_string(), json!(value));
        }
    }
    let mut value = player_json(graph, id);
    value
        .as_object_mut()
        .unwrap()
        .insert("attributes".into(), Value::Object(attributes));
    (text, value)
}

fn team_profile_line(graph: &KnowledgeGraph, team: TeamId) -> String {
    let matches = graph.team_matches(team).len();
    format!("{matches} matches in the match datasets")
}

pub fn club_squad(graph: &KnowledgeGraph, squad: &ClubSquad, limit: usize) -> (String, Value) {
    let mut text = format!("Squad for {} in the FIFA dataset:\n", squad.club_label);
    if let Some(note) = &squad.note {
        text.push_str(note);
        text.push('\n');
    }
    if squad.players.is_empty() {
        text.push_str(
            "No players found. The FIFA 19 database only includes officially licensed Brazilian clubs.\n",
        );
        let available = linked_clubs(graph);
        if !available.is_empty() {
            text.push_str("Brazilian clubs with player data: ");
            text.push_str(
                &available
                    .iter()
                    .map(|(team, count, _)| format!("{} ({count})", graph.team(*team).name))
                    .collect::<Vec<_>>()
                    .join(", "),
            );
            text.push('\n');
        }
    } else {
        text.push_str(&format!(
            "- Players: {}, average overall: {:.1}, Brazilian nationals: {}\n",
            squad.players.len(),
            squad.average_overall,
            squad.brazilian_players
        ));
        for (idx, id) in squad.players.iter().take(limit).enumerate() {
            text.push_str(&format!("{}. {}\n", idx + 1, player_line(graph, *id)));
        }
        if let Some(team) = squad.team {
            text.push_str(&format!(
                "- Match data: {} matches recorded for {}\n",
                graph.team_matches(team).len(),
                graph.team(team).display()
            ));
        }
    }
    let value = json!({
        "club": squad.club_label,
        "players_found": squad.players.len(),
        "average_overall": round1(squad.average_overall),
        "brazilian_nationals": squad.brazilian_players,
        "players": squad.players.iter().take(limit).map(|id| player_json(graph, *id)).collect::<Vec<_>>(),
        "matches_in_graph": squad.team.map(|team| graph.team_matches(team).len()),
    });
    (text, value)
}

pub fn team_profile(graph: &KnowledgeGraph, profile: &TeamProfile) -> (String, Value) {
    let team = graph.team(profile.team);
    let mut text = format!("{} profile:\n", team.display());
    text.push_str(&format!("- Overall: {}\n", record_line(&profile.overall)));
    text.push_str("- Competitions in the datasets:\n");
    for (competition, seasons, record) in &profile.competitions {
        text.push_str(&format!(
            "  - {}: {} matches, seasons {}\n",
            competition.name(),
            record.matches,
            summarize_seasons(seasons)
        ));
    }
    if let Some(id) = profile.first_match {
        text.push_str(&format!("- First match: {}\n", match_line(graph, id)));
    }
    if let Some(id) = profile.last_match {
        text.push_str(&format!("- Latest match: {}\n", match_line(graph, id)));
    }
    if !profile.squad.is_empty() {
        text.push_str(&format!(
            "- FIFA squad: {} players, best: {}\n",
            profile.squad.len(),
            player_line(graph, profile.squad[0])
        ));
    }
    if !team.aliases.is_empty() {
        text.push_str(&format!(
            "- Name variants in the data: {}\n",
            team.aliases.join(" | ")
        ));
    }
    let value = json!({
        "team": team.name,
        "team_key": team.key,
        "state": team.state,
        "country": team.country,
        "aliases": team.aliases,
        "overall": record_json(&profile.overall),
        "competitions": profile.competitions.iter().map(|(competition, seasons, record)| json!({
            "competition": competition.name(),
            "competition_id": competition.slug(),
            "seasons": seasons,
            "record": record_json(record),
        })).collect::<Vec<_>>(),
        "squad_size": profile.squad.len(),
        "first_match": profile.first_match.map(|id| match_json(graph, id)),
        "last_match": profile.last_match.map(|id| match_json(graph, id)),
    });
    (text, value)
}

/// `2012-2016, 2018` instead of listing every year.
pub fn summarize_seasons(seasons: &[i32]) -> String {
    let mut parts = Vec::new();
    let mut idx = 0;
    while idx < seasons.len() {
        let start = seasons[idx];
        let mut end = start;
        while idx + 1 < seasons.len() && seasons[idx + 1] == end + 1 {
            idx += 1;
            end = seasons[idx];
        }
        if start == end {
            parts.push(start.to_string());
        } else {
            parts.push(format!("{start}-{end}"));
        }
        idx += 1;
    }
    parts.join(", ")
}

#[cfg(test)]
mod tests {
    use super::summarize_seasons;

    #[test]
    fn season_ranges_collapse() {
        assert_eq!(
            summarize_seasons(&[2012, 2013, 2014, 2016]),
            "2012-2014, 2016"
        );
        assert_eq!(summarize_seasons(&[2019]), "2019");
        assert_eq!(summarize_seasons(&[]), "");
    }
}
