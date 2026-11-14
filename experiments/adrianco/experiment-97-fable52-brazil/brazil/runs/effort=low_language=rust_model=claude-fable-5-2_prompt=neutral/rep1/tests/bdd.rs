//! BDD-style (Given / When / Then) scenarios run against the real Kaggle datasets.
use brazilian_soccer_mcp::data::{Competition, Db, Source};
use brazilian_soccer_mcp::mcp::{call_tool, handle_message, tool_definitions};
use brazilian_soccer_mcp::queries::{Filter, PlayerQuery, Venue};
use serde_json::{json, Value};
use std::path::Path;
use std::sync::OnceLock;
use std::time::Instant;

/// Given the match and player data is loaded
fn db() -> &'static Db {
    static DB: OnceLock<Db> = OnceLock::new();
    DB.get_or_init(|| {
        Db::load(&Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle")).expect("datasets load")
    })
}

fn ask(tool: &str, args: Value) -> String {
    call_tool(db(), tool, &args).unwrap_or_else(|e| panic!("{tool} failed: {e}"))
}

fn team(name: &str) -> Option<std::collections::HashSet<String>> {
    Some(db().resolve_team(name).unwrap())
}

// ---------------------------------------------------------------- data coverage

#[test]
fn scenario_all_six_csv_files_are_loaded() {
    // Given the data directory with the six Kaggle files
    let db = db();
    // Then every file contributed rows
    for f in [
        "Brasileirao_Matches.csv",
        "Brazilian_Cup_Matches.csv",
        "Libertadores_Matches.csv",
        "BR-Football-Dataset.csv",
        "novo_campeonato_brasileiro.csv",
        "fifa_data.csv",
    ] {
        assert!(db.loaded.get(f).copied().unwrap_or(0) > 1000, "{f} not loaded");
    }
    assert_eq!(db.loaded["BR-Football-Dataset.csv"], 10296);
    assert_eq!(db.loaded["novo_campeonato_brasileiro.csv"], 6886);
    assert_eq!(db.loaded["fifa_data.csv"], 18207);
    // And every source file is queryable through the match list
    for s in [Source::BrasileiraoMatches, Source::NovoCampeonato, Source::CupMatches, Source::LibertadoresMatches, Source::BrFootball] {
        assert!(db.matches.iter().any(|m| m.source == s && !m.duplicate), "{s:?}");
    }
}

#[test]
fn scenario_overlapping_files_do_not_double_count_matches() {
    // Given Serie A 2012-2019 appears in three of the files
    // When I count unique Serie A matches per season
    for season in [2006, 2012, 2014, 2017, 2019, 2020, 2021, 2022] {
        let n = db().season_matches(Competition::SerieA, season).len();
        // Then each 20-team season has exactly 380 matches
        assert_eq!(n, 380, "season {season}");
    }
}

#[test]
fn scenario_dates_are_normalised_to_iso() {
    // Given files with ISO, Brazilian and timestamp date formats
    // Then every loaded match has an ISO date
    for m in &db().matches {
        assert_eq!(m.date.len(), 10, "{:?}", m.date);
        assert_eq!(&m.date[4..5], "-");
    }
    // And the first 2003 match (29/03/2003 in the file) is found by ISO date range
    let out = ask("search_matches", json!({"team": "Guarani", "date_from": "2003-03-29", "date_to": "29/03/2003"}));
    assert!(out.contains("2003-03-29: Guarani 4-2 Vasco"), "{out}");
}

// ---------------------------------------------------------------- match queries

#[test]
fn scenario_find_matches_between_two_teams() {
    // When I search for matches between "Flamengo" and "Fluminense"
    let f = Filter { team: team("Flamengo"), opponent: team("Fluminense"), ..Default::default() };
    let ms = db().find_matches(&f);
    // Then I should receive a list of matches
    assert!(ms.len() >= 30, "only {} Fla-Flu matches", ms.len());
    // And each match should have date, scores, and competition
    for m in &ms {
        assert!(!m.date.is_empty());
        let keys = [m.home_key.as_str(), m.away_key.as_str()];
        assert!(keys.contains(&"flamengo") && keys.contains(&"fluminense"));
        assert!(!m.competition.name().is_empty());
    }
    // And the formatted answer has a head-to-head summary
    let out = ask("search_matches", json!({"team": "Flamengo", "opponent": "Fluminense"}));
    assert!(out.contains("Head-to-head in dataset: Flamengo"), "{out}");
    assert!(out.contains("more matches in dataset"));
}

