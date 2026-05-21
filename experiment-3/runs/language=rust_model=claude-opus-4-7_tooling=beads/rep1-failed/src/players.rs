//! FIFA player queries.
//!
//! Context: implements requirement category 3 ("Player Queries") from
//! `TASK.md` — searching the FIFA database by name, nationality, club and
//! position, plus rating filters. Positions can be queried either by exact
//! FIFA code (e.g. "ST") or by broad category ("forward", "defender").
//! Results are sorted by overall rating, highest first.

use crate::data::Database;
use crate::model::Player;
use crate::normalize::fold_accents;

/// Criteria for [`find_players`]. All set fields must be satisfied (AND).
#[derive(Debug, Default, Clone)]
pub struct PlayerFilter {
    pub name: Option<String>,
    pub nationality: Option<String>,
    pub club: Option<String>,
    pub position: Option<String>,
    pub min_overall: Option<i32>,
}

fn norm(s: &str) -> String {
    fold_accents(s).to_lowercase()
}

/// True when a player's FIFA position satisfies a position query, which may
/// be an exact code ("ST") or a category ("forward"/"midfielder"/...).
pub fn position_matches(player_pos: &str, query: &str) -> bool {
    let pos = player_pos.trim().to_uppercase();
    let q = query.trim().to_lowercase();
    if q.is_empty() {
        return true;
    }
    let category: &[&str] = match q.as_str() {
        "gk" | "goalkeeper" | "keeper" => &["GK"],
        "defender" | "defence" | "defense" | "back" => {
            &["CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB", "SW"]
        }
        "midfielder" | "midfield" | "mid" => &[
            "CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM",
        ],
        "forward" | "forwards" | "attacker" | "striker" | "attack" => {
            &["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"]
        }
        _ => &[],
    };
    if !category.is_empty() {
        return category.contains(&pos.as_str());
    }
    // Fall back to a direct (sub)string comparison on the FIFA code.
    pos == q.to_uppercase() || pos.contains(&q.to_uppercase())
}

/// Return every player satisfying `filter`, sorted by overall rating desc.
pub fn find_players<'a>(db: &'a Database, filter: &PlayerFilter) -> Vec<&'a Player> {
    let mut out: Vec<&Player> = db
        .players
        .iter()
        .filter(|p| matches_filter(p, filter))
        .collect();
    out.sort_by(|a, b| b.overall.cmp(&a.overall));
    out
}

fn matches_filter(p: &Player, f: &PlayerFilter) -> bool {
    if let Some(name) = &f.name {
        if !norm(&p.name).contains(&norm(name)) {
            return false;
        }
    }
    if let Some(nat) = &f.nationality {
        // "Brazilian" should match the nationality "Brazil".
        let n = norm(&p.nationality);
        let q = norm(nat);
        let q_root = q.trim_end_matches(|c| c == 'n' || c == 's').to_string();
        if !(n.contains(&q) || (!q_root.is_empty() && n.contains(&q_root))) {
            return false;
        }
    }
    if let Some(club) = &f.club {
        if !norm(&p.club).contains(&norm(club)) {
            return false;
        }
    }
    if let Some(pos) = &f.position {
        if !position_matches(&p.position, pos) {
            return false;
        }
    }
    if let Some(min) = f.min_overall {
        if p.overall.unwrap_or(0) < min {
            return false;
        }
    }
    true
}

/// Average overall rating across a slice of players (0.0 when empty).
pub fn avg_overall(players: &[&Player]) -> f64 {
    let rated: Vec<i32> = players.iter().filter_map(|p| p.overall).collect();
    if rated.is_empty() {
        0.0
    } else {
        rated.iter().sum::<i32>() as f64 / rated.len() as f64
    }
}

/// Render a numbered list of players, showing at most `limit` entries.
pub fn format_players(players: &[&Player], limit: usize) -> String {
    if players.is_empty() {
        return "No players found for the given criteria.".to_string();
    }
    let mut out = String::new();
    for (i, p) in players.iter().take(limit).enumerate() {
        let age = p.age.map(|a| format!(", age {a}")).unwrap_or_default();
        out.push_str(&format!(
            "{}. {} — Overall: {}, Potential: {}, Position: {}, Club: {}{age}\n",
            i + 1,
            p.name,
            p.overall.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
            p.potential
                .map(|v| v.to_string())
                .unwrap_or_else(|| "?".into()),
            if p.position.is_empty() {
                "?"
            } else {
                &p.position
            },
            if p.club.is_empty() {
                "(no club)"
            } else {
                &p.club
            },
        ));
    }
    if players.len() > limit {
        out.push_str(&format!(
            "... ({} more player(s) match)\n",
            players.len() - limit
        ));
    }
    out.push_str(&format!(
        "\nTotal matching players: {} (avg overall of shown: {:.0})",
        players.len(),
        avg_overall(&players.iter().take(limit).copied().collect::<Vec<_>>()),
    ));
    out
}
