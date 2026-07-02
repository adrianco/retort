use std::path::Path;

use crate::loaders;
use crate::models::{Match, Player};
use crate::player_loader;

pub struct Store {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

impl Store {
    /// Loads all six provided datasets from `dir` (expected to contain the six
    /// `data/kaggle` CSV files) into a single in-memory store.
    pub fn load_from_dir(dir: &Path) -> anyhow::Result<Self> {
        let mut matches = Vec::new();
        matches.extend(loaders::load_brasileirao_matches(
            &dir.join("Brasileirao_Matches.csv"),
        )?);
        matches.extend(loaders::load_brazilian_cup_matches(
            &dir.join("Brazilian_Cup_Matches.csv"),
        )?);
        matches.extend(loaders::load_libertadores_matches(
            &dir.join("Libertadores_Matches.csv"),
        )?);
        matches.extend(loaders::load_br_football_dataset(
            &dir.join("BR-Football-Dataset.csv"),
        )?);
        matches.extend(loaders::load_novo_campeonato(
            &dir.join("novo_campeonato_brasileiro.csv"),
        )?);

        let players = player_loader::load_fifa_players(&dir.join("fifa_data.csv"))?;

        Ok(Store { matches, players })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn loads_all_datasets_from_a_directory() {
        let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        let store = Store::load_from_dir(&dir).unwrap();
        // 4180 + 1337 + 1254 + 10296 + 6886 (one Libertadores placeholder row is skipped).
        assert_eq!(store.matches.len(), 4180 + 1337 + 1254 + 10296 + 6886);
        assert_eq!(store.players.len(), 18207);
    }
}
