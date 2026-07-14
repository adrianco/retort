// =============================================================================
// main — Brazilian Soccer MCP Server entry point
// -----------------------------------------------------------------------------
// Context:
//   Loads the datasets once and then either:
//     * (default / `mcp`) runs the MCP JSON-RPC server over stdio, or
//     * (`demo`)          prints answers to a handful of sample questions from
//                         TASK.md so the server can be exercised without an MCP
//                         client, or
//     * (`info`)          prints dataset totals and exits.
//
//   Diagnostics go to stderr so they never corrupt the stdio JSON-RPC stream.
// =============================================================================

use brazilian_soccer_mcp::queries::{self, MatchFilter, PlayerFilter, PlayerSort, Venue};
use brazilian_soccer_mcp::{mcp, DataStore};
use std::io::{self, BufReader};

fn main() {
    let mode = std::env::args().nth(1).unwrap_or_else(|| "mcp".to_string());

    let dir = DataStore::resolve_data_dir();
    eprintln!("brazilian-soccer-mcp: loading datasets from {}", dir.display());
    let store = DataStore::load_from_dir(&dir);
    eprintln!(
        "brazilian-soccer-mcp: loaded {} matches and {} players",
        store.match_count(),
        store.player_count()
    );

    match mode.as_str() {
        "info" => {
            println!("{}", queries::list_competitions(&store));
        }
        "demo" => run_demo(&store),
        "mcp" | "serve" | "--stdio" => {
            let stdin = io::stdin();
            let stdout = io::stdout();
            let reader = BufReader::new(stdin.lock());
            let writer = stdout.lock();
            if let Err(e) = mcp::serve(&store, reader, writer) {
                eprintln!("brazilian-soccer-mcp: server error: {}", e);
                std::process::exit(1);
            }
        }
        other => {
            eprintln!(
                "Unknown mode '{}'. Use one of: mcp (default), demo, info.",
                other
            );
            std::process::exit(2);
        }
    }
}

/// Print answers to representative sample questions from the specification.
fn run_demo(store: &DataStore) {
    let line = "=".repeat(72);

    println!("{line}\nBrazilian Soccer MCP — demo queries\n{line}\n");

    println!("Q: Show me all Flamengo vs Fluminense matches\n");
    let mut f = MatchFilter::new();
    f.team = Some("Flamengo".into());
    f.opponent = Some("Fluminense".into());
    println!("{}\n{line}\n", queries::search_matches(store, &f, 8));

    println!("Q: What is Corinthians' home record in 2022 Brasileirão?\n");
    println!(
        "{}\n{line}\n",
        queries::team_record(store, "Corinthians", Some(2022), Some("Brasileirão"), Venue::Home)
    );

    println!("Q: Compare Palmeiras and Santos head-to-head\n");
    println!(
        "{}\n{line}\n",
        queries::head_to_head(store, "Palmeiras", "Santos", None, None, 8)
    );

    println!("Q: Top-rated Brazilian players\n");
    let pf = PlayerFilter {
        nationality: Some("Brazil".into()),
        ..Default::default()
    };
    println!(
        "{}\n{line}\n",
        queries::search_players(store, &pf, PlayerSort::Overall, 5)
    );

    println!("Q: Highest-rated players at Fluminense\n");
    let pf2 = PlayerFilter {
        club: Some("Fluminense".into()),
        ..Default::default()
    };
    println!(
        "{}\n{line}\n",
        queries::search_players(store, &pf2, PlayerSort::Overall, 5)
    );

    println!("Q: Who won the 2019 Brasileirão?\n");
    println!("{}\n{line}\n", queries::standings(store, "Brasileirão", 2019));

    println!("Q: Average goals per match and biggest wins in the Brasileirão\n");
    println!(
        "{}\n{line}\n",
        queries::competition_summary(store, Some("Brasileirão"), None, 5)
    );

    println!("Q: What competitions and seasons are available?\n");
    println!("{}", queries::list_competitions(store));
    println!("{}", queries::list_seasons(store, Some("Libertadores")));
}