#[test]
fn scenario_matches_by_team_and_season() {
    // When I ask "What matches did Palmeiras play in 2023?"
    let out = ask("search_matches", json!({"team": "Palmeiras", "season": 2023, "limit": 100}));
    // Then all listed matches involve Palmeiras in 2023
    let lines: Vec<&str> = out.lines().filter(|l| l.starts_with("- 2")).collect();
    assert!(lines.len() >= 38, "{out}");
    assert!(lines.iter().all(|l| l.contains("Palmeiras") && l.starts_with("- 2023")));
}

#[test]
fn scenario_matches_by_competition_stage_and_venue() {
    // When I ask for all Copa do Brasil finals
    let out = ask("search_matches", json!({"competition": "Copa do Brasil", "stage": "final", "limit": 50}));
    // Then the 2019 final (Athletico-PR beat Internacional) is included and no semifinal is
    assert!(out.contains("2019-09-18: Internacional 1-2 Athletico-PR (Copa do Brasil, Final)"), "{out}");
    assert!(!out.contains("Semifinals"));
    // When I restrict a team to home matches in the Libertadores
    let f = Filter { team: team("Grêmio"), venue: Venue::Home, competition: Some(Competition::Libertadores), ..Default::default() };
    let ms = db().find_matches(&f);
    // Then every match is a Grêmio home Libertadores match
    assert!(!ms.is_empty());
    assert!(ms.iter().all(|m| m.home_key == "gremio" && m.competition == Competition::Libertadores));
}

#[test]
fn scenario_last_meeting_and_score() {
    // When I ask "When did Flamengo last play Corinthians?" / "What was the score?"
    let out = ask("search_matches", json!({"team": "Flamengo", "opponent": "Corinthians", "limit": 1}));
    let first = out.lines().find(|l| l.starts_with("- 2")).unwrap();
    // Then the most recent match with its score is returned first
    let f = Filter { team: team("Flamengo"), opponent: team("Corinthians"), ..Default::default() };
    let latest = db().find_matches(&f).iter().map(|m| m.date.clone()).max().unwrap();
    assert!(first.contains(&latest), "{first} vs {latest}");
    assert!(first.contains(&format!("{}-", db().find_matches(&f)[0].home_goals)));
}

// ---------------------------------------------------------------- team queries

#[test]
fn scenario_get_team_statistics_for_a_season() {
    // When I request statistics for "Palmeiras" in season "2019"
    let f = Filter { team: team("Palmeiras"), season: Some(2019), competition: Some(Competition::SerieA), ..Default::default() };
    let r = db().record(&db().find_matches(&f), f.team.as_ref().unwrap(), Venue::Either);
    // Then I should receive wins, losses, draws, and goals (official 2019 numbers)
    assert_eq!((r.played, r.wins, r.draws, r.losses), (38, 21, 11, 6));
    assert_eq!((r.goals_for, r.goals_against), (61, 32));
}

#[test]
fn scenario_home_record() {
    // When I ask "What is Corinthians' home record in 2022?"
    let out = ask("team_stats", json!({"team": "Corinthians", "season": 2022, "venue": "home", "competition": "Brasileirão"}));
    // Then the answer follows the specified format
    assert!(out.starts_with("Corinthians home record (2022, Brasileirão Série A):"), "{out}");
    assert!(out.contains("- Matches: 19"));
    assert!(out.contains("- Wins: ") && out.contains("Draws: ") && out.contains("Losses: "));
    assert!(out.contains("- Goals For: ") && out.contains("Goals Against: "));
    assert!(out.contains("- Win rate: ") && out.contains('%'));
}

#[test]
fn scenario_compare_teams_head_to_head() {
    // When I ask "Compare Palmeiras and Santos head-to-head"
    let out = ask("head_to_head", json!({"team_a": "Palmeiras", "team_b": "Santos"}));
    // Then wins for each side, draws and goals are reported and add up
    assert!(out.contains("Palmeiras vs Santos"), "{out}");
    let f = Filter { team: team("Palmeiras"), opponent: team("Santos"), ..Default::default() };
    let ms = db().find_matches(&f);
    let a = db().record(&ms, f.team.as_ref().unwrap(), Venue::Either);
    let b = db().record(&ms, f.opponent.as_ref().unwrap(), Venue::Either);
    assert_eq!(a.played as usize, ms.len());
    assert_eq!((a.wins, a.draws, a.losses), (b.losses, b.draws, b.wins));
    assert_eq!(a.goals_for, b.goals_against);
    assert!(out.contains(&format!("Palmeiras wins: {}, Santos wins: {}, Draws: {}", a.wins, b.wins, a.draws)));
}

