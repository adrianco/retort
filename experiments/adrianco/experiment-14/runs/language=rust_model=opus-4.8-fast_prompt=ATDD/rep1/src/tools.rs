//! Query tools — the public capabilities exposed over MCP.
//!
//! Each function takes the loaded `DataStore` and the JSON `arguments` an MCP
//! client passed, and returns a `ToolOutput` carrying both a human-readable
//! text rendering and a machine-readable `structured` JSON payload.

use serde_json::{json, Value};

use crate::data::DataStore;
use crate::model::Match;
use crate::normalize::{self, canonical_competition_query};
use crate::teams;

pub struct ToolOutput {
    pub text: String,
    pub structured: Value,
}

type ToolResult = Result<ToolOutput, String>;

fn arg_str<'a>(args: &'a Value, key: &str) -> Option<&'a str> {
    args.get(key).and_then(|v| v.as_str()).filter(|s| !s.trim().is_empty())
}

fn arg_i64(args: &Value, key: &str) -> Option<i64> {
    match args.get(key) {
        Some(Value::Number(n)) => n.as_i64(),
        Some(Value::String(s)) => s.trim().parse().ok(),
        _ => None,
    }
}

/// Filter helper: does a match pass an optional competition filter?
fn competition_ok(m: &Match, comp_query: Option<&str>) -> bool {
    match comp_query {
        None => true,
        Some(q) => match canonical_competition_query(q) {
            Some(canon) => m.competition == canon,
            None => normalize::fold(&m.competition) == normalize::fold(q),
        },
    }
}

fn match_json(m: &Match) -> Value {
    let mut v = json!({
        "date": m.date,
        "competition": m.competition,
        "season": m.season,
        "home_team": m.home_display,
        "away_team": m.away_display,
        "home_goal": m.home_goal,
        "away_goal": m.away_goal,
    });
    if let Some(r) = &m.round {
        v["round"] = json!(r);
    }
    if let Some(s) = &m.stage {
        v["stage"] = json!(s);
    }
    v
}

fn score_line(m: &Match) -> String {
    let when = if m.date.is_empty() { "????-??-??" } else { &m.date };
    let extra = m
        .round
        .as_ref()
        .map(|r| format!(" Round {r}"))
        .or_else(|| m.stage.as_ref().map(|s| format!(" {s}")))
        .unwrap_or_default();
    format!(
        "{when}: {} {}-{} {} ({}{})",
        m.home_display, m.home_goal, m.away_goal, m.away_display, m.competition, extra
    )
}

// ---------------------------------------------------------------------------

