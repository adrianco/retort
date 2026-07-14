//! League-table / standings calculation.
//!
//! Context: implements requirement category 4 ("Competition Queries") from
//! `TASK.md`. There are no standings in the source data, so a final table is
//! computed from match results using the standard 3-1-0 points system, then
//! ordered by points, goal difference, goals scored and finally name.

use std::collections::HashMap;

use crate::data::Database;
use crate::teams::TeamRecord;

/// One row of a computed league table.
pub struct StandingRow {
    pub team: String,
    pub key: String,
    pub record: TeamRecord,
}

/// Compute the final table for a competition and season from match results.
///
/// `competition` must be an exact canonical competition label (resolve free
/// text with [`crate::matches::canonical_competition`] first). The returned
/// rows are ranked best-first.
pub fn standings(db: &Database, competition: &str, season: i32) -> Vec<StandingRow> {
    let mut table: HashMap<String, (String, TeamRecord)> = HashMap::new();

    for m in &db.matches {
        if m.season != season || m.competition != competition {
            continue;
        }
        for (key, display) in [
            (&m.home_key, &m.home_team),
            (&m.away_key, &m.away_team),
        ] {
            table
                .entry(key.clone())
                .or_insert_with(|| (display.clone(), TeamRecord::default()));
        }
        if let Some(outcome) = m.outcome_for(&m.home_key) {
            table
                .get_mut(&m.home_key)
                .unwrap()
                .1
                .record_outcome(outcome, m.home_goal, m.away_goal);
        }
        if let Some(outcome) = m.outcome_for(&m.away_key) {
            table
                .get_mut(&m.away_key)
                .unwrap()
                .1
                .record_outcome(outcome, m.away_goal, m.home_goal);
        }
    }

    let mut rows: Vec<StandingRow> = table
        .into_iter()
        .map(|(key, (team, record))| StandingRow { team, key, record })
        .collect();

    rows.sort_by(|a, b| {
        b.record
            .points()
            .cmp(&a.record.points())
            .then(b.record.goal_diff().cmp(&a.record.goal_diff()))
            .then(b.record.goals_for.cmp(&a.record.goals_for))
            .then(a.team.to_lowercase().cmp(&b.team.to_lowercase()))
    });
    rows
}

/// Format a computed league table in the style of the `TASK.md` example.
///
/// When the table looks like a 20-team Série A season the champion and the
/// bottom-four relegation places are annotated.
pub fn format_standings(rows: &[StandingRow], competition: &str, season: i32) -> String {
    if rows.is_empty() {
        return format!(
            "No match data found for {competition} in {season}."
        );
    }
    let annotate_relegation = rows.len() == 20;
    let mut out = format!(
        "{} {} final standings (calculated from match results):\n",
        season, competition
    );
    for (i, row) in rows.iter().enumerate() {
        let r = &row.record;
        let mut line = format!(
            "{:>2}. {} - {} pts ({}W {}D {}L, GF {} GA {} GD {:+})",
            i + 1,
            row.team,
            r.points(),
            r.won,
            r.drawn,
            r.lost,
            r.goals_for,
            r.goals_against,
            r.goal_diff(),
        );
        if i == 0 {
            line.push_str("  — Champion");
        } else if annotate_relegation && i >= rows.len() - 4 {
            line.push_str("  — Relegated");
        }
        out.push_str(&line);
        out.push('\n');
    }
    out
}
