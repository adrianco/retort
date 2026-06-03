use std::path::{Path, PathBuf};

use anyhow::{Context, Result};

use crate::data::{Match, Player};
use crate::loader;

#[derive(Debug)]
pub struct Store {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    pub source_dir: PathBuf,
}

impl Store {
    /// Load every CSV under `data_dir` (expected layout: `data_dir/kaggle/*.csv`
    /// or simply `data_dir/*.csv`).
    pub fn load<P: AsRef<Path>>(data_dir: P) -> Result<Self> {
        let base = data_dir.as_ref().to_path_buf();
        let kaggle = if base.join("kaggle").is_dir() {
            base.join("kaggle")
        } else {
            base.clone()
        };

        let mut matches = Vec::new();

        let brasileirao = kaggle.join("Brasileirao_Matches.csv");
        if brasileirao.is_file() {
            matches.extend(
                loader::load_brasileirao(&brasileirao)
                    .with_context(|| format!("loading {}", brasileirao.display()))?,
            );
        }
        let cup = kaggle.join("Brazilian_Cup_Matches.csv");
        if cup.is_file() {
            matches.extend(
                loader::load_cup(&cup)
                    .with_context(|| format!("loading {}", cup.display()))?,
            );
        }
        let lib = kaggle.join("Libertadores_Matches.csv");
        if lib.is_file() {
            matches.extend(
                loader::load_libertadores(&lib)
                    .with_context(|| format!("loading {}", lib.display()))?,
            );
        }
        let brf = kaggle.join("BR-Football-Dataset.csv");
        if brf.is_file() {
            matches.extend(
                loader::load_br_football(&brf)
                    .with_context(|| format!("loading {}", brf.display()))?,
            );
        }
        let hist = kaggle.join("novo_campeonato_brasileiro.csv");
        if hist.is_file() {
            matches.extend(
                loader::load_historic(&hist)
                    .with_context(|| format!("loading {}", hist.display()))?,
            );
        }

        let players_path = kaggle.join("fifa_data.csv");
        let players = if players_path.is_file() {
            loader::load_players(&players_path)
                .with_context(|| format!("loading {}", players_path.display()))?
        } else {
            Vec::new()
        };

        Ok(Store {
            matches,
            players,
            source_dir: base,
        })
    }
}
