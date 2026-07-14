//! ============================================================================
//! Context
//! ----------------------------------------------------------------------------
//! Module:   format
//! Purpose:  Render query results into the human-readable text blocks shown in
//!           the specification's "Example answer format" sections. These are
//!           the strings the MCP tools return to the LLM/user.
//!
//! Formatting is intentionally separate from `query` so the analytical logic
//! stays free of presentation concerns and remains easy to test.
//! ============================================================================

use crate::models::{Match, Player};
use crate::query::{
    ClubAggregate, CompetitionStats, HeadToHead, Standing, TeamRecord,
};

/// Cap on how many match/player lines we print before summarizing the rest.
const MAX_LINES: usize = 25;

pub fn format_matches(title: &str, matches: &[&Match]) -> String {
    if matches.is_empty() {
        return format!("{}\nNo matches found in the dataset.", title);
    }
    let mut out = format!("{} ({} found):\n", title, matches.len());
    for m in matches.iter().take(MAX_LINES) {
        out.push_str(&format!("- {}\n", m.summary()));
    }
    if matches.len() > MAX_LINES {
        out.push_str(&format!("- ... ({} more in dataset)\n", matches.len() - MAX_LINES));
    }
    out
}

pub fn format_head_to_head(h: &HeadToHead) -> String {
    let mut out = format!(
        "{} vs {} head-to-head ({} matches in dataset):\n",
        h.team_a,
        h.team_b,
        h.matches.len()
    );
    for m in h.matches.iter().take(MAX_LINES) {
        out.push_str(&format!("- {}\n", m.summary()));
    }
    if h.matches.len() > MAX_LINES {
        out.push_str(&format!(
            "- ... ({} more in dataset)\n",
            h.matches.len() - MAX_LINES
        ));
    }
    out.push_str(&format!(
        "\nRecord: {} {} wins, {} {} wins, {} draws.",
        h.team_a, h.a_wins, h.team_b, h.b_wins, h.draws
    ));
    out
}

pub fn format_team_record(rec: &TeamRecord, scope: &str) -> String {
    if rec.matches == 0 {
        return format!("{} {}: no matches with results found.", rec.team, scope);
    }
    format!(
        "{} record {}:\n\
         - Matches: {}\n\
         - Wins: {}, Draws: {}, Losses: {}\n\
         - Goals For: {}, Goals Against: {} (GD: {:+})\n\
         - Points: {}\n\
         - Win rate: {:.1}%",
        rec.team,
        scope,
        rec.matches,
        rec.wins,
        rec.draws,
        rec.losses,
        rec.goals_for,
        rec.goals_against,
        rec.goal_difference(),
        rec.points(),
        rec.win_rate(),
    )
}

pub fn format_standings(rows: &[Standing], competition: &str, season: i32) -> String {
    if rows.is_empty() {
        return format!(
            "No {} matches found for season {} to calculate standings.",
            competition, season
        );
    }
    let mut out = format!(
        "{} {} Final Standings (calculated from matches):\n",
        season, competition
    );
    for (i, r) in rows.iter().enumerate() {
        let tag = if i == 0 { " - Champion" } else { "" };
        out.push_str(&format!(
            "{:>2}. {} - {} pts ({}W, {}D, {}L), GF {} GA {} (GD {:+}){}\n",
            i + 1,
            r.team,
            r.points(),
            r.wins,
            r.draws,
            r.losses,
            r.goals_for,
            r.goals_against,
            r.goal_difference(),
            tag,
        ));
    }
    out
}

pub fn format_players(title: &str, players: &[&Player]) -> String {
    if players.is_empty() {
        return format!("{}\nNo players found in the dataset.", title);
    }
    let mut out = format!("{} ({} found):\n", title, players.len());
    for (i, p) in players.iter().take(MAX_LINES).enumerate() {
        out.push_str(&format!("{}. {}\n", i + 1, p.summary()));
    }
    if players.len() > MAX_LINES {
        out.push_str(&format!(
            "... ({} more in dataset)\n",
            players.len() - MAX_LINES
        ));
    }
    out
}

pub fn format_player_detail(p: &Player) -> String {
    let mut out = format!("{}\n", p.name);
    out.push_str(&format!("- Nationality: {}\n", nz(&p.nationality)));
    out.push_str(&format!("- Club: {}\n", nz(&p.club)));
    out.push_str(&format!("- Position: {}\n", nz(&p.position)));
    if let Some(a) = p.age {
        out.push_str(&format!("- Age: {}\n", a));
    }
    if let Some(o) = p.overall {
        out.push_str(&format!("- Overall: {}\n", o));
    }
    if let Some(pot) = p.potential {
        out.push_str(&format!("- Potential: {}\n", pot));
    }
    if let Some(j) = &p.jersey_number {
        out.push_str(&format!("- Jersey: {}\n", j));
    }
    if !p.height.is_empty() || !p.weight.is_empty() {
        out.push_str(&format!("- Height/Weight: {} / {}\n", nz(&p.height), nz(&p.weight)));
    }
    out
}

pub fn format_club_aggregates(title: &str, aggs: &[ClubAggregate]) -> String {
    if aggs.is_empty() {
        return format!("{}\nNo clubs found.", title);
    }
    let mut out = format!("{}:\n", title);
    for a in aggs.iter().take(MAX_LINES) {
        out.push_str(&format!(
            "- {}: {} players (avg rating: {:.0})\n",
            a.club, a.count, a.avg_overall
        ));
    }
    out
}

pub fn format_stats(s: &CompetitionStats, scope: &str, biggest: &[&Match]) -> String {
    let mut out = format!("Statistics {} (from provided data):\n", scope);
    out.push_str(&format!("- Total matches: {}\n", s.total_matches));
    out.push_str(&format!("- Matches with scores: {}\n", s.matches_with_score));
    out.push_str(&format!("- Total goals: {}\n", s.total_goals));
    out.push_str(&format!(
        "- Average goals per match: {:.2}\n",
        s.avg_goals_per_match()
    ));
    out.push_str(&format!("- Home win rate: {:.1}%\n", s.home_win_rate()));
    out.push_str(&format!("- Away win rate: {:.1}%\n", s.away_win_rate()));
    out.push_str(&format!("- Draw rate: {:.1}%\n", s.draw_rate()));
    if !biggest.is_empty() {
        out.push_str("\nBiggest victories:\n");
        for (i, m) in biggest.iter().enumerate() {
            out.push_str(&format!("{}. {}\n", i + 1, m.summary()));
        }
    }
    out
}

fn nz(s: &str) -> &str {
    if s.trim().is_empty() {
        "unknown"
    } else {
        s
    }
}
