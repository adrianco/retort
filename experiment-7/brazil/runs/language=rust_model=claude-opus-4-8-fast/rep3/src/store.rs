// =============================================================================
// store — the in-memory dataset
// -----------------------------------------------------------------------------
// Context:
//   `DataStore` owns the unified `Match` and `Player` collections. It is built
//   once at start-up via `load_from_dir` and then shared (read-only) by the
//   query layer and the MCP server. It also knows how to locate the dataset
//   directory from a list of candidate paths so the binary works both from the
//   repo root and from a packaged location.
// =============================================================================

use crate::data::{load_matches, load_players, Match, Player};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
pub struct DataStore {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

impl DataStore {
    /// Load every dataset found under `dir`.
    pub fn load_from_dir<P: AsRef<Path>>(dir: P) -> Self {
        let dir = dir.as_ref();
        DataStore {
            matches: load_matches(dir),
            players: load_players(dir),
        }
    }

    /// Resolve the dataset directory, honoring the `BRAZIL_SOCCER_DATA`
    /// environment variable, then trying a handful of conventional locations.
    pub fn resolve_data_dir() -> PathBuf {
        if let Ok(p) = std::env::var("BRAZIL_SOCCER_DATA") {
            let pb = PathBuf::from(p);
            if pb.exists() {
                return pb;
            }
        }
        let candidates = [
            PathBuf::from("data/kaggle"),
            PathBuf::from("./data/kaggle"),
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle"),
        ];
        for c in candidates {
            if c.exists() {
                return c;
            }
        }
        PathBuf::from("data/kaggle")
    }

    /// Convenience: load from the resolved default directory.
    pub fn load_default() -> Self {
        Self::load_from_dir(Self::resolve_data_dir())
    }

    pub fn match_count(&self) -> usize {
        self.matches.len()
    }

    pub fn player_count(&self) -> usize {
        self.players.len()
    }
}
