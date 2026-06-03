//! ============================================================================
//! Module: format
//! Project: Brazilian Soccer MCP Server (Rust)
//!
//! Context:
//!   Renders the structured query results from `store` into the human-readable
//!   text blocks shown in the specification's "Example answer format" sections.
//!   The MCP layer returns these strings as the textual content of each tool
//!   result so the connected LLM (and humans inspecting the protocol) get
//!   nicely formatted answers rather than raw JSON. Keeping all presentation
//!   here means `store` stays purely about data and is easy to unit-test.
//! ============================================================================

use crate::model::Match;
use crate::store::{GoalStats, HeadToHead, Store, Summary, TeamRecord};

/// Format a single match line, e.g.
/// `2023-09-03: Flamengo 2-1 Fluminense (Brasileirão, Round 22)`.
pub fn match_line(m: &Match) -> String {
    let when = if m.date.is_empty() { "unknown date" } else { &m.date };
    let extra = match &m.round {
        Some(r) => format!("{}, Round/Stage {}", m.competition.label(), r),
        None => m.competition.label().to_string(),
    };
    format!(
        "{}: {} {}-{} {} ({})",
        when, m.home_team_raw, m.home_goal, m.away_goal, m.away_team_raw, extra
    )
}

/// Render a list of matches with a header.
pub fn matches(title: &str, list: &[Match]) -> String {
    if list.is_empty() {
        return format!("{title}\nNo matches found in the dataset.");
    }
    let mut s = format!("{title} ({} match(es)):\n", list.len());
    for m in list {
        s.push_str("- ");
        s.push_str(&match_line(m));
        s.push('\n');
    }
    s.trim_end().to_string()
}

/// Render a head-to-head summary.
pub fn head_to_head(h: &HeadToHead) -> String {
    if h.total == 0 {
        return format!(
            "No matches between {} and {} found in the dataset.",
            h.team_a, h.team_b
        );
    }
    let mut s = format!(
        "Head-to-head: {} vs {} ({} matches in dataset)\n",
        h.team_a, h.team_b, h.total
    );
    s.push_str(&format!(
        "Record: {} {} wins, {} {} wins, {} draws\n",
        h.team_a, h.team_a_wins, h.team_b, h.team_b_wins, h.draws
    ));
    s.push_str(&format!(
        "Goals: {} {} - {} {}\n",
        h.team_a, h.team_a_goals, h.team_b_goals, h.team_b
    ));
    s.push_str("Recent matches:\n");
    for m in h.matches.iter().take(10) {
        s.push_str("- ");
        s.push_str(&match_line(m));
        s.push('\n');
    }
    if h.matches.len() > 10 {
        s.push_str(&format!("... ({} more)\n", h.matches.len() - 10));
    }
    s.trim_end().to_string()
}

/// Render a team record block.
pub fn team_record(rec: &TeamRecord, context: &str) -> String {
    if rec.matches == 0 {
        return format!("No matches found for {} ({context}).", rec.team);
    }
    format!(
        "{} record ({context}):\n- Matches: {}\n- Wins: {}, Draws: {}, Losses: {}\n- Goals For: {}, Goals Against: {} (GD {:+})\n- Points: {}\n- Win rate: {:.1}%",
        rec.team,
        rec.matches,
        rec.wins,
        rec.draws,
        rec.losses,
        rec.goals_for,
        rec.goals_against,
        rec.goal_difference(),
        rec.points,
        rec.win_rate(),
    )
}

/// Render computed standings.
pub fn standings(title: &str, rows: &[TeamRecord]) -> String {
    if rows.is_empty() {
        return format!("{title}\nNo data available for that season/competition.");
    }
    let mut s = format!("{title}\n");
    for (i, r) in rows.iter().enumerate() {
        s.push_str(&format!(
            "{:>2}. {} - {} pts ({}W, {}D, {}L) GF {} GA {} (GD {:+})\n",
            i + 1,
            r.team,
            r.points,
            r.wins,
            r.draws,
            r.losses,
            r.goals_for,
            r.goals_against,
            r.goal_difference(),
        ));
    }
    s.trim_end().to_string()
}

/// Render goal statistics.
pub fn goal_stats(title: &str, g: &GoalStats) -> String {
    if g.matches == 0 {
        return format!("{title}\nNo matches found for the given filters.");
    }
    format!(
        "{title}\n- Matches: {}\n- Total goals: {}\n- Average goals per match: {:.2}\n- Home wins: {} ({:.1}%), Away wins: {}, Draws: {}",
        g.matches, g.total_goals, g.avg_goals_per_match, g.home_wins, g.home_win_rate, g.away_wins, g.draws
    )
}

/// Render a players list.
pub fn players(title: &str, list: &[crate::model::Player]) -> String {
    if list.is_empty() {
        return format!("{title}\nNo players found.");
    }
    let mut s = format!("{title} ({} player(s)):\n", list.len());
    for (i, p) in list.iter().enumerate() {
        let club = if p.club.is_empty() { "Free agent" } else { &p.club };
        s.push_str(&format!(
            "{:>2}. {} - Overall: {}, Position: {}, Club: {}, Nationality: {}\n",
            i + 1,
            p.name,
            p.overall,
            p.position,
            club,
            p.nationality,
        ));
    }
    s.trim_end().to_string()
}

/// Render the data summary.
pub fn summary(s: &Summary) -> String {
    let mut out = String::from("Brazilian Soccer dataset summary:\n");
    out.push_str(&format!("- Total matches: {}\n", s.total_matches));
    out.push_str(&format!("- Total players: {}\n", s.total_players));
    if let (Some(min), Some(max)) = (s.seasons_min, s.seasons_max) {
        out.push_str(&format!("- Seasons covered: {min}-{max}\n"));
    }
    out.push_str("- Matches by source:\n");
    for (src, n) in &s.matches_by_source {
        out.push_str(&format!("  - {src}: {n}\n"));
    }
    out.trim_end().to_string()
}

/// Convenience: a one-line description of the loaded store (used at startup).
pub fn store_banner(store: &Store) -> String {
    summary(&store.summary())
}