#[test]
fn scenario_team_name_variations_resolve_to_the_same_team() {
    // Given the datasets spell teams differently
    // When I query the same club under several names
    let variants = ["São Paulo", "Sao Paulo", "Sao Paulo-SP", "São Paulo - SP", "São Paulo FC", "sao paulo"];
    let counts: Vec<usize> = variants
        .iter()
        .map(|v| db().find_matches(&Filter { team: team(v), ..Default::default() }).len())
        .collect();
    // Then all return the same matches
    assert!(counts[0] > 500);
    assert!(counts.iter().all(|c| *c == counts[0]), "{counts:?}");
    // And accented / suffixed names from different files are merged
    assert_eq!(team("Grêmio"), team("Gremio-RS"));
    assert_eq!(team("Athletico Paranaense"), team("Atlético - PR"));
    assert_eq!(team("Vasco"), team("Vasco da Gama - RJ"));
    // And same-named clubs from different states stay separate
    assert_ne!(team("Atlético-MG"), team("Atlético-GO"));
    assert_ne!(team("Santos"), team("Santos - AP"));
    // And display names keep their UTF-8 accents
    assert_eq!(db().name("sao paulo"), "São Paulo");
    assert_eq!(db().name("gremio"), "Grêmio");
    // And an unknown team is a clear error
    assert!(db().resolve_team("Nonexistent United").is_err());
}

#[test]
fn scenario_team_competitions_across_files() {
    // When I ask "What competitions has Palmeiras played in?"
    let out = ask("team_competitions", json!({"team": "Palmeiras"}));
    // Then all three competitions (from different files) are listed
    for c in ["Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"] {
        assert!(out.contains(c), "{out}");
    }
}

// ---------------------------------------------------------------- competitions

#[test]
fn scenario_who_won_the_2019_brasileirao() {
    // When I compute the 2019 standings from match results
    let t = db().standings(Competition::SerieA, 2019);
    // Then they match the official table from the specification
    assert_eq!(t.len(), 20);
    let row = |i: usize| (db().name(&t[i].0).to_string(), t[i].1.points(), t[i].1.wins, t[i].1.draws, t[i].1.losses);
    assert_eq!(row(0), ("Flamengo".into(), 90, 28, 6, 4));
    assert_eq!(row(1), ("Santos".into(), 74, 22, 8, 8));
    assert_eq!(row(2), ("Palmeiras".into(), 74, 21, 11, 6));
    let out = ask("standings", json!({"season": 2019}));
    assert!(out.contains("1. Flamengo - 90 pts (28W, 6D, 4L)") && out.contains("Champion"), "{out}");
}

#[test]
fn scenario_champions_across_all_sources() {
    // Then historical champions are reproduced from each source file
    for (season, champion) in [(2003, "Cruzeiro"), (2005, "Corinthians"), (2011, "Corinthians"), (2015, "Corinthians"), (2018, "Palmeiras"), (2020, "Flamengo"), (2021, "Atlético-MG"), (2022, "Palmeiras")] {
        let t = db().standings(Competition::SerieA, season);
        assert_eq!(db().name(&t[0].0), champion, "season {season}");
    }
}

#[test]
fn scenario_relegated_teams() {
    // When I ask "Which teams were relegated in 2020?"
    let out = ask("standings", json!({"season": 2020, "competition": "Brasileirão"}));
    // Then the bottom four are flagged
    let relegated: Vec<&str> = out.lines().filter(|l| l.contains("Relegation zone")).collect();
    assert_eq!(relegated.len(), 4, "{out}");
    for t in ["Vasco", "Goiás", "Coritiba", "Botafogo"] {
        assert!(relegated.iter().any(|l| l.contains(t)), "{t} missing: {relegated:?}");
    }
}

#[test]
fn scenario_libertadores_bracket() {
    // When I ask "Show the 2018 Copa Libertadores bracket"
    let out = ask("competition_bracket", json!({"competition": "Libertadores", "season": 2018}));
    // Then stages are listed in order and the final is River Plate v Boca Juniors
    let pos = |s: &str| out.find(s).unwrap_or_else(|| panic!("missing {s}: {out}"));
    assert!(pos("group stage") < pos("round of 16"));
    assert!(pos("quarterfinals") < pos("semifinals"));
    assert!(pos("semifinals") < pos("final (2 matches)"));
    assert!(out.contains("River Plate 3-1 Boca Juniors"));
    assert!(out.contains("winner on aggregate: River Plate"));
}