pub fn search_matches(store: &DataStore, args: &Value) -> ToolResult {
    let team = arg_str(args, "team");
    let opponent = arg_str(args, "opponent");
    let home_team = arg_str(args, "home_team");
    let away_team = arg_str(args, "away_team");
    let competition = arg_str(args, "competition");
    let season = arg_i64(args, "season");
    let start_date = arg_str(args, "start_date");
    let end_date = arg_str(args, "end_date");
    let limit = arg_i64(args, "limit").unwrap_or(50).max(1) as usize;

    let mut filtered: Vec<&Match> = store
        .matches
        .iter()
        .filter(|m| competition_ok(m, competition))
        .filter(|m| season.map_or(true, |s| m.season as i64 == s))
        .filter(|m| match (team, opponent) {
            (Some(t), Some(o)) => {
                (teams::query_matches(t, &m.home_key)
                    && teams::query_matches(o, &m.away_key))
                    || (teams::query_matches(t, &m.away_key)
                        && teams::query_matches(o, &m.home_key))
            }
            (Some(t), None) => m.involves(t),
            (None, Some(o)) => m.involves(o),
            (None, None) => true,
        })
        .filter(|m| home_team.map_or(true, |t| teams::query_matches(t, &m.home_key)))
        .filter(|m| away_team.map_or(true, |t| teams::query_matches(t, &m.away_key)))
        .filter(|m| start_date.map_or(true, |d| !m.date.is_empty() && m.date.as_str() >= d))
        .filter(|m| end_date.map_or(true, |d| !m.date.is_empty() && m.date.as_str() <= d))
        .collect();

    // Most recent first.
    filtered.sort_by(|a, b| b.date.cmp(&a.date));
    let total = filtered.len();
    let shown: Vec<&Match> = filtered.into_iter().take(limit).collect();

    let mut structured = json!({
        "count": total,
        "matches": shown.iter().map(|m| match_json(m)).collect::<Vec<_>>(),
    });

    let mut text = String::new();
    // Head-to-head summary when exactly two teams are named.
    if let (Some(t), Some(o)) = (team, opponent) {
        let (mut a_wins, mut b_wins, mut draws) = (0i64, 0i64, 0i64);
        // Tally over the full filtered set, not just the shown page.
        for m in store
            .matches
            .iter()
            .filter(|m| competition_ok(m, competition))
            .filter(|m| season.map_or(true, |s| m.season as i64 == s))
            .filter(|m| {
                (teams::query_matches(t, &m.home_key)
                    && teams::query_matches(o, &m.away_key))
                    || (teams::query_matches(t, &m.away_key)
                        && teams::query_matches(o, &m.home_key))
            })
            .filter(|m| start_date.map_or(true, |d| !m.date.is_empty() && m.date.as_str() >= d))
            .filter(|m| end_date.map_or(true, |d| !m.date.is_empty() && m.date.as_str() <= d))
        {
            let (a_goal, b_goal) = if teams::query_matches(t, &m.home_key) {
                (m.home_goal, m.away_goal)
            } else {
                (m.away_goal, m.home_goal)
            };
            match a_goal.cmp(&b_goal) {
                std::cmp::Ordering::Greater => a_wins += 1,
                std::cmp::Ordering::Less => b_wins += 1,
                std::cmp::Ordering::Equal => draws += 1,
            }
        }
        structured["head_to_head"] = json!({
            "team_a": teams::display(t),
            "team_b": teams::display(o),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
        });
        text.push_str(&format!(
            "{} vs {} — {} matches (head-to-head: {} {}, {} {}, {} draws)\n",
            teams::display(t),
            teams::display(o),
            total,
            teams::display(t),
            a_wins,
            teams::display(o),
            b_wins,
            draws
        ));
    } else {
        text.push_str(&format!("Found {total} matches\n"));
    }
    for m in &shown {
        text.push_str(&format!("- {}\n", score_line(m)));
    }
    if total > shown.len() {
        text.push_str(&format!("... ({} more not shown)\n", total - shown.len()));
    }

    Ok(ToolOutput { text, structured })
}

// ---------------------------------------------------------------------------

pub fn team_record(store: &DataStore, args: &Value) -> ToolResult {
    let team = arg_str(args, "team").ok_or("a 'team' name is required")?;
    let competition = arg_str(args, "competition");
    let season = arg_i64(args, "season");
    let venue = arg_str(args, "venue").unwrap_or("all");

    let (mut matches, mut wins, mut draws, mut losses, mut gf, mut ga) = (0i64, 0i64, 0i64, 0i64, 0i64, 0i64);

    for m in store
        .matches
        .iter()
        .filter(|m| competition_ok(m, competition))
        .filter(|m| season.map_or(true, |s| m.season as i64 == s))
    {
        let is_home = teams::query_matches(team, &m.home_key);
        let is_away = teams::query_matches(team, &m.away_key);
        let counts = match venue {
            "home" => is_home,
            "away" => is_away,
            _ => is_home || is_away,
        };
        if !counts {
            continue;
        }
        // If the same query matches both sides (a derby search would not happen
        // here since it is one team), prefer home.
        let (for_goals, against_goals) = if is_home {
            (m.home_goal, m.away_goal)
        } else {
            (m.away_goal, m.home_goal)
        };
        matches += 1;
        gf += for_goals as i64;
        ga += against_goals as i64;
        match for_goals.cmp(&against_goals) {
            std::cmp::Ordering::Greater => wins += 1,
            std::cmp::Ordering::Less => losses += 1,
            std::cmp::Ordering::Equal => draws += 1,
        }
    }

    if matches == 0 {
        return Err(format!("no matches found for team '{team}' with the given filters"));
    }

    let points = wins * 3 + draws;
    let win_rate = wins as f64 / matches as f64;
    let display = teams::display(team);

    let structured = json!({
        "team": display,
        "competition": competition.and_then(canonical_competition_query).map(|c| c.to_string()),
        "season": season,
        "venue": venue,
        "matches": matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "points": points,
        "win_rate": (win_rate * 1000.0).round() / 1000.0,
    });

    let text = format!(
        "{display} record{}{}{}:\n- Matches: {matches}\n- Wins: {wins}, Draws: {draws}, Losses: {losses}\n- Goals For: {gf}, Goals Against: {ga}\n- Points: {points}\n- Win rate: {:.1}%",
        season.map(|s| format!(" ({s})")).unwrap_or_default(),
        competition.map(|c| format!(" {c}")).unwrap_or_default(),
        if venue != "all" { format!(" [{venue}]") } else { String::new() },
        win_rate * 100.0
    );

    Ok(ToolOutput { text, structured })
}

