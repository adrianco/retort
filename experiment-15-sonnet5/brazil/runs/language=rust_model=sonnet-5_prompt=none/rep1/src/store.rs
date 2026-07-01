//! In-memory knowledge store: loads every dataset once at startup and
//! exposes it (plus a couple of derived indices) to the query layer.

use std::collections::{HashMap, HashSet};
use std::path::Path;

use anyhow::Result;

use crate::data;
use crate::model::{MatchRecord, Player};
use crate::normalize::{extract_state_suffix, normalize_team_name};

pub struct DatasetInfo {
    pub file: &'static str,
    pub rows: usize,
}

pub struct Store {
    pub matches: Vec<MatchRecord>,
    pub players: Vec<Player>,
    pub dataset_info: Vec<DatasetInfo>,
    /// Normalized keys of teams known to be Brazilian clubs, derived from
    /// the domestic competitions (everything except Libertadores, which is
    /// the only dataset containing foreign opponents).
    pub brazilian_team_keys: HashSet<String>,
    /// Loose team key -> a display name to show the user. Used for lenient
    /// search/browsing results.
    pub display_name: HashMap<String, String>,
    /// Unique team identity -> a display name. Used for aggregate stats
    /// (standings, records) where the loose key may be ambiguous.
    pub display_name_by_identity: HashMap<String, String>,
    /// Loose team keys that map to more than one real club in the loaded
    /// data (e.g. "atletico" is Atletico-MG, Atletico-GO, Atletico-PR, ...).
    pub ambiguous_bases: HashSet<String>,
}

impl Store {
    pub fn load(data_dir: &Path) -> Result<Self> {
        let brasileirao = data::load_brasileirao(&data_dir.join("Brasileirao_Matches.csv"))?;
        let cup = data::load_cup(&data_dir.join("Brazilian_Cup_Matches.csv"))?;
        let libertadores = data::load_libertadores(&data_dir.join("Libertadores_Matches.csv"))?;
        let br_football = data::load_br_football(&data_dir.join("BR-Football-Dataset.csv"))?;
        let historical = data::load_historical(&data_dir.join("novo_campeonato_brasileiro.csv"))?;
        let players = data::load_players(&data_dir.join("fifa_data.csv"))?;

        let dataset_info = vec![
            DatasetInfo { file: "Brasileirao_Matches.csv", rows: brasileirao.len() },
            DatasetInfo { file: "Brazilian_Cup_Matches.csv", rows: cup.len() },
            DatasetInfo { file: "Libertadores_Matches.csv", rows: libertadores.len() },
            DatasetInfo { file: "BR-Football-Dataset.csv", rows: br_football.len() },
            DatasetInfo { file: "novo_campeonato_brasileiro.csv", rows: historical.len() },
            DatasetInfo { file: "fifa_data.csv", rows: players.len() },
        ];

        let mut matches = Vec::with_capacity(
            brasileirao.len() + cup.len() + libertadores.len() + br_football.len() + historical.len(),
        );
        let mut brazilian_team_keys = HashSet::new();
        let mut display_name: HashMap<String, String> = HashMap::new();

        // `Brasileirao_Matches.csv` and `novo_campeonato_brasileiro.csv` both
        // cover seasons 2012-2019 (380 matches each, i.e. the same
        // fixtures). Keep `Brasileirao_Matches.csv` for the years it
        // covers (2012+) and the historical file only for the years it
        // uniquely covers (pre-2012), so aggregate stats don't double-count.
        let historical = historical
            .into_iter()
            .filter(|m| m.season.is_none_or(|s| s < 2012));

        for m in brasileirao.into_iter().chain(cup).chain(br_football).chain(historical) {
            brazilian_team_keys.insert(m.home_team_key.clone());
            brazilian_team_keys.insert(m.away_team_key.clone());
            matches.push(m);
        }
        for m in libertadores {
            matches.push(m);
        }

        for m in &matches {
            display_name
                .entry(m.home_team_key.clone())
                .or_insert_with(|| m.home_team.clone());
            display_name
                .entry(m.away_team_key.clone())
                .or_insert_with(|| m.away_team.clone());
        }

        // Some loose keys are shared by genuinely different clubs in
        // different states (e.g. "atletico" = Atletico-MG, Atletico-GO,
        // Atletico-PR, ...; see the state suffixes captured per-record by
        // the loaders). Detect those collisions from the data itself, then
        // fold the state back into a unique identity for every record so
        // aggregate stats (standings, team records) never merge distinct
        // clubs together.
        let mut states_per_key: HashMap<&str, HashSet<&str>> = HashMap::new();
        for m in &matches {
            if let Some(s) = &m.home_state {
                states_per_key.entry(&m.home_team_key).or_default().insert(s.as_str());
            }
            if let Some(s) = &m.away_state {
                states_per_key.entry(&m.away_team_key).or_default().insert(s.as_str());
            }
        }
        let ambiguous_bases: HashSet<String> = states_per_key
            .into_iter()
            .filter(|(_, states)| states.len() >= 2)
            .map(|(key, _)| key.to_string())
            .collect();

        for m in &mut matches {
            m.home_identity = team_identity(&m.home_team_key, &m.home_state, &ambiguous_bases);
            m.away_identity = team_identity(&m.away_team_key, &m.away_state, &ambiguous_bases);
        }

        let mut display_name_by_identity: HashMap<String, String> = HashMap::new();
        for m in &matches {
            display_name_by_identity
                .entry(m.home_identity.clone())
                .or_insert_with(|| m.home_team.clone());
            display_name_by_identity
                .entry(m.away_identity.clone())
                .or_insert_with(|| m.away_team.clone());
        }

        Ok(Store {
            matches,
            players,
            dataset_info,
            brazilian_team_keys,
            display_name,
            display_name_by_identity,
            ambiguous_bases,
        })
    }

    pub fn display_name_for(&self, key: &str) -> String {
        self.display_name.get(key).cloned().unwrap_or_else(|| key.to_string())
    }

    pub fn display_name_by_identity_for(&self, key: &str) -> String {
        self.display_name_by_identity.get(key).cloned().unwrap_or_else(|| key.to_string())
    }

    pub fn is_brazilian_club(&self, key: &str) -> bool {
        self.brazilian_team_keys.contains(key)
    }

    /// Resolve a user-supplied team name (which may or may not include a
    /// state suffix) to the same unique identity used to group aggregate
    /// stats in [`Self::matches`].
    pub fn resolve_identity(&self, raw: &str) -> String {
        let loose = normalize_team_name(raw);
        let state = extract_state_suffix(raw);
        team_identity(&loose, &state, &self.ambiguous_bases)
    }

    pub fn is_ambiguous_base(&self, loose_key: &str) -> bool {
        self.ambiguous_bases.contains(loose_key)
    }
}

fn team_identity(loose_key: &str, state: &Option<String>, ambiguous_bases: &HashSet<String>) -> String {
    if ambiguous_bases.contains(loose_key) {
        match state {
            Some(s) => format!("{loose_key}-{}", s.to_lowercase()),
            None => format!("{loose_key}-unk"),
        }
    } else {
        loose_key.to_string()
    }
}