#[test]
fn scenario_compare_seasons() {
    // When I ask "Compare the 2018 and 2019 seasons"
    let out = ask("compare_seasons", json!({"season_a": 2018, "season_b": 2019}));
    // Then both seasons are aggregated
    assert!(out.contains("2018:") && out.contains("2019:"));
    assert!(out.contains("Top of table: Palmeiras (80 pts") && out.contains("Top of table: Flamengo (90 pts"), "{out}");
}

// ---------------------------------------------------------------- players

#[test]
fn scenario_search_player_by_name() {
    // When I ask "Who is Neymar?"
    let out = ask("player_details", json!({"player": "neymar"}));
    // Then the FIFA profile is returned
    assert!(out.contains("Neymar Jr") && out.contains("Overall: 92"), "{out}");
    assert!(out.contains("Paris Saint-Germain") && out.contains("Position: LW"));
    assert!(out.contains("Dribbling 96"));
    // And lookup by FIFA ID works too
    assert!(ask("player_details", json!({"player": "190871"})).contains("Neymar Jr"));
}

#[test]
fn scenario_brazilian_players() {
    // When I ask "Find all Brazilian players in the dataset" / "Who are the top Brazilian players?"
    let q = PlayerQuery { nationality: Some("Brazil".into()), ..Default::default() };
    let ps = db().find_players(&q);
    // Then only Brazilians are returned, best first
    assert_eq!(ps.len(), 827);
    assert!(ps.iter().all(|p| p.nationality == "Brazil"));
    assert!(ps.windows(2).all(|w| w[0].overall >= w[1].overall));
    assert_eq!(ps[0].name, "Neymar Jr");
    let out = ask("search_players", json!({"nationality": "Brazilian", "limit": 3}));
    assert!(out.contains("1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain"), "{out}");
}

#[test]
fn scenario_players_by_club_and_position() {
    // When I ask "Which players play for Santos?" (not Santos Laguna)
    let ps = db().find_players(&PlayerQuery { club: Some("Santos".into()), ..Default::default() });
    assert!(!ps.is_empty());
    assert!(ps.iter().all(|p| p.club == "Santos"));
    // When I ask for the forwards of Grêmio (accent-insensitive)
    let fw = db().find_players(&PlayerQuery { club: Some("Gremio".into()), position: Some("forwards".into()), ..Default::default() });
    // Then only attacking positions are returned
    assert!(!fw.is_empty());
    assert!(fw.iter().all(|p| p.club == "Grêmio" && ["ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"].contains(&p.position.as_str())));
    // And goalkeepers can be filtered by rating
    let gk = db().find_players(&PlayerQuery { position: Some("GK".into()), min_overall: Some(89), ..Default::default() });
    assert!(gk.iter().any(|p| p.name == "De Gea") && gk.iter().all(|p| p.position == "GK" && p.overall >= 89));
}

#[test]
fn scenario_brazilian_players_at_brazilian_clubs() {
    // When I group Brazilian players by Brazilian club
    let out = ask("players_by_club", json!({"nationality": "Brazil", "brazilian_clubs_only": true}));
    // Then Brazilian clubs are listed with counts and average rating, foreign clubs are not
    assert!(out.contains("- Grêmio: ") && out.contains("avg rating"), "{out}");
    assert!(!out.contains("Real Madrid") && !out.contains("Santos Laguna"));
}

#[test]
fn scenario_cross_file_team_profile() {
    // When I request a club profile combining match and player data
    let out = ask("team_profile", json!({"team": "Cruzeiro"}));
    // Then it includes the match record, competitions, derby and FIFA squad
    assert!(out.contains("Match data:") && out.contains("Copa Libertadores"), "{out}");
    assert!(out.contains("Clássico Mineiro"));
    assert!(out.contains("FIFA player data: ") && out.contains("Club: Cruzeiro"));
}

// ---------------------------------------------------------------- statistics