// ---------------------------------------------------------------------------

pub fn head_to_head(store: &DataStore, args: &Value) -> ToolResult {
    let a = arg_str(args, "team_a").ok_or("'team_a' is required")?;
    let b = arg_str(args, "team_b").ok_or("'team_b' is required")?;
    let competition = arg_str(args, "competition");

    let mut meetings: Vec<&Match> = store
        .matches
        .iter()
        .filter(|m| competition_ok(m, competition))
        .filter(|m| {
            (teams::query_matches(a, &m.home_key)
                && teams::query_matches(b, &m.away_key))
                || (teams::query_matches(a, &m.away_key)
                    && teams::query_matches(b, &m.home_key))
        })
        .collect();
    meetings.sort_by(|x, y| y.date.cmp(&x.date));

    if meetings.is_empty() {
        return Err(format!("no matches found between '{a}' and '{b}'"));
    }

    let (mut a_wins, mut b_wins, mut draws, mut a_goals, mut b_goals) = (0i64, 0i64, 0i64, 0i64, 0i64);
    for m in &meetings {
        let (ag, bg) = if teams::query_matches(a, &m.home_key) {
            (m.home_goal, m.away_goal)
        } else {
            (m.away_goal, m.home_goal)
        };
        a_goals += ag as i64;
        b_goals += bg as i64;
        match ag.cmp(&bg) {
            std::cmp::Ordering::Greater => a_wins += 1,
            std::cmp::Ordering::Less => b_wins += 1,
            std::cmp::Ordering::Equal => draws += 1,
        }
    }

    let (da, db) = (teams::display(a), teams::display(b));
    let structured = json!({
        "team_a": da,
        "team_b": db,
        "total_matches": meetings.len(),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_goals,
        "team_b_goals": b_goals,
        "matches": meetings.iter().map(|m| match_json(m)).collect::<Vec<_>>(),
    });

    let mut text = format!(
        "{da} vs {db}: {} meetings\nHead-to-head: {da} {a_wins} wins, {db} {b_wins} wins, {draws} draws\n",
        meetings.len()
    );
    for m in meetings.iter().take(20) {
        text.push_str(&format!("- {}\n", score_line(m)));
    }
    Ok(ToolOutput { text, structured })
}

// ---------------------------------------------------------------------------

pub fn search_players(store: &DataStore, args: &Value) -> ToolResult {
    let name = arg_str(args, "name").map(normalize::fold);
    let nationality = arg_str(args, "nationality").map(normalize::fold);
    let club = arg_str(args, "club").map(normalize::fold);
    let position = arg_str(args, "position").map(normalize::fold);
    let min_overall = arg_i64(args, "min_overall");
    let sort_by = arg_str(args, "sort_by").unwrap_or("overall");
    let limit = arg_i64(args, "limit").unwrap_or(25).max(1) as usize;

    let mut found: Vec<&crate::model::Player> = store
        .players
        .iter()
        .filter(|p| name.as_ref().map_or(true, |n| normalize::fold(&p.name).contains(n)))
        .filter(|p| nationality.as_ref().map_or(true, |n| normalize::fold(&p.nationality) == *n))
        .filter(|p| club.as_ref().map_or(true, |c| normalize::fold(&p.club).contains(c)))
        .filter(|p| position.as_ref().map_or(true, |pos| normalize::fold(&p.position).contains(pos)))
        .filter(|p| min_overall.map_or(true, |m| p.overall as i64 >= m))
        .collect();

    found.sort_by(|a, b| match sort_by {
        "potential" => b.potential.cmp(&a.potential),
        "age" => b.age.cmp(&a.age),
        _ => b.overall.cmp(&a.overall),
    });

    let total = found.len();
    let shown: Vec<&crate::model::Player> = found.into_iter().take(limit).collect();

    let players_json: Vec<Value> = shown
        .iter()
        .map(|p| {
            json!({
                "name": p.name,
                "age": p.age,
                "nationality": p.nationality,
                "overall": p.overall,
                "potential": p.potential,
                "club": p.club,
                "position": p.position,
                "jersey_number": p.jersey_number,
                "height": p.height,
                "weight": p.weight,
            })
        })
        .collect();

    let structured = json!({ "count": total, "players": players_json });

    let mut text = format!("Found {total} players (showing {}):\n", shown.len());
    for (i, p) in shown.iter().enumerate() {
        text.push_str(&format!(
            "{}. {} - Overall: {}, Position: {}, Club: {}\n",
            i + 1,
            p.name,
            p.overall,
            p.position,
            p.club
        ));
    }
    Ok(ToolOutput { text, structured })
}

