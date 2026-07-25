//! Command-line entry point.
//!
//! * `brazilian-soccer-mcp` — speak MCP over stdio (the mode an LLM host uses)
//! * `brazilian-soccer-mcp demo` — run the sample questions and print answers
//! * `brazilian-soccer-mcp ask <tool> '<json args>'` — one-shot tool call
//! * `--data-dir <path>` — override the dataset location

use std::io::{self, BufReader, Write};
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use brazilian_soccer_mcp::graph::KnowledgeGraph;
use brazilian_soccer_mcp::samples::SAMPLE_QUESTIONS;
use brazilian_soccer_mcp::{default_data_dir, mcp, tools};

const USAGE: &str = "\
brazilian-soccer-mcp — MCP server over Brazilian soccer datasets

USAGE:
    brazilian-soccer-mcp [--data-dir <path>]              serve MCP on stdio
    brazilian-soccer-mcp demo [--data-dir <path>]         answer the sample questions
    brazilian-soccer-mcp ask <tool> [json-args]           run a single tool
    brazilian-soccer-mcp tools                            list the available tools
    brazilian-soccer-mcp --help | --version
";

fn main() -> ExitCode {
    let mut args: Vec<String> = std::env::args().skip(1).collect();
    let mut data_dir: Option<PathBuf> = None;
    let mut idx = 0;
    while idx < args.len() {
        if args[idx] == "--data-dir" {
            if idx + 1 >= args.len() {
                eprintln!("--data-dir needs a path");
                return ExitCode::FAILURE;
            }
            data_dir = Some(PathBuf::from(args.remove(idx + 1)));
            args.remove(idx);
        } else {
            idx += 1;
        }
    }

    match args.first().map(String::as_str) {
        Some("--help" | "-h" | "help") => {
            print!("{USAGE}");
            ExitCode::SUCCESS
        }
        Some("--version" | "-V") => {
            println!("{} {}", mcp::SERVER_NAME, mcp::SERVER_VERSION);
            ExitCode::SUCCESS
        }
        Some("tools") => {
            for tool in tools::TOOLS {
                println!("{:<20} {}", tool.name, tool.description);
            }
            ExitCode::SUCCESS
        }
        Some("demo") => match load(data_dir) {
            Ok(graph) => run_demo(&graph),
            Err(code) => code,
        },
        Some("ask") => {
            let Some(tool) = args.get(1).cloned() else {
                eprintln!("usage: brazilian-soccer-mcp ask <tool> [json-args]");
                return ExitCode::FAILURE;
            };
            let raw_args = args.get(2).cloned().unwrap_or_else(|| "{}".to_string());
            let parsed = match serde_json::from_str(&raw_args) {
                Ok(value) => value,
                Err(error) => {
                    eprintln!("arguments must be JSON: {error}");
                    return ExitCode::FAILURE;
                }
            };
            match load(data_dir) {
                Ok(graph) => match tools::call(&graph, &tool, &parsed) {
                    Ok(output) => {
                        println!("{}", output.text);
                        ExitCode::SUCCESS
                    }
                    Err(message) => {
                        eprintln!("{message}");
                        ExitCode::FAILURE
                    }
                },
                Err(code) => code,
            }
        }
        Some(other) if other.starts_with('-') => {
            eprintln!("unknown option '{other}'\n\n{USAGE}");
            ExitCode::FAILURE
        }
        _ => match load(data_dir) {
            Ok(graph) => {
                let mut server = mcp::Server::new(graph);
                let stdin = BufReader::new(io::stdin());
                match server.serve(stdin, io::stdout()) {
                    Ok(()) => ExitCode::SUCCESS,
                    Err(error) => {
                        eprintln!("stdio transport failed: {error}");
                        ExitCode::FAILURE
                    }
                }
            }
            Err(code) => code,
        },
    }
}

fn load(data_dir: Option<PathBuf>) -> Result<KnowledgeGraph, ExitCode> {
    let dir = data_dir.unwrap_or_else(default_data_dir);
    match KnowledgeGraph::load(&dir) {
        Ok(graph) => {
            // Progress goes to stderr so it cannot corrupt the stdio transport.
            eprintln!(
                "loaded {} matches, {} teams and {} players from {} in {} ms",
                graph.matches.len(),
                graph.teams.len(),
                graph.players.len(),
                dir.display(),
                graph.load_millis
            );
            Ok(graph)
        }
        Err(error) => {
            eprintln!("failed to load datasets from {}: {error}", dir.display());
            Err(ExitCode::FAILURE)
        }
    }
}

fn run_demo(graph: &KnowledgeGraph) -> ExitCode {
    let stdout = io::stdout();
    let mut out = stdout.lock();
    let mut failures = 0;
    let mut category = "";
    for sample in SAMPLE_QUESTIONS {
        if sample.category != category {
            category = sample.category;
            let _ = writeln!(out, "\n{}\n{}", category, "=".repeat(category.len()));
        }
        let started = Instant::now();
        let result = tools::call(graph, sample.tool, &(sample.arguments)());
        let elapsed = started.elapsed();
        let _ = writeln!(
            out,
            "\nQ: {}\n   [{} {} — {:.1} ms]",
            sample.question,
            sample.tool,
            (sample.arguments)(),
            elapsed.as_secs_f64() * 1000.0
        );
        match result {
            Ok(output) => {
                for line in output.text.lines() {
                    let _ = writeln!(out, "   {line}");
                }
            }
            Err(message) => {
                failures += 1;
                let _ = writeln!(out, "   ERROR: {message}");
            }
        }
    }
    let _ = writeln!(
        out,
        "\n{} sample questions answered, {failures} failed.",
        SAMPLE_QUESTIONS.len() - failures
    );
    if failures == 0 {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}