#[test]
fn scenario_average_goals_per_match() {
    // When I ask "What's the average goals per match in the Brasileirão?"
    let f = Filter { competition: Some(Competition::SerieA), ..Default::default() };
    let s = db().league_stats(&db().find_matches(&f));
    // Then a plausible average and consistent result split are returned
    assert!(s.avg_goals() > 2.2 && s.avg_goals() < 2.9, "{}", s.avg_goals());
    assert_eq!(s.home_wins + s.draws + s.away_wins, s.matches);
    assert!(s.home_wins > s.away_wins);
    let out = ask("league_stats", json!({"competition": "Brasileirão"}));
    assert!(out.contains("Average goals per match: 2.") && out.contains("Home win rate: "), "{out}");
    assert!(out.contains("Average corners per match"));
}

#[test]
fn scenario_best_home_and_away_records() {
    // When I ask "Which team has the best home record?"
    let f = Filter { venue: Venue::Home, competition: Some(Competition::SerieA), ..Default::default() };
    let rows = db().rank_teams(&f, "win_rate", 100).unwrap();
    // Then teams are sorted by home win rate
    assert!(rows.len() > 10);
    assert!(rows.windows(2).all(|w| w[0].1.win_rate() >= w[1].1.win_rate()));
    assert!(rows[0].1.win_rate() > 50.0);
    // And the away ranking is available as text
    let out = ask("rank_teams", json!({"venue": "away", "competition": "Série A", "min_matches": 100}));
    assert!(out.contains("away matches") && out.contains("1. "), "{out}");
    // And "Which team scored the most goals in Serie A 2019?" is Flamengo with 86
    let out = ask("rank_teams", json!({"season": 2019, "competition": "Serie A", "metric": "goals_for", "limit": 1}));
    assert!(out.contains("1. Flamengo") && out.contains("goals 86:37"), "{out}");
}

#[test]
fn scenario_biggest_wins() {
    // When I ask "Show me the biggest wins in the dataset"
    let out = ask("biggest_wins", json!({"limit": 5}));
    // Then matches are ordered by goal margin
    let margins: Vec<i32> = out
        .lines()
        .filter(|l| l.chars().next().map_or(false, |c| c.is_ascii_digit()))
        .map(|l| {
            let score = l.split_whitespace().find(|w| w.contains('-') && w.chars().all(|c| c.is_ascii_digit() || c == '-') && w.len() <= 5).unwrap();
            let (a, b) = score.split_once('-').unwrap();
            (a.parse::<i32>().unwrap() - b.parse::<i32>().unwrap()).abs()
        })
        .collect();
    assert_eq!(margins.len(), 5, "{out}");
    assert!(margins.windows(2).all(|w| w[0] >= w[1]) && margins[0] >= 7, "{margins:?}");
    assert!(out.contains("Average goals per match:"));
}

#[test]
fn scenario_derbies_in_a_season() {
    // When I ask "Show me all derbies in 2023"
    let out = ask("find_derbies", json!({"season": 2023, "limit": 100}));
    // Then matches between traditional rivals are listed with the derby name
    assert!(out.contains("Fla-Flu") && out.contains("Gre-Nal"), "{out}");
    assert!(out.lines().filter(|l| l.starts_with("- ")).all(|l| l.starts_with("- 2023")));
}

#[test]
fn scenario_extended_statistics_are_merged_onto_primary_records() {
    // Given BR-Football-Dataset.csv duplicates Serie A matches from other files
    // Then the surviving record carries the corner statistics
    let n = db().matches.iter().filter(|m| !m.duplicate && m.source != Source::BrFootball && m.extended.is_some()).count();
    assert!(n > 1000, "{n}");
}

// ---------------------------------------------------------------- performance

#[test]
fn scenario_queries_are_fast() {
    db();
    // When I run a simple lookup
    let t = Instant::now();
    ask("search_matches", json!({"team": "Flamengo", "opponent": "Vasco"}));
    ask("player_details", json!({"player": "Casemiro"}));
    // Then it responds in under 2 seconds
    assert!(t.elapsed().as_secs_f64() < 2.0);
    // When I run aggregate queries
    let t = Instant::now();
    ask("standings", json!({"season": 2019}));
    ask("rank_teams", json!({"venue": "home"}));
    ask("league_stats", json!({}));
    ask("players_by_club", json!({"nationality": "Brazil", "brazilian_clubs_only": true}));
    // Then they respond in under 5 seconds
    assert!(t.elapsed().as_secs_f64() < 5.0);
}

// ---------------------------------------------------------------- MCP protocol

fn rpc(msg: Value) -> Value {
    serde_json::from_str(&handle_message(db(), &msg.to_string()).expect("response")).unwrap()
}