// ---------------------------------------------------------------------------

struct Row {
    team: String,
    played: i64,
    wins: i64,
    draws: i64,
    losses: i64,
    gf: i64,
    ga: i64,
}

pub fn league_standings(store: &DataStore, args: &Value) -> ToolResult {
    let competition = arg_str(args, "competition").unwrap_or("Brasileirão");
    let season = arg_i64(args, "season").ok_or("a 'season' is required")?;
    let canon = canonical_competition_query(competition).unwrap_or(competition);

    use std::collections::HashMap;
    let mut table: HashMap<String, Row> = HashMap::new();
    let mut display: HashMap<String, String> = HashMap::new();

    for m in store
        .matches
        .iter()
        .filter(|m| m.competition == canon && m.season as i64 == season)
    {
        display.entry(m.home_key.clone()).or_insert_with(|| m.home_display.clone());
        display.entry(m.away_key.clone()).or_insert_with(|| m.away_display.clone());

        let home = table.entry(m.home_key.clone()).or_insert(Row {
            team: m.home_display.clone(),
            played: 0,
            wins: 0,
            draws: 0,
            losses: 0,
            gf: 0,
            ga: 0,
        });
        home.played += 1;
        home.gf += m.home_goal as i64;
        home.ga += m.away_goal as i64;
        match m.home_goal.cmp(&m.away_goal) {
            std::cmp::Ordering::Greater => home.wins += 1,
            std::cmp::Ordering::Less => home.losses += 1,
            std::cmp::Ordering::Equal => home.draws += 1,
        }

        let away = table.entry(m.away_key.clone()).or_insert(Row {
            team: m.away_display.clone(),
            played: 0,
            wins: 0,
            draws: 0,
            losses: 0,
            gf: 0,
            ga: 0,
        });
        away.played += 1;
        away.gf += m.away_goal as i64;
        away.ga += m.home_goal as i64;
        match m.away_goal.cmp(&m.home_goal) {
            std::cmp::Ordering::Greater => away.wins += 1,
            std::cmp::Ordering::Less => away.losses += 1,
            std::cmp::Ordering::Equal => away.draws += 1,
        }
    }

    if table.is_empty() {
        return Err(format!("no matches found for {canon} in {season}"));
    }

    let mut rows: Vec<Row> = table.into_values().collect();
    rows.sort_by(|a, b| {
        let pa = a.wins * 3 + a.draws;
        let pb = b.wins * 3 + b.draws;
        pb.cmp(&pa)
            .then((b.gf - b.ga).cmp(&(a.gf - a.ga)))
            .then(b.gf.cmp(&a.gf))
            .then(a.team.cmp(&b.team))
    });

    let standings: Vec<Value> = rows
        .iter()
        .enumerate()
        .map(|(i, r)| {
            json!({
                "rank": i + 1,
                "team": r.team,
                "points": r.wins * 3 + r.draws,
                "played": r.played,
                "wins": r.wins,
                "draws": r.draws,
                "losses": r.losses,
                "goals_for": r.gf,
                "goals_against": r.ga,
                "goal_difference": r.gf - r.ga,
            })
        })
        .collect();

    let mut text = format!("{canon} {season} final standings:\n");
    for row in &standings {
        text.push_str(&format!(
            "{}. {} - {} pts ({}W {}D {}L, GD {})\n",
            row["rank"], row["team"], row["points"], row["wins"], row["draws"], row["losses"], row["goal_difference"]
        ));
    }

    let structured = json!({
        "competition": canon,
        "season": season,
        "standings": standings,
    });
    Ok(ToolOutput { text, structured })
}

// ---------------------------------------------------------------------------

pub fn competition_stats(store: &DataStore, args: &Value) -> ToolResult {
    let competition = arg_str(args, "competition");
    let season = arg_i64(args, "season");

    let selected: Vec<&Match> = store
        .matches
        .iter()
        .filter(|m| competition_ok(m, competition))
        .filter(|m| season.map_or(true, |s| m.season as i64 == s))
        .collect();

    if selected.is_empty() {
        return Err("no matches found for the given filters".to_string());
    }

    let n = selected.len() as i64;
    let total_goals: i64 = selected.iter().map(|m| (m.home_goal + m.away_goal) as i64).sum();
    let home_wins = selected.iter().filter(|m| m.home_goal > m.away_goal).count() as i64;
    let away_wins = selected.iter().filter(|m| m.away_goal > m.home_goal).count() as i64;
    let draws = n - home_wins - away_wins;

    let mut biggest: Vec<&Match> = selected.clone();
    biggest.sort_by(|a, b| {
        let ma = (a.home_goal - a.away_goal).abs();
        let mb = (b.home_goal - b.away_goal).abs();
        mb.cmp(&ma).then(b.date.cmp(&a.date))
    });
    let biggest_wins: Vec<Value> = biggest
        .iter()
        .filter(|m| m.home_goal != m.away_goal)
        .take(10)
        .map(|m| {
            let mut v = match_json(m);
            v["margin"] = json!((m.home_goal - m.away_goal).abs());
            v
        })
        .collect();

    let scope = match (competition.and_then(canonical_competition_query), season) {
        (Some(c), Some(s)) => format!("{c} {s}"),
        (Some(c), None) => c.to_string(),
        (None, Some(s)) => format!("all competitions {s}"),
        (None, None) => "all competitions".to_string(),
    };

    let avg = total_goals as f64 / n as f64;
    let home_win_rate = home_wins as f64 / n as f64;

    let structured = json!({
        "scope": scope,
        "matches": n,
        "total_goals": total_goals,
        "avg_goals_per_match": (avg * 100.0).round() / 100.0,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": (home_win_rate * 1000.0).round() / 1000.0,
        "biggest_wins": biggest_wins,
    });

    let mut text = format!(
        "{scope} statistics:\n- Matches: {n}\n- Average goals per match: {:.2}\n- Home win rate: {:.1}%\n- Home {home_wins} / Draws {draws} / Away {away_wins}\nBiggest wins:\n",
        avg,
        home_win_rate * 100.0
    );
    for w in biggest_wins.iter().take(5) {
        text.push_str(&format!(
            "- {}: {} {}-{} {}\n",
            w["date"], w["home_team"], w["home_goal"], w["away_goal"], w["away_team"]
        ));
    }
    Ok(ToolOutput { text, structured })
}

// ---------------------------------------------------------------------------

pub fn list_competitions(store: &DataStore, _args: &Value) -> ToolResult {
    use std::collections::HashMap;
    let mut agg: HashMap<String, (i64, i32, i32)> = HashMap::new(); // name -> (count, min_season, max_season)
    for m in &store.matches {
        let e = agg.entry(m.competition.clone()).or_insert((0, i32::MAX, i32::MIN));
        e.0 += 1;
        if m.season > 0 {
            e.1 = e.1.min(m.season);
            e.2 = e.2.max(m.season);
        }
    }
    let mut comps: Vec<Value> = agg
        .iter()
        .map(|(name, (count, lo, hi))| {
            json!({
                "name": name,
                "matches": count,
                "first_season": if *lo == i32::MAX { Value::Null } else { json!(lo) },
                "last_season": if *hi == i32::MIN { Value::Null } else { json!(hi) },
            })
        })
        .collect();
    comps.sort_by(|a, b| b["matches"].as_i64().cmp(&a["matches"].as_i64()));

    let total: i64 = store.matches.len() as i64;
    let mut text = format!("{} competitions, {total} matches total:\n", comps.len());
    for c in &comps {
        text.push_str(&format!("- {} ({} matches)\n", c["name"], c["matches"]));
    }
    let structured = json!({ "competitions": comps, "total_matches": total });
    Ok(ToolOutput { text, structured })
}