#[test]
fn scenario_mcp_handshake_and_tool_listing() {
    // When a client initializes
    let r = rpc(json!({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}));
    // Then the server negotiates the version and advertises tools
    assert_eq!(r["result"]["protocolVersion"], "2024-11-05");
    assert!(r["result"]["capabilities"]["tools"].is_object());
    assert_eq!(r["result"]["serverInfo"]["name"], "brazilian-soccer-mcp");
    // And notifications get no response
    assert!(handle_message(db(), r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#).is_none());
    // When the client lists tools
    let r = rpc(json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}));
    let tools = r["result"]["tools"].as_array().unwrap();
    // Then every tool has a name, description and object schema
    assert_eq!(tools.len(), tool_definitions().len());
    assert!(tools.len() >= 15);
    for t in tools {
        assert!(t["name"].is_string() && t["description"].as_str().unwrap().len() > 20);
        assert_eq!(t["inputSchema"]["type"], "object");
    }
}

#[test]
fn scenario_mcp_tool_call_and_errors() {
    // When a tool is called over JSON-RPC
    let r = rpc(json!({"jsonrpc": "2.0", "id": "a", "method": "tools/call", "params": {"name": "standings", "arguments": {"season": "2019"}}}));
    // Then text content is returned
    assert_eq!(r["id"], "a");
    assert_eq!(r["result"]["isError"], false);
    assert!(r["result"]["content"][0]["text"].as_str().unwrap().contains("Flamengo - 90 pts"));
    // And bad arguments produce a tool error, not a protocol failure
    let r = rpc(json!({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "team_stats", "arguments": {"team": "Nonexistent United"}}}));
    assert_eq!(r["result"]["isError"], true);
    let r = rpc(json!({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "standings", "arguments": {}}}));
    assert_eq!(r["result"]["isError"], true);
    // And unknown tools / methods / malformed JSON produce JSON-RPC errors
    assert_eq!(rpc(json!({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "nope"}}))["error"]["code"], -32602);
    assert_eq!(rpc(json!({"jsonrpc": "2.0", "id": 6, "method": "bogus"}))["error"]["code"], -32601);
    let r: Value = serde_json::from_str(&handle_message(db(), "{not json").unwrap()).unwrap();
    assert_eq!(r["error"]["code"], -32700);
}

#[test]
fn scenario_every_tool_answers_with_default_or_minimal_arguments() {
    // When each advertised tool is called with its required arguments
    for t in tool_definitions() {
        let mut args = serde_json::Map::new();
        for r in t["inputSchema"]["required"].as_array().unwrap() {
            let k = r.as_str().unwrap();
            let v = match k {
                "team" | "team_a" => json!("Flamengo"),
                "team_b" => json!("Vasco"),
                "season" | "season_a" => json!(2018),
                "season_b" => json!(2019),
                "competition" => json!("Copa do Brasil"),
                "player" => json!("Marcelo"),
                o => panic!("no sample for required arg {o}"),
            };
            args.insert(k.to_string(), v);
        }
        // Then it returns a non-empty answer
        let out = ask(t["name"].as_str().unwrap(), Value::Object(args));
        assert!(out.len() > 40, "{}: {out}", t["name"]);
    }
}

#[test]
fn scenario_stdio_server_end_to_end() {
    use std::io::Write;
    use std::process::{Command, Stdio};
    // Given the server binary running on stdio
    let mut child = Command::new(env!("CARGO_BIN_EXE_brazilian-soccer-mcp"))
        .args(["--data-dir", &format!("{}/data/kaggle", env!("CARGO_MANIFEST_DIR"))])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .unwrap();
    // When a client sends initialize, a notification and a tool call, then closes stdin
    {
        let mut stdin = child.stdin.take().unwrap();
        for m in [
            json!({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}),
            json!({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json!({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "head_to_head", "arguments": {"team_a": "Grêmio", "team_b": "Internacional"}}}),
        ] {
            writeln!(stdin, "{m}").unwrap();
        }
    }
    let out = child.wait_with_output().unwrap();
    assert!(out.status.success());
    // Then exactly two newline-delimited responses come back
    let lines: Vec<Value> = String::from_utf8(out.stdout).unwrap().lines().map(|l| serde_json::from_str(l).unwrap()).collect();
    assert_eq!(lines.len(), 2);
    assert_eq!(lines[0]["id"], 1);
    assert!(lines[1]["result"]["content"][0]["text"].as_str().unwrap().contains("Gre-Nal"));
}
